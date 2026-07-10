# RÀ SOÁT QUYỂN ĐỒ ÁN (ĐATN-LeQuangHuy-20222297.pdf) — VIỆC CẦN HOÀN THIỆN

Đối chiếu quyển PDF ↔ code trong repo ↔ sườn slide. Xếp theo mức độ ưu tiên.
(Không lặp lại các mục đã ghi ở "GHI CHÚ ĐANG TREO" trong `slide_outline_bao_ve.md`.)

> **ĐÃ CHỐT LẠI (10/07, lần 2): slide bám đúng quyển hiện tại.** Phần cứng camera CV25, lọc Butterworth zero-phase/PNR, máy trạng thái + GPIO/MQTT, điều khiển ống kính vòng kín → **KHÔNG đưa vào quyển**, gom thành mục "Triển khai mở rộng sau đồ án" trên slide (15–16) với tinh thần "nộp quyển xong vẫn tiếp tục nghiên cứu".
> Hệ quả: các mục **A1, A2, A4 tự giải quyết** (không còn là mâu thuẫn — là phần phát triển sau); kế hoạch E chỉ còn hiệu lực **bước 1, 5, 6** (chốt số nhất quán, điền số thiếu, quét lỗi); **bước 2, 3, 4 HỦY**. Mục F giữ nguyên làm nội dung slide mở rộng + phương án cài đặt.

---

## A. MÂU THUẪN NỘI DUNG QUYỂN ↔ REPO — PHẢI CHỐT TRƯỚC KHI LÀM SLIDE

### A1. Quyển KHÔNG có phần cứng camera CV25 tự thiết kế ⚠️ (lớn nhất)
- Mục 2.8.4 của quyển viết ngược hẳn: *"đề tài không tập trung vào quá trình thiết kế hay xử lý tín hiệu mức thấp của cảm biến hình ảnh"*, chọn "camera RGB thương mại".
- Trong khi repo có cả `hardware/` (Altium CV25) + `camera_source/` (firmware C++), README coi đây là điểm nhấn, và **Slide 6 trong sườn đang dành riêng cho phần cứng này**.
- → Phải chọn 1 trong 2: (a) nếu quyển còn sửa được → bổ sung mục thiết kế camera vào Chương 2 + cập nhật 2.8.4; (b) nếu quyển đã nộp → hỏi GVHD có được trình bày phần cứng như "khối lượng phát triển thêm" không, hoặc bỏ/thu nhỏ Slide 6. Trình bày slide một đằng, quyển một nẻo là lỗi nặng nhất có thể mắc.
- Liên quan: tóm tắt đầu quyển ghi cảm biến ảnh **IMX678**, nhưng schematic Altium là **IMX415** (`ImageSensor_IMX415.SchDoc`), Chương 2 lại chỉ nói "camera RGB" chung chung → thống nhất một tên.

### A2. Bộ lọc Butterworth zero-phase 1–5 Hz + PNR +366% không có trong quyển ⚠️
- Thiết kế 2.6 của quyển chỉ có: trung bình kênh R/B → FFT → tỷ số đỉnh/trung vị. **Không có** Butterworth bandpass zero-phase, không có cửa sổ Hann, Chương 3.5 không có con số PNR 5,97 → 27,84 (+366%).
- Đây lại đang là **slide kết quả đắt giá nhất (Slide 13)** và là đóng góp xử lý tín hiệu chính theo README. Hình `so_sanh_loc_*.png` có sẵn trong `docs/images/` nhưng chưa vào quyển.
- → Nếu quyển còn sửa: thêm bước lọc vào 2.6.3/2.6.4 + kết quả so sánh trước/sau lọc vào 3.5. Nếu không: slide chỉ được nói ở mức "cải tiến sau khi hoàn thành quyển", nói rõ miệng khi trình bày.

### A3. Dải tần bộ lọc âm thanh — 4 con số khác nhau ở 4 chỗ ⚠️
| Vị trí | Giá trị |
|---|---|
| Quyển 1.1.2 & 2.3.1 (đặc điểm còi) | 500–1600 Hz |
| Quyển 2.3.2b (thiết kế bộ lọc) | **600–1500 Hz** |
| Quyển 3.2.2a (đánh giá bộ lọc) | **300–3500 Hz** (nhầm với dải Mel fmin/fmax!) |
| Code `deploy/config.py` | **500–1800 Hz** |
- → Chốt một dải duy nhất (theo code là 500–1800 Hz), sửa nhất quán cả quyển + slide. Hội đồng đo lường hỏi "bộ lọc của em dải bao nhiêu" mà 3 chỗ 3 số là mất điểm ngay. Lưu ý 300–3500 Hz là dải Mel filter bank, đừng gọi nó là "dải lọc thông dải" như ở 3.2.2a và chú thích Hình 3-2.

### A4. Máy trạng thái, GPIO/MQTT, giám sát nhiệt không có trong quyển
- Quyển 2.7/3.6 chỉ mô tả logic AND 3 điều kiện + quy trình 9 bước, **không có** state machine LISTENING→ALERT→CONFIRMED, không có đầu ra GPIO/MQTT, không có giám sát nhiệt/log — những thứ Slide 10 đang mô tả theo code.
- → Cùng cách xử lý như A2: bổ sung quyển nếu còn sửa được, hoặc điều chỉnh Slide 10 mô tả đúng như quyển (kích hoạt theo sự kiện + điều kiện AND) và chỉ nói thêm miệng về state machine trong code.

### A5. Tên mô hình trong benchmark
- Quyển Bảng 3-6 ghi "CNN-BiLSTM-Attention: 71,6 ms" — trùng đúng con số README gán cho "Siren GRU INT8". Cùng một phép đo nhưng hai tài liệu gán hai tên mô hình khác nhau.
- → Sau khi benchmark lại với BiLSTM INT8 mới (đã note), cập nhật cả Bảng 3-5/3-6 trong quyển (nếu sửa được) và slide, dùng một tên duy nhất.

### A6. Tên đề tài không nhất quán trong chính quyển
- Bìa + tóm tắt: "…tại biên **sử dụng đa cảm biến** phục vụ…". Trang Nhiệm vụ, mục 1.1 Đặt vấn đề và Kết luận 4.1: thiếu cụm "sử dụng đa cảm biến".
- → Kiểm tra tên chính thức trong quyết định giao đề tài, sửa nhất quán. Tên trên slide bìa phải khớp.

---

## B. SỐ LIỆU CÒN THIẾU TRONG QUYỂN (ảnh hưởng trực tiếp slide kết quả)

1. **Mục 3.3 (YOLO26n) không có bất kỳ con số nào** — không mAP, không precision/recall, chỉ nhận xét định tính. Repo có `yolo26n_train_results.csv` → tính mAP50/mAP50-95 cuối, đưa vào quyển (nếu sửa được) và Slide 12. Nếu không kịp sửa quyển thì slide vẫn nên có số, chuẩn bị giải thích nguồn.
2. **Mục 3.4 (ByteTrack) không có số** — ít nhất nên có: số ID switch trên video test, thời gian duy trì track qua che khuất. Có các video `yolo26_track_*.mp4` để đo.
3. **Mục 3.5**: ngưỡng thực nghiệm T (tỷ số đỉnh phổ) không cho giá trị cụ thể; dải tần Ω không định nghĩa (3.5.3 nhắc "2–4 Hz" trong khi code dùng **1–5 Hz**) → chốt số, ghi rõ.
4. **Bảng 3-3 (khung giờ)**: thiếu khung 10h–11h trong danh sách (00–07, 07–08, 08–09, 09–10, *nhảy* 11–13…) → bổ sung hoặc giải thích.
5. Số liệu dataset YOLO khiêm tốn (873 ảnh: 611/174/88) → chuẩn bị câu trả lời "dữ liệu nhỏ vậy có đủ không" (fine-tune từ pretrained, augmentation, domain hẹp góc camera cố định).
6. Cấu hình phần cứng 3.1.1 chỉ ghi "Raspberry Pi" → ghi rõ **Pi 4 Model B, RAM 4GB, CPU 1.8GHz** (có sẵn trong `benchmark_results.json`).
7. Hình 2-9 (STM32CubeAI ước lượng YOLO ~14MB RAM) vs Bảng 3-5 (YOLO 45,23MB trên Pi) — hai con số RAM khác nhau cho cùng model; nên chú thích rõ một cái là ước lượng tensor arena, một cái là đo cả runtime, tránh bị hỏi vặn.
8. Kết luận 4.1 hoàn toàn định tính → thêm đoạn số liệu tổng hợp (96,2% phát hiện thực địa, ~99% test, 164,5MB, v.v.) và đối chiếu mục tiêu — khớp tiêu chí chấm "chỉ rõ phù hợp giữa kết quả và mục tiêu".

---

## C. LỖI TRÌNH BÀY / ĐÁNH SỐ TRONG QUYỂN (sửa nếu quyển còn nộp lại; bản mềm full sẽ bị soi)

1. **Placeholder chưa xử lý**: mục 2.5.4 (trang 47) còn nguyên dòng "`// Hình ảnh`" — chưa chèn hình! Mục 3.6.1 ghi "Hình 3.xx" chưa điền số.
2. **Hình 3-33 không có caption** (trống hoàn toàn trong danh mục hình và trong bài).
3. **Đánh số hình lỗi**: "Hình 2-2-4" (typo, lại trùng caption với Hình 2-5 "Kiến trúc tổng thể của mô hình" — 2 hình 1 tên); Hình 3-5 caption lặp "Hình 3-5. Hình 3-5. …"; Hình 3-38 bị dùng 2 lần (so sánh exposure + kiến trúc tổng thể 3.6.1); Hình 3-30 caption viết thường "đồ thị…".
4. **Mục lục lỗi**: có hai mục "1.1" (Đặt vấn đề và Tổng quan); 1.1.3 có trong bài nhưng thiếu trong mục lục; 2.5.4 thiếu trong mục lục (2.5.3 nhảy 2.5.5).
5. **Nội dung bị lặp**: cuối mục 3.2.1 dán nhầm nguyên khối "Kết quả huấn luyện" (Bảng 3-1 + ma trận nhầm lẫn Hình 3-7 + PR curve Hình 3-8) — trùng hoàn toàn với mục 3.2.4 (Bảng 3-2, Hình 3-19, 3-21). Xóa khối lặp ở 3.2.1.
6. **Câu ngược nghĩa** ở 2.6.5: "hệ thống cả hai kênh màu phải xuất hiện đồng thời. Chỉ cần một trong hai kênh…" — thiếu "KHÔNG yêu cầu", câu trước và câu sau đang mâu thuẫn.
7. Typo: "cảm biến anh thanh" (Hình 1-1), "BiLTSM" (Hình 1-6), "fs = 22500 Hz" ở 2.3.2a (đúng: 22050), "đồ án nay" (lời cảm ơn), "aquan trọng" (2.3.1b), "nhấp nháu" (3.6.3), "RAM cầm rất ít" (2.8.2).
8. Lời cảm ơn: cảm ơn 2 thầy cô nhưng dùng "người đã hướng dẫn"/"Cô đã chỉ bảo" số ít → sửa cho chuẩn cả hai.
9. Lời dẫn Bảng 3-3 ghi "trình bày trong Bảng 3.4" — lệch số bảng.
10. Trang Nhiệm vụ: "Thời gian giao đề tài: 2/2025" nhưng hoàn thành 6/2026 (16 tháng?) → kiểm tra lại có phải 2/2026.
11. Trích dẫn lỗi: mục 2.3.4 viết "nghiên cứu của **R. S. Deshmukh** và cộng sự [8]" nhưng [8] trong danh mục là **Hongyi Sun et al.** → rà lại toàn bộ số trích dẫn. [14] còn là placeholder "YOLO26 Technical Report / Official Documentation" → ghi trích dẫn chuẩn. [8], [3], [4], [9] thiếu năm/nguồn xuất bản.

---

## D. CHUẨN BỊ HỎI ĐÁP PHÁT SINH TỪ QUYỂN (bổ sung vào danh sách câu hỏi trong sườn slide)

1. **INMP441 là mic I2S** — code dùng PyAudio: giải thích được chuỗi I2S overlay → ALSA device → PyAudio trên Pi. Hội đồng TĐH thích hỏi giao tiếp cảm biến.
2. Quyển ghi camera 15 FPS, YOLO ~1,67 FPS → giải thích cơ chế "suy diễn mỗi 9 frame + Kalman predict" (quyển 3.7.3 có nói nhưng không nêu con số 9 — nên nêu).
3. Dữ liệu thực địa 15–26/06/2026 tại Hà Đông (Bảng 3-3) — chuẩn bị mô tả cách xác định "ground truth" 79 xe ưu tiên (ai đếm, bằng gì) — câu hỏi kinh điển về phương pháp đo.
4. Vì sao chọn dải đèn nháy 1–5 Hz (hay 2–4 Hz?) — dẫn tiêu chuẩn đèn ưu tiên 60–240 nháy/phút, chốt cùng số với quyển sau khi sửa A3/B3.
5. Exposure time ảnh hưởng phép đo (3.5.6) — đây là điểm "đo lường" hay, nên chủ động đưa lên slide (đã có trong Slide 13).

---

## E. KẾ HOẠCH SỬA QUYỂN (đã chốt hướng: sửa quyển cho khớp thực tế)

Thứ tự làm — sửa nội dung lớn trước, lỗi trình bày quét một lượt cuối cùng:

### Bước 1 — Chốt bộ số chuẩn (30 phút, làm trước mọi thứ)
Lập một "bảng số liệu chuẩn" dùng chung cho quyển + slide, lấy từ code làm gốc:
- Dải lọc âm thanh: **500–1800 Hz** (`deploy/config.py`) — sửa tại 1.1.2, 2.3.1a, 2.3.2b (600–1500 → 500–1800), 3.2.2a + chú thích Hình 3-2 (bỏ cách gọi "dải lọc 300–3500", ghi rõ đó là dải Mel filter bank fmin/fmax).
- Dải tần đèn nháy: **1–5 Hz** (`FFT_FREQ_MIN/MAX`) — định nghĩa Ω tại 2.6.5, sửa "2–4 Hz" ở 3.5.3.
- Ngưỡng: PNR ≥ **5.0**, năng lượng màu ≥ **5.0**, voting **3/5**, cửa sổ **2 s / trượt 0,17 s**, YOLO chạy **mỗi 9 frame**, fs **22050 Hz** (sửa typo 22500 ở 2.3.2a).
- Tên cảm biến ảnh: chốt theo phần cứng thật (schematic là **IMX415** → sửa "IMX678" ở tóm tắt, hoặc ngược lại nếu board thật dùng IMX678 — kiểm tra BOM).
- *(Lưu ý sau khi chốt lại chiến lược: dải đèn 1–5 Hz và ngưỡng PNR thuộc code/phần mở rộng; trong quyển chỉ cần đảm bảo Ω và T được định nghĩa nhất quán nội bộ — 2.6.5 và 3.5.3 đang lệch nhau 2–4 Hz vs không định nghĩa.)*

### ~~Bước 2~~ — HỦY (chuyển thành slide mở rộng 15) — Bổ sung phần cứng camera CV25 (A1)
- Thêm mục mới vào Chương 2 (đề xuất: **2.9. Thiết kế phần cứng camera** sau 2.8, hoặc thay hẳn 2.8.4):
  - 2.9.1 Yêu cầu: điều khiển được exposure/gain (phục vụ phép đo FFT — nối thẳng với 3.5.6), ống kính zoom/focus/iris chỉnh từ xa, truyền frame ổn định qua Ethernet.
  - 2.9.2 Thiết kế mạch: 5 sheet Altium (Nguồn, SoM CV25, Ethernet, giao tiếp cảm biến MIPI/I2C, điều khiển ống kính TMC) — chèn ảnh schematic/3D từ `hardware/CV25_Camera_DATN/`.
  - 2.9.3 Firmware: GStreamer capture → JPEG → BGR 640×640 → TCP (header 4 byte + payload); UDP lệnh CALIB/ZOOM/FOCUS/IRIS (`camera_source/src/`).
- **Viết lại 2.8.4** cho khớp: thay đoạn "đề tài không tập trung vào thiết kế cảm biến hình ảnh" bằng lý do tự thiết kế camera (chủ động tham số thu nhận ảnh phục vụ phép đo + làm chủ phần cứng).
- Cập nhật: tóm tắt đầu quyển (thêm camera tự thiết kế vào danh mục phần cứng), 3.1.1 (cấu hình thực nghiệm), 4.1 (kết luận — thêm đóng góp phần cứng), 4.2 (hướng phát triển — thêm autofocus vòng kín nếu kịp cài đặt).

### ~~Bước 3~~ — HỦY (chuyển thành slide mở rộng 16) — Bổ sung lọc Butterworth zero-phase + PNR (A2)
- 2.6.3: sau đoạn xây dựng chuỗi R(t)/B(t), thêm bước **lọc thông dải Butterworth bậc 2, 1–5 Hz, zero-phase (lọc xuôi–ngược)** — nêu lý do: khử trôi nền (xe tiến lại gần/ra xa tạo bell curve như ID 104) và nhiễu rung bbox, không méo pha trước FFT.
- 2.6.4: thêm cửa sổ Hann trước FFT (giảm rò rỉ phổ).
- 3.5: thêm tiểu mục "Hiệu quả của bộ lọc" — chèn hình `docs/images/so_sanh_loc_id13.png` (+ id104, id115, emergency nếu cần), nêu số **PNR 5,97 → 27,84 (+366%), đỉnh 2,34 Hz**; ID 104 bị loại nhờ ngưỡng năng lượng màu.
- Danh mục hình + mục lục cập nhật theo.

### ~~Bước 4~~ — HỦY (chuyển thành slide mở rộng 16) — Bổ sung máy trạng thái + đầu ra (A4)
- 2.7.2: thay mô tả tuần tự 9 bước bằng (hoặc bổ sung) **máy trạng thái LISTENING → ALERT → CONFIRMED**, chu kỳ 0,5 s, timeout 30 s, cơ chế lùi CONFIRMED→ALERT — vẽ 1 hình state diagram (điểm cộng với hội đồng TĐH).
- Thêm mục nhỏ "Đầu ra hệ thống": GPIO BCM17, MQTT JSON, lưu frame chú thích; và "Cơ chế vận hành bền vững": tự kết nối lại camera, giám sát nhiệt 75/80°C, log xoay vòng (lấy từ `deploy/decision/`).
- 3.6 cập nhật tương ứng (quy trình hoạt động theo state machine).

### Bước 5 — Điền số liệu thiếu Chương 3 (mục B)
- 3.3: tính mAP50/mAP50-95, precision/recall từ `yolo26n_train_results.csv` (epoch cuối/best) → thêm bảng.
- 3.4: đo ID switch/độ dài track trên `yolo26_track_*.mp4` (hoặc ít nhất mô tả định lượng 1 video).
- 3.5: ghi giá trị ngưỡng T = 5.0, định nghĩa Ω = [1, 5] Hz.
- 3.7: ghi rõ Pi 4 Model B Rev 1.5, RAM 4GB, 1,8GHz, backend TFLite INT8 (`benchmark_results.json`); cập nhật số sau khi benchmark lại BiLSTM INT8; thêm 1 câu về lượng tử hóa INT8 (quy trình + so sánh float32/INT8).
- Bảng 3-3: bổ sung/giải thích khung 10h–11h; thêm 1 câu mô tả cách xác định ground truth 79 xe.
- 4.1: thêm đoạn số liệu tổng hợp + bảng đối chiếu mục tiêu ↔ kết quả.

### Bước 6 — Quét lỗi trình bày (toàn bộ mục C, 1 buổi)
*(nội dung checklist ở dưới)*

---

## F. BỔ SUNG MỚI ĐỂ TĂNG KHỐI LƯỢNG TĐH/ĐO LƯỜNG (chốt 10/07: muốn thêm "chất điều khiển")

Nguyên tắc: chỉ thêm cái **có kết quả đo thật để trình ra** (đồ thị hội tụ, bảng số), không thêm cái chỉ vẽ sơ đồ. Xếp theo tỷ lệ hiệu quả/công sức:

### F1. Vòng điều khiển khẩu độ P-Iris giữ điều kiện đo tối ưu ⭐ (khuyến nghị làm nhất)
- **Ý tưởng**: quyển 3.5.6 đã phát hiện exposure/độ sáng ảnh hưởng trực tiếp biên độ tín hiệu nhấp nháy và PNR → **khép vòng chính phát hiện đó**: đo độ sáng trung bình ROI trên Pi → bộ điều khiển PI → lệnh `IRIS:<pos>` qua UDP (firmware đã có sẵn!) → giữ độ sáng ROI bám giá trị đặt.
- **Chất TĐH**: đây là vòng kín **bám giá trị đặt kinh điển** (có setpoint, sai lệch e = I_ref − I_ROI, bộ PI, cơ cấu chấp hành động cơ bước P-Iris, đối tượng là quang học + ISP). Dễ bảo vệ hơn extremum-seeking, vẽ được sơ đồ khối chuẩn, đo được đáp ứng quá độ (overshoot, thời gian xác lập) khi thay đổi ánh sáng đột ngột.
- **Câu chuyện đẹp**: "phát hiện tham số camera ảnh hưởng phép đo (3.5.6) → thiết kế vòng điều khiển duy trì điều kiện đo tối ưu" — kết quả nghiên cứu dẫn tới thiết kế điều khiển, đúng quy trình kỹ thuật.
- **Khối lượng**: script Pi (~100 dòng) + thí nghiệm che/rọi sáng → đồ thị I_ROI(t) bám setpoint + đồ thị PNR trước/sau khi có vòng điều khiển. Cần board camera thật để demo, không có thì demo bằng webcam chỉnh exposure qua OpenCV (v4l2) làm bản mô phỏng.
- **Vào quyển**: mục 2.9.4 (thiết kế) + 3.x (kết quả đáp ứng vòng kín).

### F2. Autofocus vòng kín — extremum seeking (đã note ở slide_outline, giữ nguyên kế hoạch)
- Leo đồi trên phương sai Laplacian → lệnh `FOCUS:<n>`. Kết quả trình ra: đồ thị S(k) hội tụ theo số bước, thời gian hội tụ.
- Đi cùng F1 thành **một mục "Điều khiển ống kính vòng kín" gồm 2 vòng**: iris (bám setpoint, PI) + focus (tìm cực trị) — phân biệt rõ 2 lớp bài toán điều khiển.

### F1+F2 chi tiết lý thuyết (chuẩn bị cho slide backup B7 và hỏi đáp)
**Vòng Iris — điều chỉnh bám giá trị đặt, CÓ hàm truyền xấp xỉ:**
- Setpoint I_ref = mức sáng ROI cho PNR tốt nhất (chọn từ thực nghiệm 3.5.6 — giá trị đặt sinh ra từ kết quả đo của đồ án).
- Đối tượng: motor bước (vị trí, tức thời so với chu kỳ frame) + quang học (đặc tính tĩnh phi tuyến I(u)) + **trễ vận chuyển d = 1–3 frame** (phơi sáng + ISP + TCP về Pi + UDP về board).
- Tuyến tính hóa quanh điểm làm việc: ΔI ≈ K·Δu; **nhận dạng K và d bằng đáp ứng bậc thang** (+N bước iris → ghi I(t)).
- Bộ điều khiển I (hoặc PI): G_hở(z) ≈ K·Ki/(z−1)·z^(−d) — chọn Ki theo dự trữ biên/pha, trễ d là yếu tố giới hạn. Bão hòa iris min/max → anti-windup. Chu kỳ trích mẫu = chu kỳ frame (67 ms @15FPS).
- Kiểm chứng: đặc tính tĩnh I(u) + đáp ứng quá độ hệ kín khi che/rọi sáng (overshoot, thời gian xác lập).
- Quy trình kể trước hội đồng: nhận dạng → tuyến tính hóa → thiết kế → kiểm chứng.

**Vòng Focus — tìm cực trị, KHÔNG có setpoint thường & không có hàm truyền:**
- Hàm mục tiêu S(p) đơn đỉnh quanh điểm nét, giá trị đỉnh không biết trước → không đặt được I_ref kiểu thường.
- Câu trả lời khi bị hỏi "không có setpoint sao là vòng kín?": **giá trị đặt là gradient bằng 0** — quanh đỉnh S(p) ≈ S* − a(p−p*)², dS/dp = 0 tại điểm nét; bộ điều khiển ước lượng dấu gradient qua nhiễu loạn (perturb-and-observe) và lái về 0. Sai lệch = gradient ước lượng. Cùng nguyên lý **MPPT điện mặt trời**.
- Phân tích: **hội tụ** (đơn đỉnh + bước dò đủ nhỏ), không phải ổn định Bode. Backlash motor → tiếp cận đỉnh từ một chiều sau CALIB; cảnh động làm S nhiễu → dò khi cảnh tĩnh/hysteresis.

**Bảng so sánh 2 vòng (đưa nguyên lên slide backup B7):** lớp bài toán (điều chỉnh vs tự tối ưu) / giá trị đặt (I_ref vs dS/dp=0) / mô hình (tĩnh tuyến tính hóa + trễ vs bản đồ đơn đỉnh) / bộ điều khiển (PI+anti-windup vs leo đồi thô→tinh) / phân tích (dự trữ biên-pha vs hội tụ) / kiểm chứng (đáp ứng quá độ vs đồ thị S(k)).
**Điểm chung đáng nói:** cả hai vòng khép **qua mạng** — trễ vòng = phơi sáng + TCP + xử lý + UDP; đo con số trễ cụ thể để nêu (chất đo lường).

**Xếp lớp môn học (câu hỏi "đây là điều khiển quá trình hay LTI?"):**
- Iris = **bài toán điều khiển quá trình** (iris là "van tiết lưu ánh sáng": PV = độ sáng ROI, MV = vị trí khẩu độ, đối tượng khuếch đại + trễ chết, nhiễu = ánh sáng môi trường; nhận dạng **FOPDT** bằng bậc thang, chỉnh định PI theo Ziegler–Nichols/IMC) **phân tích bằng công cụ LTI** sau tuyến tính hóa. Câu chốt: "bài toán điều khiển quá trình, phân tích và chỉnh định bằng lý thuyết điều khiển tuyến tính quanh điểm làm việc."
- Focus = **không thuộc cả hai** — tại đỉnh độ nét dS/dp = 0 nên khuếch đại tuyến tính hóa bằng 0, LTI "mù" đúng tại điểm làm việc mong muốn (lý do sâu xa phải dùng nhiễu loạn dò) → lớp điều khiển phi tuyến/tự tối ưu (extremum seeking), phân tích hội tụ.
- Giá trị trình bày: một hệ ống kính, hai lớp bài toán — thể hiện biết dùng công cụ kinh điển VÀ biết khi nào nó hết hiệu lực.

### F3. Mục "Đánh giá độ không đảm bảo đo" cho phép đo tần số đèn (công sức thấp nhất, thuần đo lường)
- Không cần phần cứng, chỉ phân tích + thí nghiệm nhỏ:
  - Độ phân giải tần số Δf = 1/T_cửa_sổ (5 s → 0,2 Hz); trade-off cửa sổ dài ↔ trễ phát hiện — khảo sát PNR theo độ dài cửa sổ (2/3/5/8 s).
  - Ảnh hưởng **jitter chu kỳ khung hình** (lấy mẫu không đều) lên phổ: đo timestamp thực tế các frame, định lượng độ lệch đỉnh tần số; nêu giải pháp nội suy lại về lưới thời gian đều.
  - Ảnh hưởng khoảng cách/kích thước ROI lên SNR của tín hiệu màu.
- **Vào quyển**: tiểu mục mới trong 3.5 (ví dụ 3.5.8 "Đánh giá độ không đảm bảo của phép đo tần số"). Hội đồng đo lường gần như chắc chắn hỏi mấy câu này — chủ động viết trước là chuyển câu hỏi khó thành điểm cộng.

### F4. (Tùy chọn, chỉ khi dư thời gian) Ước lượng vận tốc xe từ dịch tần Doppler của còi
- Bám tần số cơ bản của còi theo thời gian → độ dịch Doppler → ước lượng vận tốc tiếp cận và thời điểm xe ngang qua. Phép đo vật lý đẹp nhưng cần bản ghi âm chất lượng + xe chuyển động chuẩn; rủi ro cao, chỉ làm dạng phân tích offline minh họa.

### F5. (Viết thêm 1 đoạn, gần như 0 công sức) Điều tiết tải theo nhiệt — vòng điều khiển on/off có trễ
- Code đã có ngưỡng 75/80°C → trình bày lại trong quyển như bộ điều khiển on/off có hysteresis điều tiết tần suất suy diễn YOLO theo nhiệt độ CPU (đối tượng nhiệt, cảm biến thermal zone, cơ cấu "chấp hành" là lịch suy diễn). Thêm 1 đồ thị nhiệt độ khi chạy dài.

**Khuyến nghị gói bổ sung**: F1 + F2 (gộp thành mục "Điều khiển ống kính vòng kín") + F3 + F5. Tổng khối lượng mới ≈ 1 mục thiết kế + 2 tiểu mục kết quả — đủ "dày" mà mọi thứ đều demo/đo được. F4 để dành làm "hướng phát triển".
Checklist: `// Hình ảnh` (2.5.4) → chèn hình pipeline YOLO+ByteTrack; "Hình 3.xx" (3.6.1) → đánh số lại chuỗi hình sau 3-38; caption Hình 3-33; gộp/xóa khối lặp ở 3.2.1; sửa câu ngược nghĩa 2.6.5 (thêm "không yêu cầu cả hai kênh xuất hiện đồng thời"); typo (anh thanh, BiLTSM, 22500, đồ án nay, aquan trọng, nhấp nháu, RAM cầm); lời cảm ơn số nhiều; "Bảng 3.4"→"Bảng 3-3"; thời gian giao đề tài 2/2025→kiểm tra; mục lục (hai mục 1.1, thiếu 1.1.3/2.5.4) — đánh số lại tự động rồi rebuild TOC; rà toàn bộ trích dẫn (Deshmukh↔[8], hoàn thiện [14], bổ sung năm cho [3][4][8][9]); thống nhất tên đề tài ở Nhiệm vụ/1.1/4.1 theo bìa.
