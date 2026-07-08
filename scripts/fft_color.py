import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import detrend, find_peaks

# =========================
# CONFIG
# =========================

VIDEO_PATH = "emergency.mp4"  # sửa path
ROI = None  # hoặc (x1, y1, x2, y2)

FREQ_MIN = 1.0
FREQ_MAX = 10.0

RED1_LOW  = np.array([0,   80, 100])
RED1_HIGH = np.array([12, 255, 255])
RED2_LOW  = np.array([168, 80, 100])
RED2_HIGH = np.array([180, 255, 255])
BLUE_LOW  = np.array([90,  70, 100])
BLUE_HIGH = np.array([135, 255, 255])

# =========================
# HÀM PHỤ
# =========================

def norm_for_plot(x):
    x = np.asarray(x, dtype=np.float32)
    return (x - x.min()) / (x.max() - x.min() + 1e-8)

def moving_average(x, k=3):
    x = np.asarray(x, dtype=np.float32)
    if len(x) < k:
        return x
    return np.convolve(x, np.ones(k) / k, mode="same")

def fft_from_raw_energy(signal, fps, fmin=1.0, fmax=10.0, n_fft=None):
    """
    FFT trên tín hiệu năng lượng thật:
    - Không minmax trước FFT
    - Chỉ detrend + bỏ DC + Hann window
    """
    signal = np.asarray(signal, dtype=np.float32)

    sig = detrend(signal)
    sig = sig - np.mean(sig)

    window = np.hanning(len(sig))
    sig_win = sig * window

    if n_fft is None:
        n_fft = len(sig_win)

    freqs = np.fft.rfftfreq(n_fft, d=1/fps)
    mag = np.abs(np.fft.rfft(sig_win, n=n_fft))

    valid = (freqs >= fmin) & (freqs <= fmax)
    freqs_v = freqs[valid]
    mag_v = mag[valid]

    peak_idx = np.argmax(mag_v)
    peak_freq = freqs_v[peak_idx]
    peak_mag = mag_v[peak_idx]

    # Độ nổi bật peak
    noise_floor = np.median(mag_v) + 1e-8
    peak_ratio = peak_mag / noise_floor

    return freqs_v, mag_v, peak_freq, peak_ratio

# =========================
# ĐỌC VIDEO
# =========================

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)

red_energy = []
blue_energy = []
flash_energy = []
brightness = []
times = []

frame_id = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if ROI is not None:
        x1, y1, x2, y2 = ROI
        frame = frame[y1:y2, x1:x2]

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2].astype(np.float32) / 255.0

    red_mask_1 = cv2.inRange(hsv, RED1_LOW, RED1_HIGH)
    red_mask_2 = cv2.inRange(hsv, RED2_LOW, RED2_HIGH)
    red_mask = cv2.bitwise_or(red_mask_1, red_mask_2) > 0
    blue_mask = cv2.inRange(hsv, BLUE_LOW, BLUE_HIGH) > 0

    # Tổng năng lượng màu trên frame/ROI
    re = np.sum(v[red_mask])
    be = np.sum(v[blue_mask])
    fe = re + be

    red_energy.append(re)
    blue_energy.append(be)
    flash_energy.append(fe)
    brightness.append(np.mean(v))
    times.append(frame_id / fps)

    frame_id += 1

cap.release()

t = np.array(times)
red_energy = np.array(red_energy)
blue_energy = np.array(blue_energy)
flash_energy = np.array(flash_energy)
brightness = np.array(brightness)

# Làm mượt cực nhẹ để giảm nhiễu 1 frame
red_raw = moving_average(red_energy, k=3)
blue_raw = moving_average(blue_energy, k=3)
flash_raw = moving_average(flash_energy, k=3)

# =========================
# FFT
# =========================

red_freqs, red_mag, red_peak, red_ratio = fft_from_raw_energy(red_raw, fps, FREQ_MIN, FREQ_MAX)
blue_freqs, blue_mag, blue_peak, blue_ratio = fft_from_raw_energy(blue_raw, fps, FREQ_MIN, FREQ_MAX)
flash_freqs, flash_mag, flash_peak, flash_ratio = fft_from_raw_energy(flash_raw, fps, FREQ_MIN, FREQ_MAX)

# Peak count trên flash energy bản chuẩn hóa để kiểm chứng
flash_plot = norm_for_plot(flash_raw)
threshold = flash_plot.mean() + 0.5 * flash_plot.std()
min_distance = max(1, int(0.08 * fps))
peaks, _ = find_peaks(flash_plot, height=threshold, distance=min_distance)
peak_count_freq = len(peaks) / (len(flash_plot) / fps)

print("===== VIDEO INFO =====")
print(f"FPS: {fps:.2f}")
print(f"Số frame: {len(t)}")
print(f"Thời lượng: {len(t)/fps:.2f} s")

print("\n===== FFT RAW ENERGY =====")
print(f"Red peak   : {red_peak:.2f} Hz | peak/noise={red_ratio:.2f}")
print(f"Blue peak  : {blue_peak:.2f} Hz | peak/noise={blue_ratio:.2f}")
print(f"Flash peak : {flash_peak:.2f} Hz | peak/noise={flash_ratio:.2f}")

print("\n===== PEAK COUNT CHECK =====")
print(f"Số peak phát hiện: {len(peaks)}")
print(f"Tần số theo peak count: {peak_count_freq:.2f} Hz")

# =========================
# VẼ TÍN HIỆU
# =========================

plt.figure(figsize=(13, 5))
plt.plot(t, norm_for_plot(red_raw), label="Red energy")
plt.plot(t, norm_for_plot(blue_raw), label="Blue energy")
plt.plot(t, flash_plot, label="Red + Blue energy", linewidth=2)
plt.scatter(t[peaks], flash_plot[peaks], marker="x", s=70, label="Detected peaks")
plt.axhline(threshold, linestyle="--", alpha=0.6, label="Peak threshold")
plt.xlabel("Time (s)")
plt.ylabel("Normalized energy")
plt.title("Năng lượng màu đỏ/xanh theo thời gian")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

plt.figure(figsize=(12, 5))
plt.plot(red_freqs, red_mag, label=f"Red FFT | {red_peak:.2f} Hz")
plt.plot(blue_freqs, blue_mag, label=f"Blue FFT | {blue_peak:.2f} Hz")
plt.plot(flash_freqs, flash_mag, label=f"Flash FFT | {flash_peak:.2f} Hz", linewidth=2)
plt.axvline(flash_peak, linestyle="--", alpha=0.7)
plt.xlabel("Frequency (Hz)")
plt.ylabel("FFT magnitude")
plt.title("FFT trên năng lượng màu thực")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()