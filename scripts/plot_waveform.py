import os
import numpy as np
import matplotlib.pyplot as plt
import librosa
from scipy.signal import butter, sosfilt

# ==========================================
# CẤU HÌNH PATH & THAM SỐ
# ==========================================
WAV_PATH = r"d:\Documents\20252\Final_project\Code\kiem_tra_du_lieu.wav"
SR = 22050
LO_FREQ = 500
HI_FREQ = 1800

# Phân đoạn phóng to (Zoom) để quan sát chi tiết còi
ZOOM_START_SEC = 10.0
ZOOM_END_SEC = 12.0

# ==========================================
# 1. TẢI VÀ LỌC BỘ LỌC THÔNG DẢI
# ==========================================
print("Đang tải file âm thanh...")
y, sr = librosa.load(WAV_PATH, sr=SR, mono=True)
duration = librosa.get_duration(y=y, sr=sr)
print(f"-> Tải thành công! SR: {sr} Hz, Thời lượng: {duration:.2f} s")

# Bộ lọc Band-pass Butterworth bậc 4
def bandpass_filter(y, sr, lo=500, hi=1800):
    sos = butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    return sosfilt(sos, y)

print("Đang áp dụng bộ lọc Band-pass...")
y_filtered = bandpass_filter(y, sr, lo=LO_FREQ, hi=HI_FREQ)

# Trích xuất phân đoạn zoom
zoom_start_idx = int(ZOOM_START_SEC * sr)
zoom_end_idx = int(ZOOM_END_SEC * sr)
y_zoom_raw = y[zoom_start_idx:zoom_end_idx]
y_zoom_filt = y_filtered[zoom_start_idx:zoom_end_idx]

# Trục thời gian
time_axis_full = np.linspace(0, duration, len(y))
time_axis_zoom = np.linspace(ZOOM_START_SEC, ZOOM_END_SEC, len(y_zoom_raw))

# ==========================================
# 2. VẼ ĐỒ THỊ DẠNG SÓNG
# ==========================================
fig, axes = plt.subplots(3, 1, figsize=(15, 12))

# Đồ thị 1: Waveform gốc
axes[0].plot(time_axis_full, y, color='steelblue', alpha=0.7, label='Raw Waveform')
axes[0].set_title("1. Toàn bộ dạng sóng (Waveform) gốc - Raw Signal", fontsize=13, fontweight='bold')
axes[0].set_xlabel("Thời gian (s)")
axes[0].set_ylabel("Biên độ")
axes[0].grid(True, alpha=0.3)
axes[0].set_xlim(0, duration)

# Đồ thị 2: Waveform sau khi lọc Band-pass
axes[1].plot(time_axis_full, y_filtered, color='forestgreen', alpha=0.7, label='Filtered Waveform')
axes[1].set_title(f"2. Toàn bộ dạng sóng sau lọc Band-pass ({LO_FREQ}-{HI_FREQ} Hz) - Làm nổi bật còi ưu tiên", fontsize=13, fontweight='bold')
axes[1].set_xlabel("Thời gian (s)")
axes[1].set_ylabel("Biên độ")
axes[1].grid(True, alpha=0.3)
axes[1].set_xlim(0, duration)

# Đồ thị 3: Phóng to so sánh
axes[2].plot(time_axis_zoom, y_zoom_raw, color='steelblue', alpha=0.5, label='Raw (Gốc)', linewidth=1.5)
axes[2].plot(time_axis_zoom, y_zoom_filt, color='crimson', alpha=0.8, label='Filtered (Đã lọc)', linewidth=1.5)
axes[2].set_title(f"3. Phóng to một phân đoạn ngắn (Từ {ZOOM_START_SEC}s đến {ZOOM_END_SEC}s)", fontsize=13, fontweight='bold')
axes[2].set_xlabel("Thời gian (s)")
axes[2].set_ylabel("Biên độ")
axes[2].grid(True, alpha=0.3)
axes[2].set_xlim(ZOOM_START_SEC, ZOOM_END_SEC)
axes[2].legend(loc='upper right')

plt.tight_layout()
plt.show()
