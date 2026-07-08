"""
mic_stream.py — Thu âm liên tục từ microphone bằng PyAudio.
Sử dụng ring buffer (collections.deque) để lưu trữ audio samples.
Thread-safe: deque tự đảm bảo atomic append/pop.
"""

import threading
import collections
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MicStream:
    """
    Thu âm liên tục, cung cấp audio chunks qua ring buffer.
    
    Usage:
        mic = MicStream(sr=22050, chunk_sec=0.17)
        mic.start()
        ...
        audio_2s = mic.get_window(duration_sec=2.0)
        ...
        mic.stop()
    """

    def __init__(self, sr=22050, channels=1, chunk_sec=0.17, device_index=None):
        self.sr = sr
        self.channels = channels
        self.chunk_size = int(chunk_sec * sr)  # Samples per chunk
        self.device_index = device_index

        # Ring buffer: giữ tối đa 10 giây audio
        max_chunks = int(10.0 / chunk_sec) + 1
        self._buffer = collections.deque(maxlen=max_chunks)

        self._stream = None
        self._pa = None
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        """Bắt đầu thu âm."""
        try:
            import pyaudio
        except ImportError:
            logger.error("PyAudio chưa được cài đặt. Chạy: pip install pyaudio")
            raise

        self._pa = pyaudio.PyAudio()
        self._running = True

        kwargs = {
            "format": pyaudio.paFloat32,
            "channels": self.channels,
            "rate": self.sr,
            "input": True,
            "frames_per_buffer": self.chunk_size,
            "stream_callback": self._audio_callback,
        }
        if self.device_index is not None:
            kwargs["input_device_index"] = self.device_index

        self._stream = self._pa.open(**kwargs)
        self._stream.start_stream()
        logger.info(
            f"Microphone started: SR={self.sr}, chunk={self.chunk_size} samples, "
            f"device={self.device_index or 'default'}"
        )

    def stop(self):
        """Dừng thu âm và giải phóng tài nguyên."""
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error closing stream: {e}")
            self._stream = None
        if self._pa is not None:
            self._pa.terminate()
            self._pa = None
        logger.info("Microphone stopped.")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback — chạy trên thread riêng của PyAudio."""
        import pyaudio
        if not self._running:
            return (None, pyaudio.paComplete)

        if status:
            logger.warning(f"Audio status: {status}")

        # Convert bytes → numpy float32
        audio_chunk = np.frombuffer(in_data, dtype=np.float32).copy()
        self._buffer.append(audio_chunk)

        return (None, pyaudio.paContinue)

    def get_window(self, duration_sec=2.0):
        """
        Lấy cửa sổ audio gần nhất với thời lượng duration_sec.
        
        Returns:
            np.ndarray float32 shape (N,) hoặc None nếu chưa đủ dữ liệu.
        """
        needed_samples = int(duration_sec * self.sr)
        
        # Snapshot buffer (thread-safe do deque)
        chunks = list(self._buffer)
        if not chunks:
            return None

        audio = np.concatenate(chunks)

        if len(audio) < needed_samples:
            return None  # Chưa đủ dữ liệu

        # Lấy N samples cuối cùng
        return audio[-needed_samples:]

    @property
    def is_running(self):
        return self._running and self._stream is not None

    def __del__(self):
        self.stop()
