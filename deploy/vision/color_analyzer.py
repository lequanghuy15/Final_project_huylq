"""
color_analyzer.py — HSV color extraction + FFT analysis per tracked vehicle.
Tích lũy năng lượng màu đỏ/xanh theo thời gian cho mỗi vehicle ID,
sau đó chạy FFT để phát hiện đèn nhấp nháy tuần hoàn.
"""

import numpy as np
import cv2
import collections
import logging
from scipy.signal import detrend, butter, sosfiltfilt

logger = logging.getLogger(__name__)


class VehicleColorBuffer:
    """Buffer năng lượng màu cho 1 vehicle."""

    __slots__ = ['red_energy', 'blue_energy', 'flash_energy', 'max_len']

    def __init__(self, max_len=150):
        self.max_len = max_len
        self.red_energy = collections.deque(maxlen=max_len)
        self.blue_energy = collections.deque(maxlen=max_len)
        self.flash_energy = collections.deque(maxlen=max_len)

    def append(self, red_e, blue_e):
        self.red_energy.append(red_e)
        self.blue_energy.append(blue_e)
        self.flash_energy.append(red_e + blue_e)

    @property
    def n_frames(self):
        return len(self.flash_energy)


class FFTResult:
    """Kết quả phân tích FFT cho 1 vehicle."""

    __slots__ = ['peak_freq', 'peak_ratio', 'red_max', 'blue_max',
                 'n_frames', 'is_strobe']

    def __init__(self):
        self.peak_freq = 0.0
        self.peak_ratio = 0.0
        self.red_max = 0.0
        self.blue_max = 0.0
        self.n_frames = 0
        self.is_strobe = False


class ColorAnalyzer:
    """
    Phân tích đèn nhấp nháy cho tất cả tracked vehicles.
    
    Pipeline per frame per vehicle:
        1. Crop bbox từ frame gốc
        2. BGR → HSV
        3. Mask đỏ + mask xanh → đo năng lượng
        4. Tích lũy vào buffer per vehicle ID
        5. Khi đủ frames → chạy FFT
    """

    def __init__(self, fps=15,
                 red1_low=None, red1_high=None,
                 red2_low=None, red2_high=None,
                 blue_low=None, blue_high=None,
                 min_frames=30, freq_min=1.0, freq_max=5.0,
                 peak_ratio_thresh=5.0, color_energy_thresh=5.0,
                 window_sec=5.0):

        self.fps = fps
        self.min_frames = min_frames
        self.freq_min = freq_min
        self.freq_max = freq_max
        self.peak_ratio_thresh = peak_ratio_thresh
        self.color_energy_thresh = color_energy_thresh
        self.max_buffer_len = int(window_sec * fps)

        # HSV thresholds
        self.red1_low = red1_low if red1_low is not None else np.array([0, 80, 100])
        self.red1_high = red1_high if red1_high is not None else np.array([12, 255, 255])
        self.red2_low = red2_low if red2_low is not None else np.array([168, 80, 100])
        self.red2_high = red2_high if red2_high is not None else np.array([180, 255, 255])
        self.blue_low = blue_low if blue_low is not None else np.array([90, 70, 100])
        self.blue_high = blue_high if blue_high is not None else np.array([135, 255, 255])

        # Bộ lọc thông dải Butterworth cho tín hiệu đèn nháy
        nyq = 0.5 * self.fps
        low = self.freq_min / nyq
        high = self.freq_max / nyq
        high = min(high, 0.99)
        self._sos = butter(2, [low, high], btype='band', output='sos')

        # Per-vehicle buffers: {vehicle_id: VehicleColorBuffer}
        self._buffers = {}
        # Per-vehicle FFT results: {vehicle_id: FFTResult}
        self._results = {}

    def extract_color_energy(self, frame, bbox):
        """
        Trích xuất năng lượng đỏ + xanh từ bbox trên frame gốc.
        
        Args:
            frame: np.ndarray BGR (H, W, 3)
            bbox: [x1, y1, x2, y2]
            
        Returns:
            (red_energy, blue_energy)
        """
        h, w = frame.shape[:2]
        x1 = max(0, int(bbox[0]))
        y1 = max(0, int(bbox[1]))
        x2 = min(w, int(bbox[2]))
        y2 = min(h, int(bbox[3]))

        if x2 <= x1 or y2 <= y1:
            return 0.0, 0.0

        crop = frame[y1:y2, x1:x2]
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        v = hsv[:, :, 2].astype(np.float32) / 255.0

        # Red mask (2 ranges vì hue wraps around)
        rm1 = cv2.inRange(hsv, self.red1_low, self.red1_high)
        rm2 = cv2.inRange(hsv, self.red2_low, self.red2_high)
        red_mask = cv2.bitwise_or(rm1, rm2) > 0

        # Blue mask
        blue_mask = cv2.inRange(hsv, self.blue_low, self.blue_high) > 0

        red_e = float(np.sum(v[red_mask]))
        blue_e = float(np.sum(v[blue_mask]))

        return red_e, blue_e

    def process_tracks(self, frame, tracks):
        """
        Xử lý tất cả tracked vehicles trong 1 frame.
        
        Args:
            frame: np.ndarray BGR
            tracks: list of Track objects (from ByteTracker)
        """
        active_ids = set()

        for track in tracks:
            tid = track.id
            active_ids.add(tid)

            # Tạo buffer mới nếu chưa có
            if tid not in self._buffers:
                self._buffers[tid] = VehicleColorBuffer(maxlen=self.max_buffer_len)

            # Extract color energy
            bbox = track.bbox
            red_e, blue_e = self.extract_color_energy(frame, bbox)
            self._buffers[tid].append(red_e, blue_e)

            # Chạy FFT nếu đủ frames
            buf = self._buffers[tid]
            if buf.n_frames >= self.min_frames:
                self._results[tid] = self._compute_fft(buf)

        # Cleanup: xóa buffers cho vehicles đã mất track quá lâu
        stale_ids = [tid for tid in self._buffers if tid not in active_ids]
        for tid in stale_ids:
            # Giữ lại thêm 1 chút để tránh xóa quá sớm
            buf = self._buffers[tid]
            if buf.n_frames > 0:
                buf.red_energy.clear()
                buf.blue_energy.clear()
                buf.flash_energy.clear()
            del self._buffers[tid]
            if tid in self._results:
                del self._results[tid]

    def _compute_fft(self, buf):
        """Chạy FFT trên buffer năng lượng và trả về FFTResult."""
        result = FFTResult()
        result.n_frames = buf.n_frames

        flash = np.array(buf.flash_energy, dtype=np.float32)
        red = np.array(buf.red_energy, dtype=np.float32)
        blue = np.array(buf.blue_energy, dtype=np.float32)

        result.red_max = float(np.max(red)) if len(red) > 0 else 0.0
        result.blue_max = float(np.max(blue)) if len(blue) > 0 else 0.0

        if len(flash) < self.min_frames:
            return result

        # Áp dụng bộ lọc thông dải không trễ pha (zero-phase bandpass filter) để khử nhiễu
        try:
            # Nhờ sosfiltfilt lọc cả chiều xuôi và ngược nên pha giữ nguyên và khử nhiễu rất tốt
            sig = sosfiltfilt(self._sos, flash)
        except Exception:
            try:
                sig = detrend(flash)
            except Exception:
                sig = flash - np.mean(flash)
            sig = sig - np.mean(sig)

        # Hann window
        window = np.hanning(len(sig))
        sig_win = sig * window

        # FFT
        n_fft = len(sig_win)
        freqs = np.fft.rfftfreq(n_fft, d=1.0 / self.fps)
        mag = np.abs(np.fft.rfft(sig_win, n=n_fft))

        # Filter frequency range
        valid = (freqs >= self.freq_min) & (freqs <= self.freq_max)
        if not np.any(valid):
            return result

        freqs_v = freqs[valid]
        mag_v = mag[valid]

        peak_idx = np.argmax(mag_v)
        result.peak_freq = float(freqs_v[peak_idx])

        noise_floor = float(np.median(mag_v)) + 1e-8
        result.peak_ratio = float(mag_v[peak_idx]) / noise_floor

        # Quyết định: có phải đèn nhấp nháy không
        has_color = (result.red_max > self.color_energy_thresh or
                     result.blue_max > self.color_energy_thresh)
        has_peak = result.peak_ratio >= self.peak_ratio_thresh
        freq_valid = self.freq_min <= result.peak_freq <= self.freq_max

        result.is_strobe = has_color and has_peak and freq_valid

        return result

    def get_results(self):
        """
        Lấy FFT results cho tất cả vehicles.
        
        Returns:
            dict {vehicle_id: FFTResult}
        """
        return dict(self._results)

    def get_strobe_vehicles(self):
        """
        Lấy danh sách vehicle IDs có đèn nhấp nháy.
        
        Returns:
            list of vehicle_id
        """
        return [tid for tid, r in self._results.items() if r.is_strobe]

    def reset(self):
        """Reset tất cả buffers và results."""
        self._buffers.clear()
        self._results.clear()
