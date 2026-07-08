import os
import numpy as np
import matplotlib.pyplot as plt
import librosa
import tensorflow as tf
from scipy.signal import butter, sosfilt
# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN & THAM SỐ
# ==========================================
SIREN_PURE_WAV = r"d:\Documents\20252\Final_project\Code\pure_siren.mp3"
SIREN_NOISY_WAV = r"d:\Documents\20252\Final_project\Code\kiem_tra_du_lieu.wav"
NON_SIREN_WAV = r"d:\Documents\20252\Final_project\Code\negative.wav"
TFLITE_PATH = r"d:\Documents\20252\Final_project\Code\siren_gru_int8.tflite"
WORKSPACE_DIR = r"d:\Documents\20252\Final_project\Code"
ARTIFACT_DIR = r"C:\Users\LENOVO\.gemini\antigravity-ide\brain\478b3952-d4c6-47d5-836d-36ffde20e6d0"
SR = 22050
LO_FREQ = 500
HI_FREQ = 1800
PRE_EMPH = 0.97
N_FFT = 1024
HOP_LEN = 512
N_MELS = 64
N_MFCC = 40
FMIN = 300
FMAX = 3500
CLIP_SEC = 2.0
CLIP_LEN = int(CLIP_SEC * SR)
STRIDE_SEC = 0.17
N_FRAMES = CLIP_LEN // HOP_LEN + 1
THRESHOLD = 0.5  # Ngưỡng phân loại chuẩn của TFLite
# ==========================================
# CÁC HÀM TIỀN XỬ LÝ
# ==========================================
def bandpass_filter(y, sr, lo=500, hi=1800):
    sos = butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    return sosfilt(sos, y)
def pre_emphasis(y, coeff=0.97):
    return np.append(y[0], y[1:] - coeff * y[:-1])
def normalize(x):
    return (x - x.mean()) / (x.std() + 1e-6)
def fix_len(x, T):
    if x.shape[1] >= T: return x[:, :T]
    return np.pad(x, ((0,0),(0,T-x.shape[1])))
def extract_features(seg, sr):
    seg_pe = pre_emphasis(seg, coeff=PRE_EMPH)
    # Mel
    S = librosa.feature.melspectrogram(y=seg_pe, sr=sr, n_fft=N_FFT, hop_length=HOP_LEN, n_mels=N_MELS, fmin=FMIN, fmax=FMAX, power=2.0)
    mel = normalize(librosa.power_to_db(S, ref=np.max))
    # MFCC
    mfcc_raw = librosa.feature.mfcc(y=seg_pe, sr=sr, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LEN, fmin=FMIN, fmax=FMAX)
    mfcc = normalize(mfcc_raw)
    
    return fix_len(mel, N_FRAMES).astype(np.float32), fix_len(mfcc, N_FRAMES).astype(np.float32)
# ==========================================
# CHẠY INFERENCE TFLITE LƯỢNG TỬ HÓA (INT8)
# ==========================================
def run_tflite_inference(y, sr, interpreter):
    y_bp = bandpass_filter(y, sr, lo=LO_FREQ, hi=HI_FREQ)
    stride = int(STRIDE_SEC * sr)
    
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    idx_mfcc = 0 if 'mfcc' in input_details[0]['name'] else 1
    idx_mel = 1 - idx_mfcc
    
    s_mfcc, z_mfcc = input_details[idx_mfcc]['quantization']
    s_mel, z_mel = input_details[idx_mel]['quantization']
    s_out, z_out = output_details[0]['quantization']
    
    probs, times = [], []
    
    for start in range(0, len(y_bp) - CLIP_LEN + 1, stride):
        seg = y_bp[start : start + CLIP_LEN]
        mel, mfcc = extract_features(seg, sr)
        
        mel_nhwc = mel[np.newaxis, :, :, np.newaxis]
        mfcc_nhwc = mfcc[np.newaxis, :, :, np.newaxis]
        
        # Lượng tử hóa đặc trưng đầu vào sang INT8
        q_mel = np.round(mel_nhwc / s_mel + z_mel).astype(np.int8)
        q_mfcc = np.round(mfcc_nhwc / s_mfcc + z_mfcc).astype(np.int8)
        
        interpreter.set_tensor(input_details[idx_mel]['index'], q_mel)
        interpreter.set_tensor(input_details[idx_mfcc]['index'], q_mfcc)
        interpreter.invoke()
        
        # Nhận kết quả và giải lượng tử hóa sang Float
        q_out = interpreter.get_tensor(output_details[0]['index'])
        logits = (q_out.astype(np.float32) - z_out) * s_out
        
        # Softmax để lấy xác suất của lớp Siren (chỉ số 1)
        probs_window = np.exp(logits) / np.sum(np.exp(logits), axis=-1, keepdims=True)
        probs.append(probs_window[0, 1])
        times.append((start + CLIP_LEN/2) / sr)
        
    return np.array(times), np.array(probs)
def apply_voting(probs, window_size=5, min_votes=3):
    voting_decisions = []
    for i in range(len(probs)):
        start_idx = max(0, i - window_size + 1)
        sub_probs = probs[start_idx : i + 1]
        votes = sum(sub_probs >= THRESHOLD)
        voting_decisions.append(1 if votes >= min_votes else 0)
    return np.array(voting_decisions)
# Khởi tạo mô hình
interpreter = tf.lite.Interpreter(model_path=TFLITE_PATH)
interpreter.allocate_tensors()
# Tải và xử lý các tệp âm thanh
siren_pure, _ = librosa.load(SIREN_PURE_WAV, sr=SR, mono=True)
siren_noisy, _ = librosa.load(SIREN_NOISY_WAV, sr=SR, mono=True)
ns_raw, _ = librosa.load(NON_SIREN_WAV, sr=SR, mono=True)

# Tự động lặp lại (tile) tín hiệu non-siren nếu thời gian quá ngắn (ví dụ: negative.wav chỉ có 2.0s)
# để hiển thị biểu đồ diễn tiến thời gian (sliding-window) ổn định hơn
MIN_DURATION_SEC = 10.0
if len(ns_raw) < MIN_DURATION_SEC * SR:
    ns_raw = np.tile(ns_raw, int(np.ceil(MIN_DURATION_SEC * SR / len(ns_raw))))
# Lấy kết quả
t_pure, p_pure = run_tflite_inference(siren_pure, SR, interpreter)
v_pure = apply_voting(p_pure)
t_noisy, p_noisy = run_tflite_inference(siren_noisy, SR, interpreter)
v_noisy = apply_voting(p_noisy)
t_ns, p_ns = run_tflite_inference(ns_raw, SR, interpreter)
v_ns = apply_voting(p_ns)
# ==========================================
# VẼ ĐỒ THỊ
# ==========================================
def plot_and_save(times, probs, votes, title, fig_name):
    plt.figure(figsize=(12, 5.5), dpi=300)
    plt.plot(times, probs, color='steelblue', label='Xác suất Siren (TFLite INT8)', linewidth=2.0)
    plt.axhline(y=THRESHOLD, color='crimson', linestyle='--', label=f'Ngưỡng phân loại ({THRESHOLD:.2f})')
    plt.fill_between(times, 0, votes * 0.1, color='forestgreen', alpha=0.3, step='mid', label='Hệ thống báo động (Voting 3/5)')
    
    plt.title(title, fontsize=13, fontweight='bold', pad=15)
    plt.xlabel("Thời gian (giây)")
    plt.ylabel("Xác suất / Trạng thái")
    plt.ylim(-0.05, 1.05)
    plt.xlim(times[0], times[-1])
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(loc='upper right')
    plt.tight_layout()
    
    # Lưu vào cả thư mục workspace và thư mục artifacts
    plt.savefig(os.path.join(WORKSPACE_DIR, fig_name), dpi=300)
    if os.path.exists(ARTIFACT_DIR):
        plt.savefig(os.path.join(ARTIFACT_DIR, fig_name), dpi=300)
    plt.close()
plot_and_save(t_pure, p_pure, v_pure, "Hình 3.21: Kết quả nhận diện trên tín hiệu Siren thuần (TFLite INT8)", "hinh_3_21.png")
plot_and_save(t_noisy, p_noisy, v_noisy, "Hình 3.22: Kết quả nhận diện Siren trong môi trường có nhiễu giao thông (TFLite INT8)", "hinh_3_22.png")
plot_and_save(t_ns, p_ns, v_ns, "Hình 3.23: Kết quả nhận diện trên tín hiệu Non-Siren (TFLite INT8)", "hinh_3_23.png")
print("Done!")