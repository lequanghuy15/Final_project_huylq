"""
Cấu hình hệ thống nhận diện xe ưu tiên.
Tất cả tham số tập trung tại đây để dễ chỉnh sửa.
"""
import os
import numpy as np

# ============================================================
# ĐƯỜNG DẪN MÔ HÌNH
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

YOLO_MODEL = os.path.join(PROJECT_ROOT, "models", "best_int8_imgsz640.tflite")
SIREN_MODEL = os.path.join(PROJECT_ROOT, "models", "siren_int8.tflite")

# ============================================================
# AUDIO — Microphone & Siren Detection
# ============================================================
AUDIO_SR = 22050              # Sample rate (Hz)
AUDIO_CHANNELS = 1            # Mono
AUDIO_CLIP_SEC = 2.0          # Cửa sổ phân tích (giây)
AUDIO_STRIDE_SEC = 0.17       # Bước trượt (giây) — ~6 inferences/giây
AUDIO_CLIP_LEN = int(AUDIO_CLIP_SEC * AUDIO_SR)   # 44100 samples
AUDIO_STRIDE_LEN = int(AUDIO_STRIDE_SEC * AUDIO_SR)  # 3748 samples
AUDIO_DEVICE_INDEX = None     # None = default mic, hoặc chỉ định index

# Bandpass filter
AUDIO_LO_FREQ = 500           # Hz
AUDIO_HI_FREQ = 1800          # Hz

# Feature extraction
AUDIO_PRE_EMPH = 0.97
AUDIO_N_FFT = 1024
AUDIO_HOP_LEN = 512
AUDIO_N_MELS = 64
AUDIO_N_MFCC = 40
AUDIO_FMIN = 300
AUDIO_FMAX = 3500
AUDIO_N_FRAMES = AUDIO_CLIP_LEN // AUDIO_HOP_LEN + 1  # 87

# Siren classification
SIREN_THRESHOLD = 0.5         # Ngưỡng softmax cho lớp siren
SIREN_VOTING_WINDOW = 5       # Số cửa sổ liên tiếp cho voting
SIREN_VOTING_MIN = 3          # Số vote tối thiểu để kích hoạt

# ============================================================
# VISION — Camera & Object Detection
# ============================================================
# Camera source: có thể là RTSP URL, device index, video file, hoặc "socket://host:port" cho ảnh RAW thô
CAMERA_SOURCE = 0             # 0 = webcam, "socket://0.0.0.0:8089" = LAN socket mode
CAMERA_FPS = 15               # FPS mong muốn
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# YOLO
YOLO_IMGSZ = 640
YOLO_CONF_THRESH = 0.25       # Ngưỡng confidence
YOLO_IOU_THRESH = 0.45        # Ngưỡng NMS IoU
YOLO_INTERVAL = 9             # Chạy YOLO mỗi N frames (phụ thuộc FPS/speed)

# ============================================================
# BYTETRACK — Multi-Object Tracking
# ============================================================
BT_TRACK_THRESH = 0.5         # Ngưỡng score cao cho first association
BT_TRACK_LOW = 0.1            # Ngưỡng score thấp cho second association
BT_MATCH_THRESH = 0.8         # Ngưỡng IoU cho matching
BT_MAX_TIME_LOST = 30         # Số frame tối đa giữ track khi mất detection

# ============================================================
# FFT COLOR ANALYSIS — Phân tích đèn nhấp nháy
# ============================================================
# Ngưỡng màu HSV cho đèn ưu tiên
HSV_RED1_LOW  = np.array([0,   80, 100])
HSV_RED1_HIGH = np.array([12, 255, 255])
HSV_RED2_LOW  = np.array([168, 80, 100])
HSV_RED2_HIGH = np.array([180, 255, 255])
HSV_BLUE_LOW  = np.array([90,  70, 100])
HSV_BLUE_HIGH = np.array([135, 255, 255])

# FFT
FFT_MIN_FRAMES = 30           # Tối thiểu frames trước khi chạy FFT (~2s@15FPS)
FFT_WINDOW_SEC = 5.0          # Cửa sổ tích lũy năng lượng (giây)
FFT_FREQ_MIN = 1.0            # Tần số nhấp nháy tối thiểu (Hz)
FFT_FREQ_MAX = 5.0            # Tần số nhấp nháy tối đa (Hz)
FFT_PEAK_RATIO_THRESH = 5.0   # Ngưỡng peak-to-noise ratio

# Ngưỡng năng lượng màu — xe phải có ít nhất mức này
COLOR_ENERGY_THRESH = 5.0     # Tổng năng lượng HSV tối thiểu

# ============================================================
# DECISION ENGINE — Máy trạng thái
# ============================================================
ALERT_TIMEOUT_SEC = 30.0      # Timeout từ ALERT → LISTENING nếu không còn còi
DECISION_INTERVAL_SEC = 0.5   # Tần suất kiểm tra quyết định

# ============================================================
# OUTPUT
# ============================================================
GPIO_ENABLED = False           # Bật/tắt GPIO output
GPIO_PIN = 17                  # BCM pin number cho relay/đèn cảnh báo
MQTT_ENABLED = False           # Bật/tắt MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "emergency_vehicle/detected"

# Logging
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_MAX_SIZE_MB = 100
LOG_BACKUP_COUNT = 7           # Giữ 7 file log cũ
LOG_SAVE_FRAMES = False        # Lưu frame khi phát hiện xe ưu tiên

# ============================================================
# SYSTEM
# ============================================================
THERMAL_WARN_TEMP = 75         # °C — cảnh báo nhiệt
THERMAL_THROTTLE_TEMP = 80     # °C — giảm tải khi quá nóng
