# Hệ Thống Nhận Diện Xe Ưu Tiên 24/7 Trên Thiết Bị Nhúng

**Đồ án tốt nghiệp** — Lê Quang Huy — MSSV 20222297
📄 Báo cáo đầy đủ: [`ĐATN-LeQuangHuy-20222297.pdf`](./ĐATN-LeQuangHuy-20222297.pdf)

Dự án triển khai hệ thống nhận diện xe ưu tiên (xe cứu thương, cứu hỏa, cảnh sát) hoạt động liên tục 24/7 trên phần cứng giới hạn tài nguyên (Raspberry Pi 4), kết hợp:

- **Camera IP tự thiết kế** dựa trên SoM Ambarella CV25 (cảm biến IMX415, ống kính có động cơ zoom/focus/iris), tự phát triển mạch (Altium) và firmware (C++/GStreamer).
- **Phân tích đa phương tiện** trên Pi: âm thanh còi hú (Siren INT8) + hình ảnh phương tiện (YOLO26n INT8) + tần số nhấp nháy đèn ưu tiên (FFT trên ROI màu sau lọc Butterworth).

Toàn bộ hệ thống được thiết kế theo nguyên tắc **always-on nhưng tiết kiệm năng lượng**: chỉ có microphone + mô hình GRU siêu nhẹ chạy liên tục; camera, YOLO, tracker và FFT chỉ được đánh thức khi có bằng chứng âm thanh về còi ưu tiên.

---

## 🌟 Tính Năng Nổi Bật

- **Always-on Audio Monitor**: Microphone hoạt động liên tục với tải CPU cực thấp (~5%) và RAM ~40MB nhờ mô hình Siren GRU INT8 siêu nhẹ (~5.5MB).
- **Tiết Kiệm Năng Lượng Động**: Camera và bộ suy diễn YOLO chỉ kích hoạt khi xác thực có tiếng còi hú qua cơ chế Voting (3/5 cửa sổ 2 giây, trượt mỗi 170ms).
- **Lọc Thông Dải Zero-phase (Butterworth)**: Triệt tiêu nhiễu chuyển động và rung lắc bounding box, nâng cao chỉ số PNR (Peak-to-Noise Ratio) của tần số đèn ưu tiên thêm **+366%** so với detrend thông thường.
- **Tối Ưu Nhúng**: Hỗ trợ suy diễn hoàn toàn bằng TFLite INT8 Quantized, tự động giảm tải (throttling) khi CPU quá nhiệt (> 80°C), tự động kết nối lại camera (exponential backoff) và quay vòng log file (100MB × 7 bản).
- **Camera Tự Thiết Kế**: Board camera CV25 (Ambarella/Oclea) với ống kính varifocal điều khiển động cơ bước (zoom/focus/P-Iris) qua driver TMC, truyền frame JPEG→BGR 640×640 về Pi qua TCP LAN với zero-copy decode ở phía Pi.
- **Máy trạng thái 3 lớp bằng chứng**: chỉ xác nhận "xe ưu tiên" khi có đủ cả 3 tín hiệu độc lập (còi + hiện diện phương tiện + đèn nhấp nháy đúng tần số), giảm false positive so với chỉ dùng 1 cảm biến.

---

## 📐 Kiến Trúc Hệ Thống

### 1. Luồng dữ liệu tổng quan (Camera cứng → Raspberry Pi)

```
   [ 📷 Camera CV25 (Ambarella SoM, IMX415, ống kính động cơ) ]
                │
                │  GStreamer: olcamerasrc ! image/jpeg (WxH@FPS cấu hình)
                │  ! queue leaky=downstream ! appsink (src/media/stream.cpp)
                ▼
        OpenCV imdecode (JPEG → BGR) → resize 640×640
                │
                │  Header 4-byte Big-Endian (uint32 = 1,228,800 bytes)
                │  + Payload BGR thô (src/media/tcp_client.cpp)
                ▼
   ============ TCP, LAN Ethernet, cổng mặc định 8089 =============
                ▼
      [ 🖥️ Raspberry Pi 4 — deploy/vision/camera.py, socket:// mode ]
                    (zero-copy: np.frombuffer + reshape, không decode ảnh)

   UDP :8080 — lệnh text "CALIB" / "ZOOM:<n>" / "FOCUS:<n>" / "IRIS:<pos>"
   ─────────────────────────────────────────────► điều khiển ống kính qua
                                                    TmcDriver (ioctl /dev/tmc_dev0)
```

> Khi chưa có board camera thật, `scripts/stream_from_pc.py` giả lập vai trò camera CV25 bằng cách phát MJPEG qua HTTP từ webcam/video file trên PC.

### 2. Pipeline xử lý trên Raspberry Pi (3 threads song song)

```
                       [ 🎤 Microphone (Always-on, PyAudio callback) ]
                                      │  ring buffer (deque, 10s)
                                      ▼
                 Bandpass 500–1800Hz → Pre-emphasis 0.97
                                      │
                          Mel(64) + MFCC(40) @ 22050Hz, n_fft=1024, hop=512
                                      ▼
                    Quantize INT8 → Siren GRU (2 input: mel, mfcc)
                                      │
                        Dequantize → Softmax → prob[siren]
                                      ▼
                Voting: 5 cửa sổ gần nhất (170ms/cửa sổ), cần ≥3 vote > 0.5
                                      │
                                      ▼
                           siren_active? ──────────────────────┐
                                      │                        │
                 ┌────────────────────┴───────────┐            │
              YES│                              NO│            │
                 ▼                                ▼            │
         [ 📷 Bật Camera ]                 [ 📷 Tắt Camera ]    │
                 │                         [ Reset Tracker+FFT ]│
                 ▼                         (State: LISTENING)   │
       YOLO26n INT8 (mỗi 9 frames, letterbox 640×640 + NMS)     │
                 │                                              │
                 ▼                                              │
     ByteTrack-lite (Kalman 8-state + Hungarian 2-tầng IoU)     │
      score cao (≥0.5) ↔ track, rồi score thấp (≥0.1) ↔ leftover│
                 │                                              │
                 ▼                                              │
     HSV Extraction theo bbox mỗi track (2 dải đỏ + 1 dải xanh) │
                 │                                              │
                 ▼                                              │
    Zero-phase Butterworth Bandpass 1–5Hz (sosfiltfilt, order 2)│
                 │                                              │
                 ▼                                              │
      Hann window → rFFT → Peak/Noise-floor ratio (PNR)         │
                 │                                              │
                 ▼                                              │
       🚨 is_strobe = (màu đủ mạnh) & (PNR ≥ 5) & (freq ∈[1,5]Hz)│
                 │                                              │
                 ▼                                              │
   ┌─────────────────────────────────────────────────────────────┐
   │        Decision Engine (State Machine, chu kỳ 0.5s)         │
   │  LISTENING → ALERT (có còi) → CONFIRMED (còi+xe+đèn nháy)   │
   │  timeout 30s không còi → quay về LISTENING                 │
   └─────────────────────────────────────────────────────────────┘
                 │
                 ▼
   🚨 CONFIRMED → GPIO (BCM17) HIGH + MQTT publish + lưu frame chú thích
```

---

## 🔬 Chi Tiết Kỹ Thuật Từng Khối Xử Lý

### a) Audio — Siren Detection (`deploy/audio/`)

| Bước | Mô tả | Tham số (`config.py`) |
|---|---|---|
| Thu âm | PyAudio callback ghi liên tục vào ring buffer `deque` (giữ tối đa 10s), lấy cửa sổ 2s mới nhất mỗi lần suy diễn | `AUDIO_SR=22050`, `AUDIO_CLIP_SEC=2.0`, `AUDIO_STRIDE_SEC=0.17` (~6 lần suy diễn/giây) |
| Bandpass | Butterworth bậc 4, dải 500–1800Hz (dải tần đặc trưng của còi ưu tiên) | `AUDIO_LO_FREQ=500`, `AUDIO_HI_FREQ=1800` |
| Pre-emphasis | `y[n] = x[n] - 0.97·x[n-1]` để tăng cường tần số cao | `AUDIO_PRE_EMPH=0.97` |
| Feature extraction | Mel-spectrogram (64 bands, dB, chuẩn hóa z-score) **và** MFCC (40 hệ số) tính song song bằng `librosa`, cùng `n_fft=1024`, `hop_length=512`, `fmin=300`, `fmax=3500` → 87 frame thời gian | `AUDIO_N_MELS=64`, `AUDIO_N_MFCC=40` |
| Suy diễn | 2 tensor input (mel, mfcc) được quantize theo scale/zero-point riêng của model, đưa vào Siren GRU INT8 (TFLite), output dequantize rồi softmax 2 lớp (nhiễu nền / còi ưu tiên) | Model: `models/siren_int8.tflite` |
| Voting | Giữ lịch sử 5 xác suất gần nhất; kích hoạt `siren_active=True` khi ≥3/5 lần vượt ngưỡng 0.5 — chống nhiễu giật cục (flickering) | `SIREN_THRESHOLD=0.5`, `SIREN_VOTING_WINDOW=5`, `SIREN_VOTING_MIN=3` |

### b) Vision — Nhận diện & bám vết phương tiện (`deploy/vision/`)

- **`camera.py`**: hỗ trợ 2 chế độ — OpenCV (`webcam`/`RTSP`/file video, tự reconnect với backoff mũ tối đa 60s) và **Socket mode** (`socket://host:port`) nhận ảnh RAW BGR 640×640 trực tiếp từ camera CV25, không cần decode/resize (zero-CPU), đọc đúng giao thức header 4-byte mà `camera_source/src/media/tcp_client.cpp` tạo ra.
- **`yolo_detector.py`**: tiền xử lý bằng **letterbox resize** (giữ tỷ lệ khung hình, pad giá trị 114) về 640×640, quantize theo dtype input của model (int8/uint8/float32), hậu xử lý hỗ trợ cả 2 dạng output YOLO (`[N,6]` hoặc `[6,N]`, có/không tách class score), NMS tự viết theo từng ảnh. `YOLO_INTERVAL=9` — chỉ chạy suy diễn đầy đủ mỗi 9 frame, các frame còn lại chỉ dùng bước dự đoán Kalman (`predict_only`) để giữ track mượt mà không tốn suy diễn.
- **`byte_tracker.py`**: cài đặt rút gọn ByteTrack — Kalman filter 8 chiều trạng thái `[cx, cy, aspect_ratio, h, vx, vy, va, vh]` (mô hình vận tốc không đổi) + ghép cặp 2 tầng bằng thuật toán Hungarian (`scipy.optimize.linear_sum_assignment`): tầng 1 ghép detection điểm cao (`BT_TRACK_THRESH=0.5`) với track theo IoU (`BT_MATCH_THRESH=0.8`), tầng 2 ghép phần dư với detection điểm thấp (`BT_TRACK_LOW=0.1`) để giữ track qua occlusion. Track bị xoá sau `BT_MAX_TIME_LOST=30` frame không khớp.
- **`color_analyzer.py`**: với mỗi track, crop bbox từ frame gốc → BGR2HSV → tính năng lượng 2 dải đỏ (do hue đỏ "bọc vòng" 0°/360°: `[0,12]` và `[168,180]`) và 1 dải xanh (`[90,135]`), năng lượng = tổng kênh V trong vùng mask. Tích lũy vào deque riêng theo từng `vehicle_id` (tối đa `FFT_WINDOW_SEC=5s × fps` frame).

### c) FFT — Phát hiện đèn nhấp nháy (`color_analyzer.py::_compute_fft`)

1. Khi buffer đủ `FFT_MIN_FRAMES=30` frame (~2s@15FPS), áp **Butterworth bandpass bậc 2, dải 1–5Hz** theo kiểu **zero-phase** (`scipy.signal.sosfiltfilt` — lọc xuôi rồi ngược để triệt tiêu độ trễ pha, tránh méo dạng sóng nhấp nháy).
2. Nhân cửa sổ Hann để giảm rò rỉ phổ (spectral leakage), sau đó `np.fft.rfft`.
3. Giới hạn phổ trong dải `[FFT_FREQ_MIN, FFT_FREQ_MAX] = [1, 5]Hz`, tìm đỉnh và tính **PNR = biên độ đỉnh / trung vị nhiễu nền**.
4. Xe được gắn nhãn `is_strobe=True` **chỉ khi cả 3 điều kiện** đều thoả: năng lượng màu đủ lớn (`COLOR_ENERGY_THRESH=5.0` — loại xe không có đèn ưu tiên dù có rung/nhiễu), `PNR ≥ FFT_PEAK_RATIO_THRESH=5.0`, và tần số đỉnh nằm trong dải hợp lệ. Đây chính là lớp bảo vệ giúp loại xe thường (vd. ID 104 trong thực nghiệm) dù có nhiễu chuyển động.

### d) Decision Engine & Output (`deploy/decision/`)

- **State machine 3 trạng thái** (`engine.py`): `LISTENING` (chỉ mic) → `ALERT` (có còi, camera+YOLO+FFT bật) → `CONFIRMED` (còi + phương tiện hiện diện + có track nhấp nháy). Timeout `ALERT_TIMEOUT_SEC=30s` không nghe còi sẽ đưa hệ thống về `LISTENING` từ bất kỳ trạng thái nào; mất tín hiệu đèn/còi tạm thời từ `CONFIRMED` chỉ lùi về `ALERT` (không mất toàn bộ ngữ cảnh ngay lập tức).
- **Output** (`output.py`): khi `CONFIRMED`, đồng thời (1) set GPIO BCM pin 17 lên HIGH (relay/còi cảnh báo, tuỳ chọn bật qua `GPIO_ENABLED`), (2) publish JSON (`timestamp`, `vehicle_ids`, `peak_freq`, `peak_ratio`) lên topic MQTT `emergency_vehicle/detected` (tuỳ chọn), (3) lưu 1 frame đã vẽ bounding box + nhãn `🚨 XE UU TIEN ID: <id>` vào `deploy/logs/`.
- **Giám sát nhiệt & log**: đọc `/sys/class/thermal/thermal_zone0/temp` mỗi 10s, cảnh báo khi > `THERMAL_WARN_TEMP=75°C` và gợi ý giảm tải khi > `THERMAL_THROTTLE_TEMP=80°C`; log xoay vòng tối đa 100MB × 7 file (`RotatingFileHandler`).

---

## 📂 Cấu Trúc Thư Mục Dự Án

```
├── camera_source/            # Firmware C++ chạy trên board camera CV25 (Ambarella/Oclea)
│   ├── CMakeLists.txt        # Cross-compile bằng Ambarella SDK (GStreamer + OpenCV)
│   ├── config/
│   │   └── camera_config.json# IP/port Pi, độ phân giải, framerate, thiết bị TMC
│   ├── src/
│   │   ├── main.cpp          # Entry point: capture -> TCP client -> UDP lens listener
│   │   ├── media/            # GStreamer capture pipeline (olcamerasrc→JPEG) & TCP client gửi frame
│   │   ├── control/          # TmcDriver (ioctl /dev/tmc_dev0) & LensController (zoom/focus/iris)
│   │   └── utils/            # Logger, config loader (parser JSON tối giản, không phụ thuộc thư viện ngoài)
│   └── tools/
│       └── test_receiver.py  # Server TCP giả lập Pi để kiểm tra luồng camera độc lập
│
├── hardware/
│   └── CV25_Camera_DATN/     # Project Altium Designer thiết kế mạch camera (schematic + PCB lib)
│       ├── 01_Power.SchDoc, 02_CV25_SOM.SchDoc, 03_Ethernet.SchDoc,
│       │   04_InterfaceSensor.SchDoc, 05_LensControl.SchDoc, ImageSensor_IMX415.SchDoc
│       └── MyLib.SchLib / MyLib.PcbLib
│
├── deploy/                   # Mã nguồn triển khai trên Raspberry Pi
│   ├── main.py                # Entry point khởi chạy 3 threads xử lý + decision loop
│   ├── config.py              # Cấu hình toàn bộ tham số hệ thống (ngưỡng, chân GPIO, đường dẫn model)
│   ├── audio/
│   │   ├── mic_stream.py      # Ring buffer thu âm từ PyAudio (callback-based, thread-safe)
│   │   └── siren_detector.py  # Bandpass + Mel/MFCC extraction & GRU INT8 inference + voting
│   ├── vision/
│   │   ├── camera.py          # Nhận luồng ảnh Socket (zero-copy)/OpenCV, tự động kết nối lại
│   │   ├── yolo_detector.py   # YOLO26n INT8 TFLite: letterbox, quantize, NMS
│   │   ├── byte_tracker.py    # Kalman 8-state + Hungarian 2-tầng (ByteTrack rút gọn)
│   │   └── color_analyzer.py  # Trích xuất HSV theo track, lọc Butterworth & phân tích FFT
│   └── decision/
│       ├── engine.py          # Máy trạng thái (LISTENING -> ALERT -> CONFIRMED)
│       └── output.py          # Điều khiển GPIO (BCM 17), MQTT & xuất ảnh chụp chú thích
│
├── models/                   # Mô hình đã lượng tử hóa, sẵn sàng triển khai (INT8 TFLite)
│   ├── best_int8_imgsz640.tflite   # YOLO26n phát hiện phương tiện (2.7MB)
│   └── siren_int8.tflite           # Siren GRU phân loại còi hú (5.5MB)
│
├── notebooks/                 # Notebooks huấn luyện mô hình (chạy trên Colab/PC)
│   ├── train_siren_gru.ipynb        # Huấn luyện mô hình Siren GRU (PyTorch)
│   ├── train_yolo26n.ipynb          # Huấn luyện mô hình YOLOv26n trên tập dữ liệu ảnh
│   └── siren_quantize_int8.ipynb    # Lượng tử hóa mô hình Siren GRU sang dạng INT8 (2 input: mel+mfcc)
│
├── data/                      # Cấu trúc dữ liệu huấn luyện (dữ liệu nặng không đưa lên git)
│   ├── audio/                 # Dataset còi hú: audio/ (positive/negative), features/, split/ (train/val/test csv)
│   └── vision/data.yaml       # Mô tả tập dữ liệu YOLO: 7 lớp (bike, motorbike, car, truck, bus, pedestrian, exception)
│
├── scripts/                   # Công cụ hỗ trợ đo đạc & minh họa cho báo cáo
│   ├── stream_from_pc.py      # Giả lập phát luồng camera MJPEG từ PC sang Pi qua LAN (khi chưa có board thật)
│   ├── benchmark_pi.py        # Đo RAM/FPS/độ trễ suy diễn từng khối trên Pi thật
│   ├── run_tflite_interface.py# Test suy diễn TFLite độc lập ngoài pipeline chính
│   ├── fft_color.py            # Vẽ minh hoạ tín hiệu màu trước/sau lọc + phổ FFT
│   ├── plot_mel_pipeline.py, plot_waveform.py  # Vẽ waveform/mel-spectrogram cho báo cáo
│   └── send_frames_sample.py
│
├── docs/images/               # Hình ảnh/biểu đồ dùng trong báo cáo (hình 3.x)
├── benchmark_results.json     # Kết quả benchmark RAM/FPS/latency trên Raspberry Pi 4 thật
├── yolo26n_train_results.csv  # Log huấn luyện YOLO26n (loss/mAP theo epoch)
├── requirements.txt            # Thư viện Python cần cho deploy/ trên Pi
├── ĐATN-LeQuangHuy-20222297.pdf # Báo cáo đồ án tốt nghiệp đầy đủ
└── .gitignore
```

---

## 🔌 Phần Cứng — Camera CV25 (`hardware/`, `camera_source/`)

### Thiết kế mạch (Altium Designer)

Camera được tự thiết kế mạch quanh SoM Ambarella CV25, gồm 5 khối schematic chính (project tại `hardware/CV25_Camera_DATN/`):

| Sheet | Nội dung |
|---|---|
| `01_Power` | Khối nguồn cấp cho SoM và ngoại vi |
| `02_CV25_SOM` | Khối gắn kết System-on-Module CV25 (Ambarella/Oclea) |
| `03_Ethernet` | Giao tiếp Ethernet — kênh truyền frame về Pi |
| `04_InterfaceSensor` | Giao tiếp giữa SoM và cảm biến ảnh (MIPI CSI, I2C control) |
| `05_LensControl` | Driver động cơ bước (TMC) điều khiển ống kính: zoom, focus, P-Iris |
| `ImageSensor_IMX415` | Cảm biến ảnh Sony IMX415 |

Thư viện linh kiện/footprint tự tạo nằm trong `MyLib.SchLib` (symbol) và `MyLib.PcbLib` (footprint).

### Firmware (`camera_source/`)

Firmware là một daemon C++17 chạy trên Linux của SoM (Ambarella/Oclea SDK), gồm 3 tác vụ song song khởi động từ `main.cpp`:

1. **Capture thread (main loop)**: pipeline GStreamer `olcamerasrc name=ol ol.src_2 ! image/jpeg,width=W,height=H,framerate=F/1 ! queue leaky=downstream max-size-buffers=1 ! appsink` kéo JPEG mới nhất (bỏ khung cũ nếu xử lý không kịp — tránh trễ tích lũy), OpenCV `imdecode` thành BGR rồi resize 640×640 trước khi gửi.
2. **TCP client**: kết nối tới `pi_ip:pi_port` (đọc từ `config/camera_config.json`), gửi mỗi frame kèm header 4-byte Big-Endian chứa kích thước payload (`1,228,800` bytes = 640×640×3), tự động thử kết nối lại nếu gửi thất bại.
3. **UDP command listener** (cổng `8080`, chạy trên thread riêng): nhận lệnh text điều khiển ống kính và chuyển tới `LensController` → `TmcDriver` (mở character device `/dev/tmc_dev0`, điều khiển qua `ioctl`):
   - `CALIB` — hiệu chuẩn về vị trí 0 cho cả 3 động cơ (zoom/focus/P-Iris).
   - `ZOOM:<n>` / `FOCUS:<n>` — di chuyển tương đối `n` bước (dấu quyết định chiều: zoom in/out, focus near/far).
   - `IRIS:<pos>` — đặt vị trí khẩu độ tuyệt đối.

Build (cross-compile cho board hoặc native để test trên PC):

```bash
cd camera_source
mkdir -p build && cd build
cmake .. -DCROSS_COMPILE=ON   # dùng Ambarella SDK tại /opt/ambarella-sdk (toolchain aarch64-oclea-linux)
                              # hoặc -DCROSS_COMPILE=OFF để build native, cần OpenCV + GStreamer dev trên PC
make -j$(nproc)
```

Yêu cầu hệ thống để build: `pkg-config`, `glib-2.0`, `gstreamer-1.0` (+ `-base`, `-app`), `opencv4` — cross-compile cần thêm sysroot của Ambarella SDK đặt tại `/opt/ambarella-sdk`.

Kiểm thử luồng TCP độc lập (không cần chạy `deploy/main.py`) bằng script Python giả lập server Pi:

```bash
python camera_source/tools/test_receiver.py   # lắng nghe cổng 8089, lưu vài frame debug vào received_frames/
```

---

## 🚀 Hướng Dẫn Triển Khai Chạy Thực Tế Trên Raspberry Pi

### 1. Nguồn video đầu vào (chọn 1 trong 2)

**a) Camera CV25 thật**: build & chạy firmware trong `camera_source/` trên board, cấu hình đúng IP/port của Pi trong `camera_source/config/camera_config.json`. Trên Pi, chạy `main.py` với `--camera socket://0.0.0.0:8089` để nhận đúng giao thức RAW từ firmware.

**b) Giả lập từ PC** (khi chưa có board camera):
```bash
# Stream webcam mặc định
python scripts/stream_from_pc.py --source 0 --port 5000

# Stream một file video test có sẵn
python scripts/stream_from_pc.py --source Xeuutien.mp4 --port 5000 --fps 15
```
Luồng video sẽ được phân phối tại địa chỉ: `http://<IP_PC>:5000/video_feed`.

### 2. Chuẩn Bị Trên Raspberry Pi
Copy thư mục `deploy/` và `models/` lên Pi:
```bash
scp -r deploy/ models/ huylq@huylq.local:~/
```

SSH vào Pi, cài đặt các thư viện cần thiết:
```bash
ssh huylq@huylq.local
cd ~/deploy
pip install -r ../requirements.txt
# PyAudio cần PortAudio hệ thống:
sudo apt install portaudio19-dev
```

> `requirements.txt` gồm: `numpy`, `opencv-python`, `scipy`, `librosa` (trích xuất Mel/MFCC), `pyaudio` (thu âm), `paho-mqtt` (output tuỳ chọn), `tflite-runtime` (suy diễn INT8). Nếu `tflite-runtime` không có bản build cho kiến trúc Pi, `deploy/audio/siren_detector.py` và `deploy/vision/yolo_detector.py` tự động thử `ai_edge_litert` rồi mới tới `tensorflow.lite` như phương án dự phòng.

### 3. Khởi Chạy Trên Pi
```bash
# Chạy nhận diện đầy đủ, nhận ảnh RAW trực tiếp từ camera CV25 qua socket
python3 main.py --camera socket://0.0.0.0:8089

# Chạy nhận diện đầy đủ, lấy luồng MJPEG giả lập từ PC (khi test)
python3 main.py --camera http://<IP_PC>:5000/video_feed

# Chạy test độc lập Vision (Không cần còi hú, tự động kích hoạt camera & FFT)
python3 main.py --camera http://<IP_PC>:5000/video_feed --force-alert

# Debug: dùng video file có sẵn, tắt audio
python3 main.py --video ../Xeuutien.mp4 --no-audio --force-alert
```

Toàn bộ log (console + file xoay vòng `deploy/logs/system.log`) in trạng thái hệ thống mỗi 10 giây, gồm state hiện tại, xác suất còi, danh sách ID xe đang nhấp nháy, số frame vision đã xử lý và nhiệt độ CPU.

---

## 🧠 Huấn Luyện & Lượng Tử Hóa Mô Hình (`notebooks/`)

| Notebook | Mục đích |
|---|---|
| `train_siren_gru.ipynb` | Huấn luyện mô hình GRU phân loại còi hú (PyTorch), input là cặp Mel-spectrogram + MFCC, trên `data/audio/` |
| `train_yolo26n.ipynb` | Huấn luyện YOLO26n nhận diện 7 lớp phương tiện (`bike, motorbike, car, truck, bus, pedestrian, exception`) trên `data/vision/` (`data.yaml`) |
| `siren_quantize_int8.ipynb` | Lượng tử hóa mô hình Siren GRU (2 input mel+mfcc) sang TFLite INT8 |

> Thư mục `data/` chỉ giữ cấu trúc và file mô tả (`data.yaml`), dữ liệu ảnh/âm thanh gốc không đưa lên git do dung lượng lớn (tổng ~320MB tập ảnh YOLO, chưa kể tập audio).

---

## 📊 Kết Quả Thực Nghiệm

### Lọc đèn nhấp nháy (FFT)

Bằng việc áp dụng bộ lọc **Butterworth Bandpass Zero-phase (`sosfiltfilt`)**, tỷ số Peak-to-Noise Ratio (PNR) tăng vọt giúp hệ thống không bỏ sót mục tiêu trong điều kiện nhiễu chuyển động mạnh:

- **Xe ưu tiên ID 13**: PNR tăng từ **5.97** lên **27.84** (**+366.1%**). Đỉnh tần số chớp đèn tại **2.34 Hz** nổi bật hoàn toàn khỏi nhiễu nền.
- **Xe thường ID 104**: Bị loại bỏ chính xác nhờ lớp bảo vệ năng lượng màu tuyệt đối (`COLOR_ENERGY_THRESH`), dù có PNR giả cao do rung lắc.
- **Trực quan hóa**: Khi phát hiện xe ưu tiên, một frame chụp đã vẽ sẵn **Bounding Box** và nhãn thông tin dạng `🚨 XE UU TIEN ID: <id>` sẽ tự động được xuất ra thư mục `deploy/logs/`.

### Hiệu năng trên Raspberry Pi 4 (`benchmark_results.json`, đo bằng `scripts/benchmark_pi.py`)

Cấu hình đo: Raspberry Pi 4 Model B Rev 1.5, RAM 3.8GB, CPU tối đa 1800MHz, Python 3.13.5, backend `ai_edge_litert`.

| Chỉ số | Giá trị |
|---|---|
| RAM baseline (chưa load model) | 33.7 MB |
| RAM sau khi nạp YOLO INT8 | 78.9 MB (+45.2 MB) |
| RAM sau khi nạp cả Siren GRU INT8 | 104.3 MB → tổng ước tính **~164.5 MB** |
| YOLO26n INT8 (640×640) | 599.7 ms/lần suy diễn (~1.67 FPS) — chạy mỗi 9 frame (`YOLO_INTERVAL`) nên không nghẽn pipeline hiển thị |
| Siren GRU INT8 | 71.6 ms/lần suy diễn (đủ nhanh so với chu kỳ 170ms) |
| ByteTrack-lite | 0.13 ms (5 tracks) → 1.28 ms (50 tracks) |
| HSV extraction + FFT | 0.48 ms + 0.75 ms mỗi track |
| Giải mã & resize video (1280×720@15FPS) | decode 10.7 ms (93.3 FPS khả dụng), resize 1.7 ms |

Các con số này cho thấy nút thắt cổ chai duy nhất là suy diễn YOLO (~600ms); toàn bộ kiến trúc "chỉ chạy YOLO mỗi N frame + giữ track bằng Kalman ở các frame còn lại" chính là để dung hoà giữa độ chính xác bám vết và giới hạn phần cứng của Pi 4.

---

## 📄 Báo Cáo Đồ Án

Toàn bộ cơ sở lý thuyết, quá trình huấn luyện/lượng tử hóa mô hình, thiết kế phần cứng và kết quả thực nghiệm chi tiết được trình bày trong [`ĐATN-LeQuangHuy-20222297.pdf`](./ĐATN-LeQuangHuy-20222297.pdf).
