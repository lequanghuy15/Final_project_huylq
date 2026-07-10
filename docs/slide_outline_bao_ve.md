# SƯỜN SLIDE BẢO VỆ ĐỒ ÁN TỐT NGHIỆP (v2 — thân bài bám quyển, mở rộng tách riêng)

**Đề tài:** Thiết kế hệ thống nhận diện xe ưu tiên tại biên sử dụng đa cảm biến phục vụ điều khiển giao thông thông minh
**SV:** Lê Quang Huy — 20222297 | **GVHD:** TS. Lê Minh Hoàng, PGS.TS. Nguyễn Thanh Hường

---

## Chiến lược trình bày (chốt 10/07)

1. **Thân bài (slide 3–14) bám đúng quyển báo cáo** — mọi phương pháp, con số, hình vẽ đều truy được về mục/hình trong quyển. Hội đồng cầm quyển đối chiếu không lệch chỗ nào.
2. **Phần cứng camera CV25 + các cải tiến trong code (Butterworth zero-phase, máy trạng thái, GPIO/MQTT) + điều khiển ống kính vòng kín → gom vào mục "Triển khai mở rộng sau đồ án"** (slide 15–16), trình bày với tinh thần: *"nộp quyển không có nghĩa là dừng nghiên cứu — sau khi hoàn thành đồ án em tiếp tục phát triển hệ thống"*. Đây vừa là điểm cộng thái độ nghiên cứu, vừa chạm tiêu chí điểm thành tích ("sản phẩm ứng dụng có tính hoàn thiện cao, khối lượng thực hiện lớn").
3. Khung câu chuyện cho hội đồng TĐH giữ nguyên: **hệ đo đa cảm biến** — thu tín hiệu → lọc/trích đặc trưng → đo đại lượng có ích → hợp nhất bằng chứng → kết luận. Mô hình học sâu chỉ là khối phân loại trong chuỗi đo, không sa đà kiến trúc mạng.
4. Nếu hội đồng xem repo/demo thấy code "đi trước" quyển → câu trả lời nhất quán: các cải tiến đó thực hiện sau khi nộp quyển, đã trình bày ở phần mở rộng.

**Quy tắc trình bày (bám tiêu chí chấm 1,5đ chất lượng slide):**
- **Đánh số trang mọi slide**; ít chữ, từ khóa + sơ đồ/biểu đồ; mỗi slide 1 thông điệp.
- Slide photo **đen trắng 4 bản** → biểu đồ phân biệt bằng nét liền/đứt + marker, không chỉ bằng màu; chữ trong hình ≥ 18pt.
- Chuẩn bị video demo + phần mềm mô phỏng sẵn sàng chiếu (Xeuutien.mp4, Stable_light.mp4, các video track).
- Đến sớm 30 phút thử máy. Tên mô hình còi: **CNN-BiLSTM-Attention** thống nhất mọi chỗ.

---

## PHẦN MỞ ĐẦU (≈2 phút)

### Slide 1 — Trang bìa
- Tên trường/khoa, đề tài (đúng tên trên bìa quyển), SV + MSSV, GVHD, hội đồng, ngày.

### Slide 2 — Nội dung trình bày
- 6 mục: Đặt vấn đề & mục tiêu → Thiết kế hệ thống → Kết quả thực nghiệm → Kết luận → Triển khai mở rộng sau đồ án → Hướng phát triển.

### Slide 3 — Đặt vấn đề & tính cấp thiết (quyển 1.1, 1.1.3)
- Ùn tắc đô thị → xe ưu tiên khó lưu thông; nhận biết hiện phụ thuộc con người/CSGT điều tiết thủ công.
- Bảng mini các hướng hiện có: V2X/GPS/RFID — chi phí hạ tầng lớn, khó đồng bộ ở VN; chỉ camera — che khuất; chỉ âm thanh — nhiễu, không định vị.
- → Giải pháp: **hệ đo đa cảm biến tại biên**, tận dụng hạ tầng camera sẵn có + module thu âm giá rẻ.

### Slide 4 — Mục tiêu & phạm vi (quyển 2.1 — viết dạng chỉ tiêu đo được, slide kết luận sẽ tick lại)
- Nhận diện xe ưu tiên bằng **3 bằng chứng độc lập**: còi hú + phương tiện hiện diện + đèn nhấp nháy tuần hoàn.
- Chạy liên tục trên thiết bị biên (Raspberry Pi), không phụ thuộc cloud; khối thị giác chỉ kích hoạt khi có còi (tiết kiệm tài nguyên).
- Chống báo động giả trong môi trường nhiễu giao thông thực tế.
- Phạm vi: một nút giao, 1 mic + 1 camera.

---

## PHẦN THIẾT KẾ (≈4,5 phút — theo Chương 2 của quyển)

### Slide 5 — Kiến trúc tổng thể (Hình 2-1/2-7 quyển)
- Sơ đồ khối: [Mic] luôn hoạt động → phát hiện còi → kích hoạt [Camera → YOLO26n → ByteTrack → FFT] → hợp nhất 3 điều kiện → kết luận.
- Nhấn nguyên tắc **kích hoạt theo sự kiện**: mic luôn nghe với tải thấp nhất, thị giác chỉ chạy khi có bằng chứng âm thanh.

### Slide 6 — Kênh đo âm thanh (quyển 2.3)
- Chuỗi xử lý tín hiệu: fs 22 050 Hz, mono → **lọc thông dải Butterworth** (dải tần đặc trưng còi — ghi đúng số sau khi chốt bước 1 kế hoạch sửa quyển) → cửa sổ 2 s trượt 0,17 s → pre-emphasis 0,97 → **Mel(64, 300–3500 Hz) + MFCC(40)** song song.
- Phân loại: **Dual-Stream CNN-BiLSTM-Attention** (2 nhánh đặc trưng, BiLSTM khai thác tính chuỗi, Attention tập trung vùng chứa còi) — 1 hình kiến trúc, không đi sâu.
- **Voting 3/5 cửa sổ** chống báo giả → tín hiệu kích hoạt ổn định.
- Nói miệng: các lựa chọn fs/dải lọc/cửa sổ là quyết định đo lường (Nyquist, phổ còi 500–1800 Hz, chu kỳ WAIL/YELP/HI-LO).

### Slide 7 — Khối phát hiện & bám vết phương tiện (quyển 2.4–2.5, 1 slide duy nhất cho "AI thị giác")
- Vai trò: cung cấp **ROI ổn định theo từng xe** cho phép đo quang — YOLO không phân loại "xe ưu tiên", chỉ phát hiện 7 lớp phương tiện.
- YOLO26n (nano, tối ưu biên, NMS-free); suy luận chậm hơn framerate → **ByteTrack + Kalman** duy trì vị trí và ID giữa các lần suy luận, ghép cặp 2 tầng tận dụng cả detection tin cậy thấp (giữ track qua che khuất).

### Slide 8 — Khối xác thực đèn ưu tiên bằng FFT (quyển 2.6 — trọng tâm phương pháp)
- Xây tín hiệu đo: ROI theo từng ID → cường độ trung bình kênh Đỏ R(t) và Xanh dương B(t) theo thời gian.
- Loại DC → **FFT** → tìm đỉnh phổ trong dải tần đèn nháy Ω → **tỷ số đỉnh/trung vị nền phổ** (chuẩn hóa theo nhiễu nền, không dùng ngưỡng biên độ tuyệt đối — lý do: cường độ phụ thuộc khoảng cách/ánh sáng/exposure).
- Tiêu chí: ρ_R ≥ T **hoặc** ρ_B ≥ T (xe chỉ đèn đỏ, chỉ đèn xanh, hoặc cả hai).
- Hình: đồ thị R(t)/B(t) + phổ FFT của xe ưu tiên (Hình 3-36/3-37 quyển).

### Slide 9 — Tích hợp & ra quyết định + lựa chọn phần cứng (quyển 2.7–2.8)
- Điều kiện kết luận: **Siren ∧ Vehicle ∧ FlashingLight** — 3 bằng chứng độc lập, giảm báo giả so với đơn cảm biến.
- Lựa chọn phần cứng theo ước lượng tài nguyên (điểm TĐH): STM32 bị loại (YOLO cần ~14 MB RAM + thư viện Python) → **Raspberry Pi 4**; mic MEMS **INMP441** (I2S, ADC tích hợp); camera RGB điều chỉnh được exposure/AWB (phục vụ phép đo — dẫn trước cho slide 12).

---

## PHẦN KẾT QUẢ (≈4,5 phút — theo Chương 3, mỗi kết quả một con số)

### Slide 10 — Kết quả kênh âm thanh: mô hình (quyển 3.2.4)
- Test 6 381 mẫu: **Precision/Recall/F1 ≈ 0,98–0,99** cả hai lớp, accuracy ~99%, **ROC-AUC 0,9982**.
- Hình: ma trận nhầm lẫn + đường PR (Hình 3-19, 3-21); loss/accuracy hội tụ để backup.
- Nhấn: nhầm Non-Siren→Siren thấp = ít kích hoạt thị giác vô ích (tiết kiệm tài nguyên).

### Slide 11 — Kết quả kênh âm thanh: thực địa (quyển 3.2.5 — slide "thực chiến", hội đồng thích)
- Triển khai thật 15–26/06/2026 tại Hà Đông: **76/79 xe ưu tiên phát hiện đúng (96,2%)**, 3 bỏ sót (giờ cao điểm), 8 báo giả (còi hơi) — bảng theo khung giờ (Bảng 3-3).
- Hiệu quả Voting: trước/sau (Hình 3-26) — loại dự đoán giật cục.
- Chuẩn bị miệng: cách xác định ground truth 79 xe (hội đồng đo lường chắc chắn hỏi).

### Slide 12 — Kết quả khối thị giác + FFT (quyển 3.3–3.5 — slide kết quả đắt nhất, nói chậm)
- YOLO + ByteTrack: phát hiện đa đối tượng, ID ổn định (Hình 3-27, 3-28; thêm mAP từ CSV nếu kịp bổ sung quyển).
- **3 trường hợp đối chứng FFT**: nguồn sáng tĩnh → phổ bẹt; xe thường ID 104 → bell curve trơn, đỉnh 1,05 Hz (chuyển động của xe, không phải đèn) → loại; xe ưu tiên → dao động bật/tắt rõ, đỉnh phổ nổi bật trong dải đèn → xác nhận.
- **Ảnh hưởng exposure time** (3.5.6): giảm exposure hợp lý → biên độ nhấp nháy giữ tốt hơn, tín hiệu sạch hơn — phát hiện "đo lường" đắt giá, dẫn trước cho phần mở rộng (vòng điều khiển iris).

### Slide 13 — Kết quả tài nguyên & thời gian thực (quyển 3.7)
- Bảng: CNN-BiLSTM-Attention 61,8 MB / 71,6 ms mỗi cửa sổ 2 s; YOLO26n 45,2 MB / 599,7 ms (~1,67 FPS); ByteTrack 0,51 ms; FFT 1,23 ms; **tổng ~164,5 MB**.
- Biện luận: nút thắt duy nhất là YOLO → giải bằng ByteTrack duy trì ROI giữa các lần suy luận + kích hoạt theo sự kiện → hệ chạy ổn định trên Pi, camera 15 FPS.

### Slide 14 — Kết luận (quyển Chương 4 + bảng đối chiếu)
- Bảng mục tiêu (Slide 4) ↔ kết quả, tick ✓ từng dòng: 3 bằng chứng ✓ (99% test / 96,2% thực địa / FFT phân biệt đúng 3 trường hợp), chạy trên Pi ✓ (164,5 MB), chống báo giả ✓ (voting + AND 3 điều kiện).
- Hạn chế nói thẳng (quyển 3.8): phụ thuộc khoảng cách mic, điều kiện sáng/tham số camera, tốc độ suy luận YOLO.

---

## PHẦN MỞ RỘNG SAU ĐỒ ÁN (≈2 phút — điểm nhấn "không dừng nghiên cứu")

> Mở màn bằng 1 câu định vị: *"Sau khi hoàn thành quyển báo cáo, em tiếp tục phát triển hệ thống theo hướng hoàn thiện sản phẩm — xin trình bày các kết quả đã và đang triển khai."*

### Slide 15 — Đã triển khai (1/2): Tự thiết kế phần cứng camera
- Board camera SoM **Ambarella CV25** + cảm biến Sony, ống kính varifocal điều khiển động cơ bước (zoom/focus/P-Iris qua driver TMC).
- Mạch tự thiết kế (Altium, 5 khối: nguồn — SoM — Ethernet — giao tiếp cảm biến MIPI/I2C — điều khiển ống kính); firmware C++ GStreamer → TCP frame về Pi + UDP lệnh điều khiển ống kính từ xa.
- Ảnh board thật/3D + sơ đồ khối; lý do: chủ động tham số thu nhận ảnh (đúng phát hiện exposure ở slide 12) + làm chủ phần cứng.

### Slide 16 — Đã & đang triển khai (2/2): Cải tiến xử lý tín hiệu và điều khiển
- **Đã làm — lọc Butterworth thông dải zero-phase (1–5 Hz) trước FFT**: khử trôi nền (bell curve xe tiến lại gần) + nhiễu rung bbox, không méo pha → **PNR 5,97 → 27,84 (+366%)** trên xe ID 13, đỉnh 2,34 Hz — 1 hình so sánh trước/sau (`so_sanh_loc_id13.png`).
- **Đã làm — hoàn thiện vận hành**: máy trạng thái LISTENING→ALERT→CONFIRMED, đầu ra GPIO/MQTT cho hệ điều khiển đèn, giám sát nhiệt, tự kết nối lại.
- **Đang làm — điều khiển ống kính vòng kín**: (1) vòng PI giữ độ sáng ROI bằng khẩu độ P-Iris (bám giá trị đặt — duy trì điều kiện đo tối ưu, khép vòng chính phát hiện exposure của đồ án); (2) autofocus tìm cực trị theo độ nét ảnh (extremum-seeking, cùng nguyên lý MPPT). Chỉ nói "đang làm" nếu chưa có kết quả đo; có đồ thị hội tụ thì chuyển thành "đã làm".

### Slide 17 — Hướng phát triển & Lời cảm ơn (quyển 4.2)
- Dataset đa dạng hơn; mô hình tối ưu nhúng/NPU; kết hợp V2X/GPS; tích hợp điều khiển đèn tín hiệu quy mô lớn; (nếu thích: ước lượng vận tốc xe qua dịch tần Doppler của còi).
- "Em xin chân thành cảm ơn quý thầy cô. Em sẵn sàng nhận câu hỏi."

---

## SLIDE DỰ PHÒNG (BACKUP)

- B1. Dataset: audio Siren/Non-Siren (nguồn, gán nhãn); ảnh 873 (611/174/88), 7 lớp, lớp exception.
- B2. Đường huấn luyện 2 mô hình; lượng tử hóa INT8 (kích thước ↓, chạy CPU Pi; BiLSTM từng khó quantize — đã giải quyết, không phải hạ xuống GRU); so sánh float32 ↔ INT8.
- B3. Toán FFT khối đèn: công thức tỷ số đỉnh/trung vị, lý do dùng trung vị ước lượng nền; (mở rộng: đáp ứng Butterworth, vì sao zero-phase).
- B4. ByteTrack chi tiết: Kalman 8 trạng thái, Hungarian 2 tầng, ngưỡng score.
- B5. Phần cứng mở rộng: schematic từng sheet Altium; giao thức TCP header 4 byte + 1 228 800 byte BGR, zero-copy; lệnh UDP CALIB/ZOOM/FOCUS/IRIS.
- B6. Bảng benchmark đầy đủ + điều kiện đo (Pi 4 Model B, RAM, backend TFLite).
- B7. Sơ đồ vòng điều khiển iris PI + autofocus extremum-seeking (nếu bị hỏi sâu phần mở rộng).
- B8. Độ không đảm bảo đo tần số: Δf = 1/T_cửa_sổ, trade-off cửa sổ ↔ trễ, jitter khung hình.

---

## PHÂN BỔ THỜI GIAN (mục tiêu 13 phút, trần 15)

| Phần | Slide | Thời gian |
|---|---|---|
| Mở đầu | 1–4 | 2,0′ |
| Thiết kế (theo quyển) | 5–9 | 4,0′ |
| Kết quả (theo quyển) | 10–13 | 4,0′ |
| Kết luận | 14 | 1,0′ |
| Mở rộng sau đồ án | 15–16 | 1,5′ |
| Hướng phát triển + cảm ơn | 17 | 0,5′ |

---

## CÂU HỎI HỘI ĐỒNG DỄ HỎI (trả lời ngắn, đi thẳng — tiêu chí 2,5đ)

1. **Vì sao lấy mẫu 22 050 Hz?** Phổ còi < 3,5 kHz; thỏa Nyquist với biên rộng, cân bằng tải trên Pi.
2. **Dải lọc thông dải của em là bao nhiêu, vì sao?** Trả lời đúng MỘT con số đã chốt nhất quán trong quyển (sau bước sửa) — dải tần đặc trưng còi ưu tiên theo quy chuẩn thiết bị tín hiệu.
3. **Tỷ số đỉnh/trung vị là gì, sao không dùng ngưỡng biên độ?** Trung vị ước lượng nền phổ bền vững với đỉnh nhiễu cục bộ; biên độ tuyệt đối biến động theo khoảng cách/ánh sáng/exposure nên không dùng.
4. **Vì sao dải tần đèn nháy chọn như vậy?** Đèn ưu tiên nhấp nháy 60–300 lần/phút → 1–5 Hz; đỉnh 1,05 Hz của xe thường ID 104 nằm sát biên là chuyển động của xe — minh chứng cần dải chặn dưới.
5. **Độ phân giải phép đo tần số?** Δf = 1/T_cửa_sổ (cửa sổ 5 s → 0,2 Hz) — đủ phân biệt trong dải đèn.
6. **Độ trễ từ khi có còi đến khi kết luận?** Voting 3/5 × 0,17 s + FFT cần đủ mẫu (~2 s) → nêu tổng và biện luận đủ cho điều khiển pha đèn.
7. **Ground truth 79 xe ưu tiên xác định thế nào?** Chuẩn bị câu trả lời cụ thể (quan sát/ghi hình đối chiếu).
8. **INMP441 là mic I2S, code đọc thế nào?** I2S overlay trên Pi → thiết bị ALSA → thư viện thu âm; ADC tích hợp trong mic giảm nhiễu đường truyền analog.
9. **Chỉ có còi mà không thấy đèn (che khuất)?** Chưa kết luận — thiết kế chấp nhận trễ để tránh báo giả; hướng mở rộng đa camera.
10. **Vì sao YOLO không nhận diện thẳng "xe ưu tiên"?** Hình dáng xe ưu tiên đa dạng, dễ nhầm; hệ dùng YOLO phát hiện phương tiện rồi xác thực bằng 2 bằng chứng vật lý độc lập (còi + tần số đèn) — bền vững hơn.
11. **Lượng tử hóa INT8 mất bao nhiêu độ chính xác?** Số so sánh float32 ↔ INT8 (chuẩn bị từ notebook); đổi lại giảm ~4× kích thước, chạy CPU Pi.
12. **Phần mở rộng có trong quyển không?** Trả lời thẳng: thực hiện sau khi nộp quyển, sản phẩm/mã nguồn/demo sẵn sàng trình chiếu — thể hiện đồ án tiếp tục được phát triển thành sản phẩm hoàn thiện.
13. **Điều khiển lens vòng kín cụ thể là gì?** Iris: vòng bám giá trị đặt (PI, sai lệch độ sáng ROI); focus: tìm cực trị hàm độ nét (extremum-seeking, tương tự MPPT điện mặt trời) — phân biệt rõ hai lớp bài toán.

---

## GHI CHÚ ĐANG TREO (việc cần chốt trước khi làm slide)

1. **Sửa quyển theo kế hoạch rút gọn** (xem `ra_soat_quyen_do_an.md` mục E — bước 2/3/4 đã HỦY vì nội dung đó chuyển sang phần mở rộng): chỉ còn bước 1 (chốt bộ số nhất quán trong quyển), bước 5 (điền số liệu thiếu Chương 3), bước 6 (quét lỗi trình bày).
2. Chạy lại `benchmark_pi.py` với model BiLSTM INT8 đang deploy — xác nhận 71,6 ms và cập nhật nếu lệch.
3. Cập nhật README/notebook đang ghi "GRU" cho khớp CNN-BiLSTM-Attention.
4. Tính mAP từ `yolo26n_train_results.csv` cho slide 12 (và quyển 3.3 nếu kịp).
5. Chuẩn bị số float32 ↔ INT8 cho câu hỏi 11.
6. Autofocus + vòng iris PI: nếu muốn slide 16 nói "đã làm" thì phải cài đặt và có đồ thị hội tụ/đáp ứng trước ngày bảo vệ (chi tiết phương án ở `ra_soat_quyen_do_an.md` mục F); chưa có thì để nguyên "đang làm".
