"""
yolo_detector.py — YOLO26n INT8 inference wrapper cho TFLite.
Bao gồm: resize, quantize, invoke, NMS, và trả về detections.
"""

import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)


def _load_tflite_interpreter(model_path):
    """Load TFLite interpreter."""
    try:
        from tflite_runtime.interpreter import Interpreter
        return Interpreter(model_path=model_path)
    except ImportError:
        pass
    try:
        from ai_edge_litert.interpreter import Interpreter
        return Interpreter(model_path=model_path)
    except ImportError:
        pass
    import tensorflow as tf
    return tf.lite.Interpreter(model_path=model_path)


class YOLODetector:
    """
    YOLO26n INT8 TFLite detector.
    
    Output format per detection:
        [x1, y1, x2, y2, confidence, class_id]
    Tọa độ trả về ở scale ảnh gốc.
    """

    def __init__(self, model_path, imgsz=640, conf_thresh=0.25, iou_thresh=0.45):
        self.imgsz = imgsz
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh

        self._interp = _load_tflite_interpreter(model_path)
        self._interp.allocate_tensors()

        self._inp = self._interp.get_input_details()[0]
        self._outs = self._interp.get_output_details()

        self._inp_shape = self._inp['shape']  # [1, H, W, 3]
        self._inp_dtype = self._inp['dtype']

        # Quantization params
        if self._inp_dtype in (np.int8, np.uint8):
            self._inp_scale, self._inp_zp = self._inp['quantization']
        else:
            self._inp_scale, self._inp_zp = 1.0, 0

        logger.info(f"YOLODetector loaded: {model_path}")
        logger.info(f"  Input: {list(self._inp_shape)}, dtype={self._inp_dtype}")
        logger.info(f"  Outputs: {len(self._outs)}")
        for i, o in enumerate(self._outs):
            logger.info(f"  Output[{i}]: {list(o['shape'])}, dtype={o['dtype']}")

    def _preprocess(self, frame):
        """
        Resize + letterbox + quantize.
        Returns: (input_tensor, scale, pad_x, pad_y)
        """
        h0, w0 = frame.shape[:2]
        
        # Letterbox resize giữ tỷ lệ
        scale = min(self.imgsz / h0, self.imgsz / w0)
        new_w, new_h = int(w0 * scale), int(h0 * scale)
        resized = cv2.resize(frame, (new_w, new_h))

        # Pad to imgsz × imgsz
        pad_x = (self.imgsz - new_w) // 2
        pad_y = (self.imgsz - new_h) // 2
        padded = np.full((self.imgsz, self.imgsz, 3), 114, dtype=np.uint8)
        padded[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

        # Convert BGR → RGB
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)

        # Quantize
        if self._inp_dtype == np.float32:
            tensor = rgb.astype(np.float32) / 255.0
        elif self._inp_dtype == np.uint8:
            tensor = rgb.astype(np.uint8)
        elif self._inp_dtype == np.int8:
            tensor = (rgb.astype(np.float32) / self._inp_scale + self._inp_zp)
            tensor = np.clip(tensor, -128, 127).astype(np.int8)
        else:
            tensor = rgb.astype(np.float32) / 255.0

        tensor = np.expand_dims(tensor, axis=0)
        return tensor, scale, pad_x, pad_y

    def _postprocess(self, outputs, scale, pad_x, pad_y, orig_h, orig_w):
        """
        Parse YOLO output → list of [x1, y1, x2, y2, conf, class_id].
        Hỗ trợ cả output format (1, N, 6) và (1, 6, N).
        """
        # Lấy output tensor đầu tiên
        raw = outputs[0].astype(np.float32)
        
        # Dequantize nếu cần
        out_detail = self._outs[0]
        if out_detail['dtype'] in (np.int8, np.uint8):
            s, z = out_detail['quantization']
            raw = (raw - z) * s

        # Xử lý shape
        if raw.ndim == 3:
            raw = raw[0]  # Remove batch dim → (N, 6) or (6, N)
        
        # Nếu shape là (6, N), transpose về (N, 6)
        if raw.shape[0] < raw.shape[1]:
            raw = raw.T

        if len(raw) == 0:
            return np.empty((0, 6), dtype=np.float32)

        # Tùy format: [cx, cy, w, h, conf, class] hoặc [cx, cy, w, h, class_scores...]
        if raw.shape[1] == 6:
            # Format: cx, cy, w, h, conf, class_id
            cx, cy, w, h = raw[:, 0], raw[:, 1], raw[:, 2], raw[:, 3]
            conf = raw[:, 4]
            cls_id = raw[:, 5]
        else:
            # Format: cx, cy, w, h, class_score_0, class_score_1, ...
            cx, cy, w, h = raw[:, 0], raw[:, 1], raw[:, 2], raw[:, 3]
            class_scores = raw[:, 4:]
            cls_id = np.argmax(class_scores, axis=1).astype(np.float32)
            conf = np.max(class_scores, axis=1)

        # Filter by confidence
        mask = conf >= self.conf_thresh
        if not np.any(mask):
            return np.empty((0, 6), dtype=np.float32)

        cx, cy, w, h = cx[mask], cy[mask], w[mask], h[mask]
        conf, cls_id = conf[mask], cls_id[mask]

        # Convert cxcywh → xyxy (on padded image)
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2

        # Remove padding and scale back to original
        x1 = (x1 - pad_x) / scale
        y1 = (y1 - pad_y) / scale
        x2 = (x2 - pad_x) / scale
        y2 = (y2 - pad_y) / scale

        # Clip to image bounds
        x1 = np.clip(x1, 0, orig_w)
        y1 = np.clip(y1, 0, orig_h)
        x2 = np.clip(x2, 0, orig_w)
        y2 = np.clip(y2, 0, orig_h)

        dets = np.stack([x1, y1, x2, y2, conf, cls_id], axis=1)

        # NMS per class
        keep = self._nms(dets)
        return dets[keep]

    def _nms(self, dets):
        """Non-Maximum Suppression."""
        if len(dets) == 0:
            return []

        x1, y1, x2, y2 = dets[:, 0], dets[:, 1], dets[:, 2], dets[:, 3]
        scores = dets[:, 4]

        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []

        while len(order) > 0:
            i = order[0]
            keep.append(i)

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

            inds = np.where(iou <= self.iou_thresh)[0]
            order = order[inds + 1]

        return keep

    def detect(self, frame):
        """
        Chạy YOLO detection trên 1 frame.
        
        Args:
            frame: np.ndarray BGR, shape (H, W, 3)
            
        Returns:
            np.ndarray shape (N, 6): [x1, y1, x2, y2, conf, class_id]
            Tọa độ ở scale ảnh gốc.
        """
        h0, w0 = frame.shape[:2]
        tensor, scale, pad_x, pad_y = self._preprocess(frame)

        self._interp.set_tensor(self._inp['index'], tensor)
        self._interp.invoke()

        outputs = [self._interp.get_tensor(o['index']) for o in self._outs]

        return self._postprocess(outputs, scale, pad_x, pad_y, h0, w0)
