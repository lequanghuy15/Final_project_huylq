"""
siren_detector.py — Nhận diện còi ưu tiên bằng Siren GRU INT8.
Bao gồm: bandpass filter, pre-emphasis, MFCC+Mel extraction,
TFLite INT8 inference, và sliding window voting.
"""

import numpy as np
import logging
from scipy.signal import butter, sosfilt

logger = logging.getLogger(__name__)


def _load_tflite_interpreter(model_path):
    """Load TFLite interpreter (tương thích nhiều backend)."""
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


class SirenDetector:
    """
    Phát hiện còi ưu tiên từ audio buffer.
    
    Pipeline:
        audio → bandpass → pre-emphasis → MFCC + Mel → quantize INT8
        → Siren GRU invoke → dequantize → softmax → voting
    """

    def __init__(self, model_path, sr=22050, lo_freq=500, hi_freq=1800,
                 pre_emph=0.97, n_fft=1024, hop_len=512, n_mels=64,
                 n_mfcc=40, fmin=300, fmax=3500, clip_sec=2.0,
                 threshold=0.5, voting_window=5, voting_min=3):
        
        self.sr = sr
        self.lo_freq = lo_freq
        self.hi_freq = hi_freq
        self.pre_emph = pre_emph
        self.n_fft = n_fft
        self.hop_len = hop_len
        self.n_mels = n_mels
        self.n_mfcc = n_mfcc
        self.fmin = fmin
        self.fmax = fmax
        self.clip_len = int(clip_sec * sr)
        self.n_frames = self.clip_len // hop_len + 1
        self.threshold = threshold
        self.voting_window = voting_window
        self.voting_min = voting_min

        # Precompute bandpass filter
        self._sos = butter(4, [lo_freq, hi_freq], btype='band', fs=sr, output='sos')

        # Load model
        self._interp = _load_tflite_interpreter(model_path)
        self._interp.allocate_tensors()

        inp = self._interp.get_input_details()
        out = self._interp.get_output_details()

        # Xác định thứ tự input (mfcc vs mel)
        self._idx_mfcc = 0 if 'mfcc' in inp[0]['name'] else 1
        self._idx_mel = 1 - self._idx_mfcc

        self._s_mfcc, self._z_mfcc = inp[self._idx_mfcc]['quantization']
        self._s_mel, self._z_mel = inp[self._idx_mel]['quantization']
        self._s_out, self._z_out = out[0]['quantization']

        self._inp_details = inp
        self._out_details = out

        # Voting history
        self._prob_history = []
        self._siren_active = False

        logger.info(f"SirenDetector loaded: {model_path}")
        logger.info(f"  Input MFCC: {inp[self._idx_mfcc]['shape']}")
        logger.info(f"  Input Mel:  {inp[self._idx_mel]['shape']}")

    def _bandpass(self, y):
        return sosfilt(self._sos, y)

    def _pre_emphasis(self, y):
        return np.append(y[0], y[1:] - self.pre_emph * y[:-1])

    @staticmethod
    def _normalize(x):
        return (x - x.mean()) / (x.std() + 1e-6)

    def _fix_len(self, x):
        T = self.n_frames
        if x.shape[1] >= T:
            return x[:, :T]
        return np.pad(x, ((0, 0), (0, T - x.shape[1])))

    def _extract_features(self, seg):
        """Trích xuất Mel spectrogram và MFCC từ đoạn audio."""
        import librosa

        seg_pe = self._pre_emphasis(seg)

        S = librosa.feature.melspectrogram(
            y=seg_pe, sr=self.sr, n_fft=self.n_fft, hop_length=self.hop_len,
            n_mels=self.n_mels, fmin=self.fmin, fmax=self.fmax, power=2.0
        )
        mel = self._normalize(librosa.power_to_db(S, ref=np.max))

        mfcc_raw = librosa.feature.mfcc(
            y=seg_pe, sr=self.sr, n_mfcc=self.n_mfcc, n_fft=self.n_fft,
            hop_length=self.hop_len, fmin=self.fmin, fmax=self.fmax
        )
        mfcc = self._normalize(mfcc_raw)

        mel = self._fix_len(mel).astype(np.float32)
        mfcc = self._fix_len(mfcc).astype(np.float32)

        return mel, mfcc

    def process_window(self, audio_window):
        """
        Xử lý 1 cửa sổ audio 2 giây.
        
        Args:
            audio_window: np.ndarray float32, shape (clip_len,)
            
        Returns:
            (siren_prob, siren_active): xác suất siren và trạng thái voting
        """
        if len(audio_window) < self.clip_len:
            return 0.0, self._siren_active

        # 1. Bandpass filter
        y_bp = self._bandpass(audio_window)

        # 2. Extract features
        mel, mfcc = self._extract_features(y_bp)

        # 3. Quantize → INT8
        mel_nhwc = mel[np.newaxis, :, :, np.newaxis]
        mfcc_nhwc = mfcc[np.newaxis, :, :, np.newaxis]

        q_mel = np.round(mel_nhwc / self._s_mel + self._z_mel).astype(np.int8)
        q_mfcc = np.round(mfcc_nhwc / self._s_mfcc + self._z_mfcc).astype(np.int8)

        # 4. Invoke
        self._interp.set_tensor(
            self._inp_details[self._idx_mel]['index'], q_mel
        )
        self._interp.set_tensor(
            self._inp_details[self._idx_mfcc]['index'], q_mfcc
        )
        self._interp.invoke()

        # 5. Dequantize → softmax
        q_out = self._interp.get_tensor(self._out_details[0]['index'])
        logits = (q_out.astype(np.float32) - self._z_out) * self._s_out
        exp_logits = np.exp(logits - np.max(logits))  # Numerically stable
        probs = exp_logits / np.sum(exp_logits)
        siren_prob = float(probs[0, 1])

        # 6. Voting
        self._prob_history.append(siren_prob)
        if len(self._prob_history) > self.voting_window:
            self._prob_history.pop(0)

        votes = sum(1 for p in self._prob_history if p >= self.threshold)
        self._siren_active = votes >= self.voting_min

        return siren_prob, self._siren_active

    @property
    def siren_active(self):
        """Trạng thái hiện tại: có đang nghe thấy còi ưu tiên không."""
        return self._siren_active

    @property
    def last_prob(self):
        """Xác suất siren gần nhất."""
        return self._prob_history[-1] if self._prob_history else 0.0

    def reset(self):
        """Reset voting history."""
        self._prob_history.clear()
        self._siren_active = False
