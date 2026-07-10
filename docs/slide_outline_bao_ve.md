# SƯỜN SLIDE BẢO VỆ ĐỒ ÁN TỐT NGHIỆP

**Đề tài:** Thiết kế hệ thống nhận diện xe ưu tiên tại biên sử dụng đa cảm biến phục vụ điều khiển giao thông thông minh
**SV:** Lê Quang Huy — 20222297 | **GVHD:** TS. Lê Minh Hoàng, PGS.TS. Nguyễn Thanh Hường

---

## Định hướng chung (đọc trước khi làm slide)

Hội đồng là hội đồng **Tự động hóa** → khung câu chuyện xuyên suốt là:

> **"Thiết kế một hệ ĐO đa cảm biến hoạt động 24/7 trên thiết bị nhúng: thu nhận tín hiệu → lọc/trích xuất đặc trưng → đo đại lượng có ích (xác suất còi, tần số nhấp nháy đèn, PNR) → hợp nhất bằng chứng → ra quyết định điều khiển (GPIO/MQTT)."**

- YOLO và mô hình phân loại còi chỉ là **một khối trong chuỗi đo** — mỗi mô hình tối đa 1 slide, nói về **vai trò, đầu vào/đầu ra, chi phí tài nguyên đã đo được**, KHÔNG đi sâu kiến trúc mạng.
- Trọng tâm "khoe": (1) chuỗi xử lý tín hiệu âm thanh (lấy mẫu → lọc thông dải → Mel/MFCC), (2) phép đo tần số đèn bằng lọc Butterworth zero-phase + FFT + chỉ số PNR, (3) logic hợp nhất 3 bằng chứng độc lập (máy trạng thái), (4) thiết kế phần cứng camera (Altium, CV25, điều khiển ống kính), (5) số liệu đo đạc thực trên Pi 4.
- Thời lượng trình bày cá nhân: **10–15 phút → 15–17 slide nội dung** (≈45–50 giây/slide), không kể bìa và backup.

**Quy tắc trình bày (bám tiêu chí chấm 1,5đ chất lượng slide):**
- **Đánh số trang mọi slide** (tiêu chí chấm ghi rõ; hội đồng hỏi "quay lại slide số N").
- Ít chữ, dùng **từ khóa** + sơ đồ khối/biểu đồ; mỗi slide 1 thông điệp.
- Slide sẽ **photo đen trắng 4 bản** → biểu đồ phải phân biệt được khi mất màu: dùng nét liền/đứt/chấm, marker khác nhau, không chỉ dựa vào màu; chữ trong hình ≥ cỡ 18.
- Chuẩn bị sẵn **video demo + phần mềm mô phỏng** để chiếu khi hội đồng yêu cầu (đã có `Xeuutien.mp4`, `Stable_light.mp4`, các video track YOLO).
- Đến sớm 30 phút thử máy chiếu; mô hình còi hú gọi thống nhất là **CNN-BiLSTM-Attention (INT8)** trong toàn bộ slide — khớp với quyển báo cáo. (Trước đây phải thay bằng GRU vì lỗi lượng tử hóa, nay đã quantize được BiLSTM trực tiếp; lưu ý cập nhật README/notebook trong repo cho khớp nếu hội đồng xem mã nguồn.)

---

## PHẦN MỞ ĐẦU (≈2 phút)

### Slide 1 — Trang bìa
- Tên trường/khoa, logo; tên đề tài; SV + MSSV; GVHD; hội đồng số; ngày bảo vệ.

### Slide 2 — Nội dung trình bày
- 5 mục: Đặt vấn đề & mục tiêu → Thiết kế hệ thống → Thiết kế các kênh đo → Kết quả thực nghiệm & đánh giá → Kết luận & hướng phát triển.

### Slide 3 — Đặt vấn đề & tính cấp thiết
- Ùn tắc đô thị → xe cứu thương/cứu hỏa/công an khó lưu thông; nhận biết hiện nay phụ thuộc con người.
- ITS cần **tự động phát hiện xe ưu tiên tại nút giao** để điều chỉnh pha đèn.
- Các hướng hiện có và hạn chế (1 bảng mini): GPS/RFID/V2X — cần hạ tầng, chi phí; chỉ camera — che khuất, nhiễu sáng; chỉ âm thanh — nhiễu ồn, không định vị.
- → Kết luận dẫn dắt: cần **hệ đo đa cảm biến tại biên**, giá rẻ, luôn hoạt động.

### Slide 4 — Mục tiêu & phạm vi (viết dạng chỉ tiêu ĐO ĐƯỢC — sẽ đối chiếu lại ở slide kết luận)
- Phát hiện xe ưu tiên bằng **3 bằng chứng độc lập**: còi hú + hiện diện phương tiện + tần số nhấp nháy đèn 1–5 Hz.
- Chạy 24/7 trên Raspberry Pi 4 (không GPU): RAM < 200 MB, luôn-lắng-nghe chỉ tốn ~5% CPU.
- Chu kỳ ra quyết định 0,5 s; cảnh báo qua GPIO/MQTT cho hệ điều khiển đèn.
- Tự thiết kế phần cứng camera (mạch + firmware) thay vì mua camera thương mại.
- Phạm vi: nút giao đơn, điều kiện ngày/đêm, một camera + một microphone.

---

## PHẦN THIẾT KẾ (≈5 phút)

### Slide 5 — Kiến trúc hệ thống tổng thể (1 sơ đồ khối lớn, slide "xương sống")
- Sơ đồ: [Mic INMP441] + [Camera CV25 tự thiết kế] → Pi 4 → 2 chuỗi đo (âm thanh / quang) → Khối hợp nhất & máy trạng thái → GPIO + MQTT + ảnh lưu trữ.
- Nhấn nguyên tắc **always-on tiết kiệm năng lượng**: chỉ mic chạy liên tục; kênh hình ảnh chỉ được "đánh thức" khi kênh âm thanh xác thực có còi.
- Nói miệng: đây là bài toán thiết kế hệ đo + logic điều khiển, mô hình học máy chỉ là 2 khối con.

### Slide 6 — Thiết kế phần cứng camera (thế mạnh với hội đồng TĐH — dành đủ thời gian)
- Ảnh 3D/ảnh thật board + sơ đồ 5 khối schematic (Altium): Nguồn — SoM CV25 — Ethernet — Giao tiếp cảm biến ảnh (MIPI/I2C) — Điều khiển ống kính.
- Cảm biến ảnh Sony (IMX415/IMX678 — ghi đúng theo quyển), ống kính varifocal: động cơ bước zoom/focus/P-Iris qua driver TMC.
- Firmware C++: GStreamer bắt JPEG → BGR 640×640 → TCP về Pi (header 4 byte + payload); lệnh UDP CALIB/ZOOM/FOCUS/IRIS chỉnh ống kính từ xa.

### Slide 7 — Kênh đo 1: Âm thanh còi hú (vẽ thành chuỗi xử lý tín hiệu)
- Chuỗi đo: Mic (fs = 22 050 Hz) → ring buffer, cửa sổ 2 s trượt 170 ms → **lọc thông dải Butterworth bậc 4, 500–1 800 Hz** (dải tần đặc trưng còi) → pre-emphasis 0,97 → **Mel(64) + MFCC(40)** → khối phân loại **CNN-BiLSTM-Attention INT8** (ghi đúng kích thước file .tflite hiện tại) → xác suất còi.
- **Voting 3/5 cửa sổ** để chống nhiễu giật cục → tín hiệu `siren_active` ổn định.
- Nói miệng: chọn fs, dải lọc, cửa sổ trượt là các quyết định đo lường — chuẩn bị trả lời "vì sao 22 050 Hz / vì sao 500–1 800 Hz" (Nyquist, phổ còi hú).

### Slide 8 — Kênh đo 2: Hiện diện & bám vết phương tiện (1 slide duy nhất cho phần "AI thị giác")
- Vai trò trong hệ đo: cung cấp **vùng quan tâm (ROI) ổn định theo từng xe** để đo tín hiệu đèn.
- Phát hiện: YOLO26n INT8 (2,7 MB) chạy **mỗi 9 khung hình**; giữa các lần chạy dùng **dự báo Kalman** để duy trì vị trí → tiết kiệm tài nguyên.
- Bám vết: ByteTrack rút gọn (Kalman 8 trạng thái + ghép cặp Hungarian 2 tầng) → mỗi xe một ID ổn định qua che khuất.
- KHÔNG trình bày kiến trúc mạng; chỉ nêu: 7 lớp phương tiện, kết quả huấn luyện để ở backup.

### Slide 9 — Kênh đo 3: Đo tần số nhấp nháy đèn ưu tiên (slide TRỌNG TÂM của đồ án)
- Xây dựng tín hiệu đo: crop ROI theo từng ID → HSV → **năng lượng màu đỏ (2 dải hue) + xanh dương** theo thời gian → chuỗi tín hiệu 1 chiều/xe (cửa sổ 5 s).
- Xử lý: **Butterworth thông dải 1–5 Hz, bậc 2, lọc zero-phase (filtfilt)** — triệt nhiễu rung bbox và trôi nền mà không méo pha → cửa sổ Hann → **FFT** → đỉnh phổ.
- Đại lượng đo: **tần số đỉnh f_peak** và **PNR = biên độ đỉnh / trung vị nhiễu nền**.
- Tiêu chí kết luận "đèn ưu tiên": năng lượng màu ≥ ngưỡng **VÀ** PNR ≥ 5 **VÀ** f_peak ∈ [1; 5] Hz.
- Hình: tín hiệu trước/sau lọc + phổ FFT (`so_sanh_loc_id13.png`).

### Slide 10 — Hợp nhất bằng chứng & ra quyết định (ngôn ngữ điều khiển — hội đồng TĐH thích)
- **Máy trạng thái 3 trạng thái, chu kỳ 0,5 s**: LISTENING (chỉ mic) → ALERT (có còi → bật camera + kênh quang) → CONFIRMED (còi + xe + đèn đúng tần số).
- Cơ chế lùi trạng thái: mất đèn/còi tạm thời chỉ lùi CONFIRMED→ALERT; 30 s không còi → về LISTENING (tắt camera, tiết kiệm năng lượng).
- Đầu ra chấp hành: GPIO BCM17 (relay/tủ đèn), bản tin MQTT JSON (timestamp, ID xe, f_peak, PNR), ảnh chú thích lưu log.
- Tính bền vững vận hành: tự kết nối lại camera (backoff mũ), giám sát nhiệt CPU (cảnh báo 75 °C, giảm tải 80 °C), log xoay vòng.

---

## PHẦN KẾT QUẢ THỰC NGHIỆM (≈4–5 phút — tiêu chí 4 điểm nằm ở đây, mỗi kết quả gắn với con số đo được)

### Slide 11 — Kết quả kênh âm thanh
- Kết quả huấn luyện/đánh giá trên tập dữ liệu còi (accuracy/precision/recall — lấy số từ Chương 3 quyển báo cáo).
- Đánh giá điều kiện thực tế: nhiễu giao thông, còi xa/gần (mục 3.2.5).
- Số liệu thời gian thực: suy diễn 71,6 ms < chu kỳ trượt 170 ms → đáp ứng thời gian thực với biên an toàn ~2,4×.
- Hình: mel-spectrogram còi hú (`mel_spectrogram_siren.png`), đường loss/accuracy để backup.

### Slide 12 — Kết quả kênh hình ảnh
- mAP/precision theo lớp trên ảnh thực tế (số từ mục 3.3, `yolo26n_train_results.csv`); ảnh khung hình có bbox + ID track.
- Bám vết qua che khuất: minh họa chuỗi frame track ID ổn định (cắt từ `yolo26_track_*.mp4`).
- Nhấn: suy diễn 599,7 ms/lần nhưng nhờ cơ chế "1 lần YOLO / 9 khung + Kalman" pipeline vẫn chạy thời gian thực.

### Slide 13 — Kết quả phép đo tần số đèn (slide kết quả đắt giá nhất — nói chậm)
- Bảng/hình 3 trường hợp đối chứng (mục 3.5): nguồn sáng không nhấp nháy → loại; xe thường ID 104 → loại nhờ ngưỡng năng lượng màu (dù PNR giả cao do rung); xe ưu tiên ID 13 → xác nhận, **f_peak = 2,34 Hz**.
- Hiệu quả bộ lọc zero-phase: **PNR 5,97 → 27,84 (+366 %)** so với chỉ detrend — đây là đóng góp xử lý tín hiệu chính, so sánh "trước/sau" ngay trên slide.
- Ảnh hưởng tham số camera (exposure — mục 3.5.6): phép đo vẫn bền vững (video `yolo26_exposure_sim_id13.mp4` để demo).

### Slide 14 — Kết quả hệ thống tích hợp & tài nguyên trên Pi 4
- Bảng benchmark (đo thực bằng `benchmark_pi.py`): RAM tổng ~164,5 MB; YOLO 599,7 ms; Siren 71,6 ms; ByteTrack 0,13–1,28 ms; HSV+FFT ~1,2 ms/track; decode 10,7 ms.
- Kết luận thời gian thực: nút thắt duy nhất là YOLO, đã xử lý bằng lịch suy diễn thưa; luôn-lắng-nghe ~5% CPU, ~40 MB.
- Ảnh chụp hệ thống chạy thật + frame CONFIRMED có nhãn "XE UU TIEN ID".
- (Nếu có) demo trực tiếp/video toàn trình: còi vang → ALERT → xe vào khung → CONFIRMED → GPIO sáng.

---

## PHẦN KẾT LUẬN (≈1,5 phút)

### Slide 15 — Kết luận: đối chiếu mục tiêu ↔ kết quả (bảng 2 cột, tick ✓)
- Mục tiêu ở Slide 4 từng dòng ↔ con số đạt được (3 bằng chứng ✓, RAM 164,5 MB < 200 MB ✓, chu kỳ 0,5 s ✓, phần cứng tự thiết kế ✓...).
- Đóng góp chính (3 gạch đầu dòng): (1) phương pháp đo tần số đèn ưu tiên bằng lọc zero-phase + FFT với chỉ số PNR (+366 %); (2) kiến trúc đa cảm biến luôn-lắng-nghe tiết kiệm năng lượng trên thiết bị nhúng; (3) tự thiết kế hoàn chỉnh phần cứng + firmware camera.
- Hạn chế (nói thẳng 1–2 ý, hội đồng đánh giá cao sự trung thực): mới thử nghiệm ở quy mô 1 nút giao/dữ liệu tự thu; YOLO ~0,6 s/lần suy diễn.

### Slide 16 — Hướng phát triển & Lời cảm ơn
- Kết nối trực tiếp tủ điều khiển đèn tín hiệu (chuẩn công nghiệp), thử nghiệm đa nút giao, ước lượng hướng/khoảng cách nguồn còi (mảng mic), tăng tốc suy diễn (NPU/Coral).
- "Em xin chân thành cảm ơn quý thầy cô. Em sẵn sàng nhận câu hỏi."

---

## SLIDE DỰ PHÒNG (BACKUP — sau slide cảm ơn, chỉ mở khi bị hỏi)

- B1. Tập dữ liệu: cấu trúc dataset âm thanh (positive/negative, train/val/test) và ảnh (7 lớp, ~320 MB), cách thu và gán nhãn.
- B2. Đường cong huấn luyện 2 mô hình (loss/mAP theo epoch) + lý do chọn/lượng tử hóa INT8 (giảm kích thước, chạy CPU Pi). Ghi chú quá trình: lượng tử hóa BiLSTM từng lỗi (toán tử LSTM/attention khó quantize trong TFLite) → giai đoạn đầu dùng GRU thay thế, sau đã khắc phục và quantize trực tiếp CNN-BiLSTM-Attention — câu chuyện tốt nếu bị hỏi "vì sao chọn kiến trúc này".
- B3. Toán bộ lọc: đáp ứng biên-pha Butterworth, vì sao zero-phase (filtfilt) — không méo pha tín hiệu nhấp nháy; chọn bậc lọc.
- B4. Chi tiết ByteTrack: vector trạng thái Kalman 8 chiều, ghép cặp 2 tầng theo IoU.
- B5. Giao thức truyền camera→Pi: khung TCP header 4 byte + 1 228 800 byte BGR, zero-copy phía Pi; lệnh UDP điều khiển ống kính.
- B6. Sơ đồ nguyên lý chi tiết từng sheet Altium (nguồn, SoM, Ethernet, sensor, lens control).
- B7. Bảng đầy đủ `benchmark_results.json` + điều kiện đo (Pi 4 rev 1.5, 1,8 GHz, backend suy diễn).

---

## PHÂN BỔ THỜI GIAN (mục tiêu 12–13 phút, trần 15)

| Phần | Slide | Thời gian |
|---|---|---|
| Mở đầu (vấn đề, mục tiêu) | 1–4 | 2,0′ |
| Kiến trúc + phần cứng | 5–6 | 2,5′ |
| Ba kênh đo + quyết định | 7–10 | 3,5′ |
| Kết quả thực nghiệm | 11–14 | 4,0′ |
| Kết luận + hướng phát triển | 15–16 | 1,5′ |

---

## CÂU HỎI HỘI ĐỒNG TĐH DỄ HỎI (chuẩn bị trả lời ngắn, đi thẳng vấn đề — tiêu chí 2,5đ)

1. **Vì sao lấy mẫu 22 050 Hz?** Phổ còi ưu tiên tập trung < 3,5 kHz; fs = 22 050 Hz thỏa Nyquist với biên rộng, cân bằng tải tính toán trên Pi.
2. **Vì sao lọc 500–1 800 Hz / 1–5 Hz?** Dải tần cơ bản của còi hú; đèn ưu tiên nhấp nháy 60–300 lần/phút = 1–5 Hz theo đặc tính đèn thực tế.
3. **Zero-phase filtering là gì, sao phải dùng?** Lọc xuôi rồi ngược → độ trễ pha bằng 0, không làm méo/dịch dạng sóng nhấp nháy trước khi FFT.
4. **PNR định nghĩa thế nào, sao ngưỡng = 5?** Biên độ đỉnh / trung vị nhiễu nền trong dải 1–5 Hz; ngưỡng chọn từ thực nghiệm đối chứng xe thường/xe ưu tiên (mục 3.5).
5. **Độ trễ từ lúc có còi đến lúc cảnh báo?** Voting 3/5 cửa sổ 170 ms (~0,5–0,85 s) + xác nhận đèn cần ≥ 30 frame (~2 s) + chu kỳ quyết định 0,5 s → nêu con số tổng và biện luận chấp nhận được cho điều khiển pha đèn.
6. **Sai số/độ phân giải phép đo tần số đèn?** Δf = fs_frame/N; với cửa sổ 5 s @15 FPS → độ phân giải ~0,2 Hz — đủ phân biệt trong dải 1–5 Hz.
7. **Nếu chỉ có còi mà không thấy đèn (che khuất)?** Hệ ở ALERT, chưa CONFIRMED — thiết kế chấp nhận trễ để tránh báo giả; nêu hướng mở rộng đa camera.
8. **Đầu ra ghép với tủ đèn tín hiệu thế nào?** GPIO relay khô + MQTT; hướng phát triển: chuẩn công nghiệp (Modbus/NTCIP).
9. **Nhiệt độ, hoạt động 24/7 có ổn định không?** Giám sát thermal zone, ngưỡng 75/80 °C, log xoay vòng, tự kết nối lại camera.
10. **Vì sao không dùng camera thương mại?** Chủ động điều khiển ống kính (zoom/focus/iris) phục vụ phép đo, làm chủ phần cứng, chi phí — và là khối lượng kỹ thuật của đồ án.
11. **Lượng tử hóa INT8 làm giảm độ chính xác bao nhiêu?** Nêu số so sánh float32 ↔ INT8 trên tập test (chuẩn bị sẵn từ notebook quantize); đổi lại giảm kích thước ~4× và chạy được trên CPU Pi. Nếu hỏi sâu: BiLSTM từng khó quantize (toán tử hồi tiếp), đã giải quyết được nên không phải hạ xuống GRU.
