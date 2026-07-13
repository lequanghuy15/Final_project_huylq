# TRIỂN KHAI HỆ THỐNG LÊN RASPBERRY PI 4 (khớp slide bảo vệ)

Sơ đồ kết nối vật lý:

```
[Camera CV25] --Ethernet GigE--> [Raspberry Pi 4] --GPIO17--> relay/tủ đèn
   TCP client → Pi:8089                |  ^-- INMP441 qua I2S (GPIO18/19/20)
   UDP server :8080 (nhận lệnh lens)   |--> MQTT broker (tùy chọn, qua mạng)
```

Vai trò mạng (đúng theo `deploy/vision/camera.py` và `camera_source/`): **Pi là TCP SERVER**, **CV25 là client** tự kết nối và thử lại theo từng frame → thứ tự bật nguồn hai thiết bị không quan trọng.

⚠️ **Lưu ý quan trọng**: cổng 8089 **không mở thường trực** — `vision_thread` chỉ gọi `camera.start()` (bind+listen) khi có còi kích hoạt (`camera_active=True`) và đóng hẳn server socket khi hết còi. Đây là thiết kế chủ đích: lúc nhàn rỗi, client không gửi được → luồng 147 Mbit/s bị chặn từ nguồn (tiết kiệm cả băng thông, không chỉ CPU). Trễ đánh thức ~0,1 s (client thử lại mỗi ~67 ms) — không đáng kể so với 2 s FFT cần tích lũy. Hệ quả khi kiểm tra: `ss -tlnp | grep 8089` chỉ thấy cổng khi đang ALERT hoặc chạy `--force-alert`.

---

## Bước 1 — Hệ điều hành

- Raspberry Pi OS **64-bit Lite** (headless). `sudo apt update && sudo apt full-upgrade`.
- Pi 4 có sẵn Gigabit Ethernet — **bắt buộc GigE** vì luồng BGR thô 640×640×3 @15 FPS ≈ 147 Mbit/s (chuẩn 100 Mbps nghẽn từ ~10 FPS). Dây Cat5e trở lên.

## Bước 2 — Microphone INMP441 (I2S)

INMP441 không phải mic USB — phải bật I2S bằng device tree:

1. Đấu dây: VDD→3V3, GND→GND, **SCK→GPIO18, WS→GPIO19, SD→GPIO20**, L/R→GND (kênh trái).
2. `/boot/firmware/config.txt`: thêm
   ```
   dtparam=i2s=on
   dtoverlay=googlevoicehat-soundcard
   ```
   (overlay soundcard I2S thông dụng cho INMP441) → reboot.
3. Kiểm tra: `arecord -l` thấy card mới; thu thử `arecord -D plughw:<card>,0 -f S32_LE -r 22050 -c 2 -d 3 test.wav`.
4. Nếu mic không phải thiết bị mặc định: đặt `AUDIO_DEVICE_INDEX` trong `deploy/config.py` (PyAudio liệt kê index qua ALSA).

## Bước 3 — Cài phần mềm

```bash
sudo apt install -y python3-pip portaudio19-dev
# từ PC:
scp -r deploy/ models/ requirements.txt huylq@<pi>:~/
# trên Pi:
pip3 install -r requirements.txt
```

Runtime suy luận INT8: code tự thử theo chuỗi `tflite-runtime` → `ai_edge_litert` → `tensorflow.lite`. Với Python 3.13 (như máy benchmark) dùng `pip3 install ai-edge-litert`.

## Bước 4 — Mạng với camera CV25

1. Đặt IP tĩnh cho `eth0` của Pi (ví dụ `192.168.10.2/24`).
2. Trên board camera, sửa `camera_source/config/camera_config.json`: `pi_ip = 192.168.10.2`, `pi_port = 8089`, độ phân giải/FPS.
3. Kiểm tra độc lập luồng frame (không cần chạy cả hệ): `python3 camera_source/tools/test_receiver.py` trên Pi — nhận và lưu vài frame debug.
4. Lệnh chỉnh ống kính gửi từ Pi tới camera: UDP `<ip_camera>:8080`, text `CALIB` / `ZOOM:<n>` / `FOCUS:<n>` / `IRIS:<pos>`.

## Bước 5 — Cấu hình `deploy/config.py`

| Khóa | Giá trị triển khai |
|---|---|
| `CAMERA_SOURCE` | `"socket://0.0.0.0:8089"` |
| `AUDIO_DEVICE_INDEX` | index card I2S (hoặc `None` nếu là default) |
| `GPIO_ENABLED` | `True` nếu nối relay chân BCM17 (**mặc định đang False**) |
| `MQTT_ENABLED` + broker/topic | `True` nếu ghép hệ điều khiển đèn (**mặc định False**) |

## Bước 6 — Nghiệm thu từng tầng (chạy tay trước khi cho chạy dịch vụ)

```bash
cd ~/deploy
# 1. Vision độc lập bằng video mẫu (không cần mic/camera):
python3 main.py --video ../Xeuutien.mp4 --no-audio --force-alert
# 2. Camera thật, ép kích hoạt vision (không cần còi):
python3 main.py --camera socket://0.0.0.0:8089 --force-alert
# 3. Chạy đầy đủ:
python3 main.py --camera socket://0.0.0.0:8089
```

Theo dõi `deploy/logs/system.log` — mỗi 10 s in: trạng thái (LISTENING/ALERT/CONFIRMED), xác suất còi, danh sách ID nhấp nháy, số frame đã xử lý, nhiệt độ CPU. Frame CONFIRMED có chú thích lưu trong `deploy/logs/`.

## Bước 7 — Chạy 24/7 bằng systemd (file `deploy/emergency-vehicle.service`)

```bash
sudo cp ~/deploy/emergency-vehicle.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now emergency-vehicle
journalctl -u emergency-vehicle -f     # xem log trực tiếp
```

Phân công trách nhiệm vận hành: **ứng dụng tự lo** giám sát nhiệt (cảnh báo 75°C/giảm tải 80°C), tự kết nối lại camera (backoff mũ), xoay vòng log (100 MB × 7); **systemd chỉ lo** tiến trình chết thì dựng lại (`Restart=always`) và khởi động cùng hệ điều hành sau khi có mạng.

## Bước 8 — Vận hành & đo đạc

- Đo lại hiệu năng trên máy thật: `python3 scripts/benchmark_pi.py` → cập nhật bảng tài nguyên (slide 18/29).
- Bản tin MQTT khi CONFIRMED: topic `emergency_vehicle/detected`, JSON gồm timestamp, danh sách ID, tần số đỉnh, tỷ số đỉnh.
- Sự cố thường gặp: không có tiếng → kiểm `arecord -l` + `AUDIO_DEVICE_INDEX`; không có frame → kiểm IP trong `camera_config.json` và test bằng `test_receiver.py`; FPS thấp → kiểm link GigE (`ethtool eth0` phải 1000Mb/s).
