"""
byte_tracker.py — Lightweight ByteTrack implementation.
Chỉ gồm Kalman filter + IoU matching (Hungarian algorithm).
Không cần thư viện ByteTrack gốc, phù hợp cho Raspberry Pi.

Thuật toán ByteTrack:
    1. First association: high-score detections ↔ tracks (IoU)
    2. Second association: low-score detections ↔ unmatched tracks (IoU)
    3. Init new tracks từ unmatched high-score detections
    4. Remove lost tracks sau max_time_lost frames
"""

import numpy as np
from scipy.optimize import linear_sum_assignment
import logging

logger = logging.getLogger(__name__)


class KalmanFilter:
    """
    Kalman filter 8-state cho object tracking.
    State: [cx, cy, aspect_ratio, height, vx, vy, va, vh]
    Measurement: [cx, cy, aspect_ratio, height]
    """

    def __init__(self):
        # State transition matrix (constant velocity model)
        self.F = np.eye(8, dtype=np.float32)
        self.F[0, 4] = 1.0  # cx += vx
        self.F[1, 5] = 1.0  # cy += vy
        self.F[2, 6] = 1.0  # a += va
        self.F[3, 7] = 1.0  # h += vh

        # Measurement matrix
        self.H = np.eye(4, 8, dtype=np.float32)

        # Process noise
        self.Q = np.eye(8, dtype=np.float32)
        self.Q[0, 0] = self.Q[1, 1] = 1.0
        self.Q[2, 2] = self.Q[3, 3] = 1.0
        self.Q[4, 4] = self.Q[5, 5] = 0.01
        self.Q[6, 6] = self.Q[7, 7] = 0.0001

        # Measurement noise
        self.R = np.eye(4, dtype=np.float32)
        self.R[0, 0] = self.R[1, 1] = 1.0
        self.R[2, 2] = self.R[3, 3] = 10.0

    def init(self, measurement):
        """Khởi tạo state từ measurement [cx, cy, a, h]."""
        x = np.zeros(8, dtype=np.float32)
        x[:4] = measurement
        P = np.eye(8, dtype=np.float32) * 10.0
        P[4:, 4:] *= 100.0
        return x, P

    def predict(self, x, P):
        """Predict step: x' = F @ x, P' = F @ P @ F^T + Q"""
        x = self.F @ x
        P = self.F @ P @ self.F.T + self.Q
        return x, P

    def update(self, x, P, measurement):
        """Update step với measurement [cx, cy, a, h]."""
        y = measurement - self.H @ x  # Innovation
        S = self.H @ P @ self.H.T + self.R  # Innovation covariance
        K = P @ self.H.T @ np.linalg.inv(S)  # Kalman gain
        x = x + K @ y
        P = (np.eye(8) - K @ self.H) @ P
        return x, P


class Track:
    """Một tracked object."""

    _next_id = 1

    def __init__(self, detection, kf):
        self.id = Track._next_id
        Track._next_id += 1

        self.kf = kf
        x1, y1, x2, y2 = detection[:4]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w = x2 - x1
        h = y2 - y1
        a = w / (h + 1e-6)

        self.x, self.P = kf.init(np.array([cx, cy, a, h], dtype=np.float32))
        self.score = detection[4] if len(detection) > 4 else 1.0
        self.cls = int(detection[5]) if len(detection) > 5 else 0
        self.time_since_update = 0
        self.hits = 1
        self.age = 1

    @property
    def bbox(self):
        """Trả về [x1, y1, x2, y2] từ state hiện tại."""
        cx, cy, a, h = self.x[:4]
        w = a * h
        return np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])

    def predict(self):
        """Predict bước tiếp theo."""
        self.x, self.P = self.kf.predict(self.x, self.P)
        self.age += 1
        self.time_since_update += 1

    def update(self, detection):
        """Update với detection mới."""
        x1, y1, x2, y2 = detection[:4]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w = x2 - x1
        h = y2 - y1
        a = w / (h + 1e-6)

        measurement = np.array([cx, cy, a, h], dtype=np.float32)
        self.x, self.P = self.kf.update(self.x, self.P, measurement)

        self.score = detection[4] if len(detection) > 4 else 1.0
        self.time_since_update = 0
        self.hits += 1


def _iou_batch(bboxes1, bboxes2):
    """Tính IoU matrix giữa 2 tập bounding boxes."""
    if len(bboxes1) == 0 or len(bboxes2) == 0:
        return np.empty((len(bboxes1), len(bboxes2)), dtype=np.float32)

    b1 = np.array(bboxes1)
    b2 = np.array(bboxes2)

    xx1 = np.maximum(b1[:, None, 0], b2[None, :, 0])
    yy1 = np.maximum(b1[:, None, 1], b2[None, :, 1])
    xx2 = np.minimum(b1[:, None, 2], b2[None, :, 2])
    yy2 = np.minimum(b1[:, None, 3], b2[None, :, 3])

    inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
    area1 = (b1[:, 2] - b1[:, 0]) * (b1[:, 3] - b1[:, 1])
    area2 = (b2[:, 2] - b2[:, 0]) * (b2[:, 3] - b2[:, 1])

    iou = inter / (area1[:, None] + area2[None, :] - inter + 1e-6)
    return iou


def _linear_assignment(cost_matrix, thresh):
    """Hungarian matching với ngưỡng."""
    if cost_matrix.size == 0:
        return [], list(range(cost_matrix.shape[0])), list(range(cost_matrix.shape[1]))

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    matches = []
    unmatched_a = list(range(cost_matrix.shape[0]))
    unmatched_b = list(range(cost_matrix.shape[1]))

    for r, c in zip(row_ind, col_ind):
        if cost_matrix[r, c] > thresh:
            continue
        matches.append((r, c))
        if r in unmatched_a:
            unmatched_a.remove(r)
        if c in unmatched_b:
            unmatched_b.remove(c)

    return matches, unmatched_a, unmatched_b


class ByteTracker:
    """
    Lightweight ByteTrack tracker.
    
    Usage:
        tracker = ByteTracker()
        
        # Khi có YOLO detection:
        tracks = tracker.update(detections)
        
        # Khi không có YOLO (chỉ predict):
        tracks = tracker.predict_only()
    """

    def __init__(self, track_thresh=0.5, track_low=0.1,
                 match_thresh=0.8, max_time_lost=30):
        self.track_thresh = track_thresh
        self.track_low = track_low
        self.match_thresh = match_thresh
        self.max_time_lost = max_time_lost

        self._kf = KalmanFilter()
        self._tracks = []

    def predict_only(self):
        """
        Chỉ predict (không có detection mới).
        Dùng cho frames không chạy YOLO.
        
        Returns:
            list of Track objects (chỉ tracks đang active)
        """
        for track in self._tracks:
            track.predict()

        # Xóa tracks quá cũ
        self._tracks = [
            t for t in self._tracks
            if t.time_since_update <= self.max_time_lost
        ]

        return [t for t in self._tracks if t.time_since_update == 0 or t.hits >= 3]

    def update(self, detections):
        """
        Update tracker với detections mới từ YOLO.
        
        Args:
            detections: np.ndarray shape (N, 6) — [x1, y1, x2, y2, conf, cls]
            
        Returns:
            list of Track objects (active tracks)
        """
        # Predict tất cả tracks
        for track in self._tracks:
            track.predict()

        if len(detections) == 0:
            self._tracks = [
                t for t in self._tracks
                if t.time_since_update <= self.max_time_lost
            ]
            return [t for t in self._tracks if t.hits >= 3]

        # Tách high-score và low-score detections
        scores = detections[:, 4]
        high_mask = scores >= self.track_thresh
        low_mask = (scores >= self.track_low) & (~high_mask)

        dets_high = detections[high_mask]
        dets_low = detections[low_mask]

        # === First association: high-score dets ↔ all tracks ===
        if len(self._tracks) > 0 and len(dets_high) > 0:
            track_bboxes = [t.bbox for t in self._tracks]
            iou_matrix = _iou_batch(track_bboxes, dets_high[:, :4])
            cost = 1.0 - iou_matrix

            matches1, unmatched_tracks, unmatched_dets = _linear_assignment(
                cost, self.match_thresh
            )

            for t_idx, d_idx in matches1:
                self._tracks[t_idx].update(dets_high[d_idx])
        else:
            unmatched_tracks = list(range(len(self._tracks)))
            unmatched_dets = list(range(len(dets_high)))

        # === Second association: low-score dets ↔ unmatched tracks ===
        remaining_tracks = [self._tracks[i] for i in unmatched_tracks]

        if len(remaining_tracks) > 0 and len(dets_low) > 0:
            track_bboxes = [t.bbox for t in remaining_tracks]
            iou_matrix = _iou_batch(track_bboxes, dets_low[:, :4])
            cost = 1.0 - iou_matrix

            matches2, _, _ = _linear_assignment(cost, self.match_thresh)

            matched_track_indices = set()
            for t_idx, d_idx in matches2:
                remaining_tracks[t_idx].update(dets_low[d_idx])
                matched_track_indices.add(unmatched_tracks[t_idx])

        # === Init new tracks từ unmatched high-score detections ===
        for d_idx in unmatched_dets:
            new_track = Track(dets_high[d_idx], self._kf)
            self._tracks.append(new_track)

        # === Remove lost tracks ===
        self._tracks = [
            t for t in self._tracks
            if t.time_since_update <= self.max_time_lost
        ]

        # Return only confirmed tracks (hits >= 3 hoặc vừa update)
        return [t for t in self._tracks if t.time_since_update == 0 or t.hits >= 3]

    def get_active_tracks(self):
        """Lấy danh sách tracks đang active."""
        return [
            t for t in self._tracks
            if t.time_since_update <= 1 and t.hits >= 2
        ]

    def reset(self):
        """Reset tất cả tracks."""
        self._tracks.clear()
        Track._next_id = 1
