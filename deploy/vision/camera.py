"""
camera.py — Đọc frame từ camera/RTSP/video file hoặc Socket (Zero-CPU Decode).
Hỗ trợ bật/tắt động theo yêu cầu để tiết kiệm tài nguyên.
"""

import cv2
import threading
import time
import logging
import socket
import struct
import numpy as np

logger = logging.getLogger(__name__)


class Camera:
    """
    Camera wrapper hỗ trợ cả OpenCV (webcam, RTSP, video file) 
    và TCP Socket (nhận ảnh RAW đã giải mã và resize từ LAN).
    """

    def __init__(self, source=0, fps=15, width=1280, height=720):
        self.source = source
        self.target_fps = fps
        self.width = width
        self.height = height

        # Kiểm tra chế độ kết nối (Socket vs OpenCV)
        self.is_socket = False
        self.socket_host = "0.0.0.0"
        self.socket_port = 8089

        if isinstance(source, str) and (source.startswith("socket://") or source.startswith("tcp://")):
            self.is_socket = True
            clean_source = source.replace("socket://", "").replace("tcp://", "")
            if ":" in clean_source:
                self.socket_host, port_str = clean_source.split(":")
                self.socket_port = int(port_str)
            else:
                self.socket_host = clean_source
            # Đối với chế độ socket, ta ưu tiên kích thước nhận về khớp với kích thước YOLO (thường là 640x640)
            self.width = 640
            self.height = 640
            self.frame_size = self.width * self.height * 3  # 1,228,800 bytes cho 640x640 BGR
            logger.info(f"Camera initialized in SOCKET mode: {self.socket_host}:{self.socket_port}")
        else:
            logger.info(f"Camera initialized in OPENCV mode: source={source}")

        self._cap = None
        self._server_socket = None
        self._conn = None
        self._frame = None
        self._frame_id = 0
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        """Mở camera/socket và bắt đầu đọc frame trên thread riêng."""
        if self._running:
            logger.warning("Camera already running.")
            return

        self._running = True
        self._frame_id = 0

        if self.is_socket:
            logger.info(f"Starting TCP Socket Camera Server on {self.socket_host}:{self.socket_port}...")
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.socket_host, self.socket_port))
            self._server_socket.listen(1)
            self._thread = threading.Thread(target=self._socket_loop, daemon=True)
        else:
            logger.info(f"Opening camera: source={self.source}")
            self._cap = cv2.VideoCapture(self.source)
            if not self._cap.isOpened():
                raise RuntimeError(f"Cannot open camera: {self.source}")
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self._cap.get(cv2.CAP_PROP_FPS) or self.target_fps
            logger.info(f"Camera opened: {actual_w}x{actual_h} @ {actual_fps:.1f} FPS")
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)

        self._thread.start()

    def stop(self):
        """Dừng camera và giải phóng tài nguyên."""
        self._running = False
        self.close_socket_conn()

        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        if self._server_socket is not None:
            self._server_socket.close()
            self._server_socket = None

        with self._lock:
            self._frame = None
            self._frame_id = 0
        logger.info("Camera stopped.")

    def close_socket_conn(self):
        """Đóng kết nối socket hiện tại."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as e:
                logger.warning(f"Error closing socket connection: {e}")
            self._conn = None

    def _recv_all(self, conn, n):
        """Đọc chính xác n bytes từ TCP socket."""
        data = bytearray()
        while len(data) < n:
            if not self._running:
                return None
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data

    def _socket_loop(self):
        """Thread loop nhận frame RAW từ socket."""
        reconnect_delay = 1.0

        while self._running:
            if self._server_socket is None:
                break
            try:
                # Đặt timeout cho accept để thread có thể thoát khi self._running = False
                self._server_socket.settimeout(2.0)
                try:
                    self._conn, addr = self._server_socket.accept()
                    logger.info(f"Camera client connected from {addr}")
                    self._conn.settimeout(5.0)  # Timeout nhận dữ liệu
                    reconnect_delay = 1.0
                except socket.timeout:
                    continue

                while self._running:
                    # 1. Nhận Header chứa độ dài frame (4 bytes)
                    header = self._recv_all(self._conn, 4)
                    if not header:
                        logger.warning("Socket disconnected (failed to read header).")
                        break
                    
                    frame_len = struct.unpack("!I", header)[0]
                    if frame_len != self.frame_size:
                        logger.error(f"Invalid frame size: {frame_len} bytes (expected {self.frame_size})")
                        break

                    # 2. Nhận Payload ảnh thô
                    data = self._recv_all(self._conn, frame_len)
                    if not data:
                        logger.warning("Socket disconnected (failed to read payload).")
                        break

                    # 3. Chuyển thành numpy BGR frame (Zero-CPU decode/resize)
                    frame = np.frombuffer(data, dtype=np.uint8).reshape((self.height, self.width, 3))

                    with self._lock:
                        self._frame = frame
                        self._frame_id += 1

            except Exception as e:
                logger.error(f"Socket receiver error: {e}")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60.0)
            finally:
                self.close_socket_conn()

    def _capture_loop(self):
        """Thread loop OpenCV: đọc frame liên tục, giữ frame mới nhất."""
        interval = 1.0 / self.target_fps
        reconnect_delay = 1.0

        while self._running:
            t0 = time.monotonic()

            if self._cap is None or not self._cap.isOpened():
                logger.warning(f"Camera disconnected. Reconnecting in {reconnect_delay:.0f}s...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60.0)
                try:
                    self._cap = cv2.VideoCapture(self.source)
                    if self._cap.isOpened():
                        logger.info("Camera reconnected.")
                        reconnect_delay = 1.0
                except Exception as e:
                    logger.error(f"Reconnect failed: {e}")
                continue

            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Failed to read frame.")
                time.sleep(0.1)
                continue

            reconnect_delay = 1.0  # Reset

            with self._lock:
                self._frame = frame
                self._frame_id += 1

            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_frame(self):
        """Lấy bản sao của frame mới nhất và ID tương ứng."""
        with self._lock:
            if self._frame is None:
                return None, 0
            return self._frame.copy(), self._frame_id

    @property
    def is_running(self):
        return self._running

    @property
    def frame_id(self):
        with self._lock:
            return self._frame_id

    def __del__(self):
        self.stop()
