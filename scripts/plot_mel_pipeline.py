import os
import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display
from scipy.signal import butter, sosfilt

# ==========================================
# CẤU HÌNH PATH & THAM SỐ (TỪ NOTEBOOK)
# ==========================================
WAV_PATH = r"d:\Documents\20252\Final_project\Code\kiem_tra_du_lieu.wav"
SR = 22050
LO_FREQ = 500
HI_FREQ = 1800

N_FFT = 1024
HOP_LEN = 512
N_MELS = 64
FMIN = 300
FMAX = 3500

# ==========================================
# CÁC BƯỚC XỬ LÝ TÍN HIỆU
# ==========================================

print("1. Tải và lọc Band-pass âm thanh...")
y, sr = librosa.load(WAV_PATH, sr=SR, mono=True)
duration = librosa.get_duration(y=y, sr=sr)

# Hàm lọc Bandpass
def bandpass_filter(y, sr, lo=500, hi=1800):
    sos = butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    return sosfilt(sos, y)

y_filtered = bandpass_filter(y, sr, lo=LO_FREQ, hi=HI_FREQ)

# BƯỚC 1: Biến đổi Fourier thời gian ngắn (STFT)
print("2. Thực hiện biến đổi Fourier thời gian ngắn (STFT)...")
stft_complex = librosa.stft(y_filtered, n_fft=N_FFT, hop_length=HOP_LEN)
stft_mag = np.abs(stft_complex) # Lấy biên độ (Magnitude)
stft_db = librosa.amplitude_to_db(stft_mag, ref=np.max) # Chuyển sang thang dB để hiển thị rõ hơn

# BƯỚC 2: Ánh xạ sang thang Mel (Tạo bộ lọc Mel)
print("3. Khởi tạo bộ lọc Mel (Mel Filterbank)...")
mel_filters = librosa.filters.mel(sr=sr, n_fft=N_FFT, n_mels=N_MELS, fmin=FMIN, fmax=FMAX)

# BƯỚC 3: Tính phổ Mel (Nhân chập STFT Power với Bộ lọc Mel và Log)
print("4. Tính toán phổ Mel (Log-Mel Spectrogram)...")
mel_spec = librosa.feature.melspectrogram(
    y=y_filtered, sr=sr, n_fft=N_FFT, hop_length=HOP_LEN,
    n_mels=N_MELS, fmin=FMIN, fmax=FMAX, power=2.0
)
mel_db = librosa.power_to_db(mel_spec, ref=np.max)

# BƯỚC 4: Chuẩn hóa đầu ra của khối Mel Spectrogram
print("5. Chuẩn hóa đầu ra (Normalized)...")
def normalize(x):
    return (x - x.mean()) / (x.std() + 1e-6)
mel_norm = normalize(mel_db)

# ==========================================
# VẼ ĐỒ THỊ SO SÁNH 4 BƯỚC
# ==========================================
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Đồ thị 1: STFT
img1 = librosa.display.specshow(
    stft_db, sr=sr, hop_length=HOP_LEN, x_axis='time', y_axis='linear',
    ax=axes[0, 0], cmap='viridis'
)
axes[0, 0].set_title("Bước 1: Biến đổi Fourier thời gian ngắn (STFT)", fontsize=13, fontweight='bold')
axes[0, 0].set_xlabel("Thời gian (s)")
axes[0, 0].set_ylabel("Tần số (Hz)")
axes[0, 0].set_ylim(0, 4000) # Tập trung vào dải tần số thấp & trung
fig.colorbar(img1, ax=axes[0, 0], format='%+2.0f dB')

# Đồ thị 2: Mel Filterbank
freqs = np.fft.rfftfreq(N_FFT, d=1/sr)
for i in range(mel_filters.shape[0]):
    axes[0, 1].plot(freqs, mel_filters[i], alpha=0.7)
axes[0, 1].set_title("Bước 2: Bộ lọc Mel (Ánh xạ sang thang Mel)", fontsize=13, fontweight='bold')
axes[0, 1].set_xlabel("Tần số (Hz)")
axes[0, 1].set_ylabel("Hệ số lọc (Weight)")
axes[0, 1].set_xlim(FMIN - 100, FMAX + 100)
axes[0, 1].grid(True, alpha=0.3)

# Đồ thị 3: Phổ Mel (Log-Mel)
img3 = librosa.display.specshow(
    mel_db, sr=sr, hop_length=HOP_LEN, x_axis='time', y_axis='mel',
    fmin=FMIN, fmax=FMAX, ax=axes[1, 0], cmap='magma'
)
axes[1, 0].set_title("Bước 3: Phổ Mel (Log-Mel Spectrogram)", fontsize=13, fontweight='bold')
axes[1, 0].set_xlabel("Thời gian (s)")
axes[1, 0].set_ylabel("Tần số Mel (Hz)")
fig.colorbar(img3, ax=axes[1, 0], format='%+2.0f dB')

# Đồ thị 4: Đầu ra khối Mel Spectrogram (Normalized)
img4 = librosa.display.specshow(
    mel_norm, sr=sr, hop_length=HOP_LEN, x_axis='time', y_axis='mel',
    fmin=FMIN, fmax=FMAX, ax=axes[1, 1], cmap='coolwarm'
)
axes[1, 1].set_title("Bước 4: Đầu ra khối Mel Spectrogram (Normalized)", fontsize=13, fontweight='bold')
axes[1, 1].set_xlabel("Thời gian (s)")
axes[1, 1].set_ylabel("Tần số Mel (Hz)")
fig.colorbar(img4, ax=axes[1, 1])

plt.tight_layout()
plt.show()
