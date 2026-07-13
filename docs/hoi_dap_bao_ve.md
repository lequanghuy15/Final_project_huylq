# NGÂN HÀNG HỎI ĐÁP BẢO VỆ — CHI TIẾT ĐẾN TẬN GỐC

Cách dùng: mỗi câu có **[Ngắn]** — câu trả lời 15–30 giây nói trước hội đồng (tiêu chí chấm: "ngắn gọn, chính xác, đi thẳng vào vấn đề"), và **[Sâu]** — kiến thức nền để trả lời khi bị truy tiếp. Đừng tự nói phần [Sâu] khi chưa bị hỏi.

---

# A. CẢM BIẾN & PHẦN CỨNG

## A1. Microphone INMP441 hoạt động thế nào? Vì sao chọn nó?

**[Ngắn]** INMP441 là micro MEMS điện dung: màng rung silicon và bản cực cố định tạo thành một tụ điện; sóng âm làm màng dao động → điện dung thay đổi → điện áp thay đổi. Điểm khác biệt là **ADC nằm ngay trong chip**, xuất thẳng dữ liệu số qua giao tiếp I2S — nên đường tín hiệu analog chỉ dài vài trăm micromet bên trong chip, gần như miễn nhiễm nhiễu điện từ trên dây, không cần mạch khuếch đại ngoài. Giá rẻ, nhỏ, đủ băng thông cho dải còi.

**[Sâu]**
- Nguyên lý tụ: C = εA/d. Màng rung cách bản cực khoảng cách d; áp suất âm p(t) làm d thay đổi → C thay đổi. Chip phân cực tụ bằng điện áp qua điện trở rất lớn nên điện tích Q gần như không đổi trong chu kỳ âm thanh → V = Q/C biến thiên theo âm thanh.
- ADC bên trong là loại **Sigma-Delta**: lấy mẫu quá mức (oversampling) 1-bit tần số rất cao rồi lọc-decimate xuống 24 bit tại tần số âm thanh. Vì thế đầu ra là chuỗi số PCM 24-bit.
- **I2S** là chuẩn truyền âm thanh số 3 dây: SCK (bit clock), WS (word select — phân kênh trái/phải), SD (data). Pi bật I2S bằng device tree overlay, kernel nhìn thấy như một sound card ALSA, PyAudio đọc qua ALSA như micro thường.
- Vì sao không dùng micro analog + ADC rời: đường analog dài trên board dễ nhiễm nhiễu 50 Hz và RF; thêm linh kiện, thêm hiệu chuẩn.

## A2. Động cơ bước xoay được là nhờ đâu? (điều khiển ống kính — phần mở rộng)

**[Ngắn]** Động cơ bước có stator gồm nhiều cuộn dây chia thành 2 pha, và rotor là nam châm vĩnh cửu có răng. Khi cấp dòng cho một tổ hợp pha, stator tạo ra một từ trường đứng yên theo một hướng xác định; rotor bị kéo xoay đến vị trí răng thẳng hàng với từ trường đó rồi **dừng và giữ** ở đấy. Muốn quay tiếp, driver đổi tổ hợp cấp dòng theo trình tự → từ trường "nhảy" sang hướng kế tiếp → rotor nhảy theo đúng **một góc bước cố định** (thường 1,8°, tức 200 bước/vòng). Quay liên tục thực chất là chuỗi cú nhảy rời rạc rất nhanh.

**[Sâu]**
- Loại dùng phổ biến là **hybrid stepper**: rotor nam châm vĩnh cửu dọc trục, hai đầu bọc nắp sắt có răng lệch nhau nửa bước răng. Momen sinh ra do rotor tìm vị trí **từ trở nhỏ nhất** (răng rotor đối diện răng stator → khe hở từ nhỏ nhất).
- Trình tự full-step 2 pha A, B: (+A) → (+B) → (−A) → (−B) → lặp lại; mỗi lần chuyển là 1 bước. **Half-step**: xen kẽ trạng thái cấp cả 2 pha → nửa góc bước. **Microstepping**: driver cấp dòng hai pha theo tỷ lệ sin–cos (I_A = I·cosθ, I_B = I·sinθ) → vector từ trường xoay đến vị trí trung gian bất kỳ → chia 1 bước vật lý thành 8/16/256 vi bước, chuyển động mượt, giảm rung.
- **Driver TMC** trong đồ án: chứa 2 cầu H, điều khiển dòng qua cuộn bằng **PWM chopper** — đóng van đến khi dòng đo được chạm ngưỡng đặt, ngắt, chờ giảm, đóng lại — nên giữ được dòng chuẩn sin bất kể điện áp nguồn. Firmware nói chuyện với driver qua ioctl tới character device `/dev/tmc_dev0`.
- Vì sao hợp với ống kính: điều khiển **vị trí vòng hở** — đếm bước là biết vị trí, không cần encoder; có momen giữ khi đứng yên (giữ nét không trôi).
- Nhược điểm dẫn tới lệnh CALIB: vòng hở nên nếu **mất bước** (quá tải, kẹt cơ khí) hoặc có **backlash** (khe hở bánh răng) thì vị trí đếm sai dần → cần lệnh CALIB đưa cả 3 động cơ về vị trí gốc 0 (chạm giới hạn cơ khí) để đặt lại mốc.

## A3. P-Iris là gì, khác DC-Iris?

**[Ngắn]** Iris là khẩu độ — lá thép chắn sáng điều chỉnh lượng ánh sáng vào cảm biến. P-Iris ("Precise Iris") dùng **động cơ bước** nên đặt được vị trí khẩu độ **tuyệt đối, lặp lại được** — lệnh `IRIS:<pos>` của em là đặt thẳng vị trí. DC-iris truyền thống chỉ là cuộn dây tự động đóng mở theo mức sáng, không đặt vị trí chính xác được. Với hệ đo của em, việc đặt được khẩu độ chính xác là điều kiện để làm vòng điều khiển độ sáng ROI.

## A4. Cảm biến ảnh CMOS tạo ra ảnh màu thế nào?

**[Ngắn]** Mỗi pixel là một photodiode: photon rơi vào giải phóng điện tử theo hiệu ứng quang điện, điện tích tích lũy trong **thời gian phơi sáng** tỷ lệ với lượng sáng; sau đó chuyển thành điện áp và số hóa qua ADC. Pixel chỉ đo được cường độ, không đo được màu — nên trên bề mặt phủ **mảng lọc Bayer** (mỗi ô 2×2: 1 đỏ, 2 xanh lá, 1 xanh dương); bộ xử lý ảnh nội suy (demosaicing) để mỗi điểm ảnh có đủ 3 kênh RGB.

**[Sâu]** Vì sao 2 xanh lá: mắt người nhạy chói nhất ở vùng xanh lá, kênh G mang phần lớn thông tin chi tiết. Giá trị pixel I ∝ L·R·t_e (nguồn sáng × hệ số phản xạ × thời gian phơi sáng) rồi qua gain và white balance — chính chuỗi phụ thuộc này là lý do phép đo đèn của em không dùng ngưỡng biên độ tuyệt đối, và là lý do exposure ảnh hưởng kết quả FFT (mục 3.5.6).

## A5. Vì sao chọn Raspberry Pi 4, loại STM32?

**[Ngắn]** Em ước lượng trước bằng STM32CubeAI: riêng YOLO26n sau INT8 cần ~14 MB RAM hoạt động — vượt mọi dòng STM32 (tối đa ~1–2 MB SRAM); ngoài ra hệ cần OpenCV, SciPy, librosa — không chạy trên vi điều khiển. Pi 4 có 4 nhân Cortex-A72 1,8 GHz, RAM 4 GB, Linux đầy đủ, và quan trọng là CPU có **lệnh SIMD NEON** xử lý song song 16 số INT8 mỗi lệnh — đủ chạy suy luận INT8 mà không cần GPU.

## A6. Đầu ra GPIO nối với gì? Điện áp chịu được bao nhiêu?

**[Ngắn]** Chân BCM17 xuất mức HIGH 3,3 V khi CONFIRMED. GPIO của Pi chỉ chịu được vài chục mA nên không đóng tải trực tiếp — tín hiệu này kích transistor/opto trên module relay, relay đóng tiếp điểm khô cho tải bên ngoài (đèn cảnh báo, đầu vào tủ điều khiển). Cách ly điện hoàn toàn giữa Pi và mạch lực. Song song, hệ publish bản tin JSON qua MQTT (timestamp, ID xe, tần số đỉnh) cho các hệ thống phần mềm khác đăng ký nhận.

## A7. Vì sao truyền frame bằng TCP nhưng lệnh ống kính bằng UDP? (phần mở rộng)

**[Ngắn]** Frame ảnh cần **toàn vẹn và đúng thứ tự** — mất một phần frame là hỏng cả khung 1,2 MB — nên dùng TCP có cơ chế phát lại. Lệnh điều khiển ống kính thì ngược lại: gói tin bé, cần độ trễ thấp, và nếu mất thì người vận hành gửi lại được — UDP không bắt tay, không phát lại, đơn giản và nhanh. Đây là lựa chọn kinh điển: dữ liệu khối lượng lớn cần tin cậy đi TCP, lệnh thời gian thực đi UDP.

**[Sâu]** "Zero-copy" phía Pi: frame gửi dạng BGR thô 640×640×3 = 1.228.800 byte kèm header 4 byte báo kích thước; Pi chỉ `np.frombuffer` + `reshape` — diễn giải trực tiếp vùng đệm nhận được thành mảng ảnh, không giải mã JPEG, không cấp phát và sao chép bộ nhớ lần hai → tốn ~0 CPU cho khâu nhận ảnh.

---

# B. LƯỢNG TỬ HÓA INT8 — TỪ SỐ NGUYÊN ĐẾN % DỰ ĐOÁN

## B1. Lượng tử hóa INT8 là gì? Các số nguyên đó có "xếp trong ma trận" không?

**[Ngắn]** Đúng — trọng số của mạng vốn là các **ma trận/tensor số thực float32**; lượng tử hóa là biểu diễn lại từng ma trận đó bằng **ma trận số nguyên 8 bit** kèm theo hai tham số: hệ số tỷ lệ S (scale, số thực) và điểm không Z (zero-point, số nguyên). Quan hệ: **giá trị thực r = S × (q − Z)**, với q là số nguyên trong khoảng −128…127. Tức là ma trận INT8 cộng với (S, Z) là bản "nén" của ma trận float gốc — sai số tối đa bằng nửa bước lượng tử S/2 cho mỗi phần tử.

**[Sâu]**
- Ví dụ cụ thể: một lớp fully-connected có trọng số W kích thước [128 × 64] float32 (32 KB). Sau lượng tử hóa: W_q là ma trận [128 × 64] kiểu int8 (8 KB) + 1 giá trị S_w (hoặc 128 giá trị nếu per-channel) + Z_w. Với tích chập, tensor trọng số 4 chiều [k, k, C_in, C_out] cũng lượng tử hóa y hệt.
- Trọng số thường lượng tử hóa **đối xứng** (Z=0) và **per-channel** (mỗi kênh đầu ra một S riêng — vì dải giá trị các kênh khác nhau nhiều); activation lượng tử hóa **per-tensor bất đối xứng** (một cặp S, Z cho cả tensor).
- S, Z của activation lấy đâu ra? Từ bước **calibration**: chạy mô hình float trên vài trăm mẫu đại diện (trong đồ án là các cặp mel/MFCC thật), ghi lại min–max của từng tensor trung gian, rồi S = (max−min)/255, Z = round(−min/S) − 128. Đây chính là nội dung notebook quantize.

## B2. Vậy đầu vào biến đổi thế nào để cuối cùng ra con số % dự đoán?

**[Ngắn]** Chuỗi đầy đủ trong hệ của em: (1) đặc trưng mel/MFCC dạng float được **lượng tử hóa đầu vào**: q = round(x/S_in + Z_in) → ma trận int8; (2) toàn bộ các lớp tính bằng **số học nguyên**: nhân int8 với int8, cộng dồn vào thanh ghi int32, rồi "tái lượng tử hóa" về int8 cho lớp sau; (3) tensor đầu ra (2 giá trị logit cho 2 lớp) được **giải lượng tử** về float: z = S_out × (q − Z_out); (4) đưa qua **softmax**: p_i = e^(z_i) / Σ e^(z_j) — ra hai số dương có tổng bằng 1, chính là xác suất "còi" và "không còi". Xác suất lớp còi so với ngưỡng 0,5 rồi vào voting.

**[Sâu]** — cơ chế một lớp tính bằng số nguyên (đây là chỗ hội đồng có thể truy nhất):
- Muốn tính y = W·x + b (float). Thay r = S(q−Z) vào:
  **S_y(q_y − Z_y) = Σ S_w(q_w − 0) · S_x(q_x − Z_x) + b**
- Suy ra: q_y = Z_y + M · [ Σ q_w·(q_x − Z_x) + b_q ], trong đó:
  - Σ q_w·(q_x − Z_x): tích và tổng **hoàn toàn bằng số nguyên**, cộng dồn trong int32 để không tràn (int8×int8 ≤ 2¹⁴, cộng vài nghìn phần tử vẫn nằm trong int32);
  - b_q = b/(S_w·S_x) — bias lưu sẵn dạng int32;
  - M = (S_w·S_x)/S_y — hằng số biết trước khi biên dịch mô hình; runtime thực hiện phép nhân M bằng **nhân số nguyên định điểm + dịch bit** (M = M₀·2⁻ⁿ), không cần phép nhân float nào.
- Các hàm phi tuyến (sigmoid, tanh trong LSTM) thực hiện bằng **bảng tra (LUT)** hoặc xấp xỉ định điểm trên int8/int16.
- Vì sao nhanh trên Pi: dữ liệu nhỏ 4× → đỡ nghẽn băng thông bộ nhớ/cache; NEON có lệnh nhân-cộng dồn 16 phần tử int8 mỗi nhịp — thông lượng gấp nhiều lần float32.

## B3. Lượng tử hóa làm mất bao nhiêu độ chính xác? Mất do đâu?

**[Ngắn]** Trên tập test, chênh lệch giữa bản float32 và INT8 của em là [ĐIỀN SỐ TỪ NOTEBOOK — thường <1 điểm %]. Sai số đến từ 3 nguồn: **làm tròn** mỗi giá trị về bước lượng tử gần nhất; **cắt xén** các giá trị ngoại lai nằm ngoài dải min–max calibration; và với mạng hồi tiếp như BiLSTM, sai số **tích lũy qua các bước thời gian** vì đầu ra bước trước là đầu vào bước sau.

**[Sâu]** Đây cũng chính là lý do BiLSTM khó quantize hơn CNN: (1) trạng thái cell c_t có dải động rộng và thay đổi theo thời gian — một cặp (S, Z) cố định khó phủ; (2) sigmoid/tanh nhạy quanh 0, lượng tử thô làm méo cổng quên/cổng vào; (3) sai số hồi tiếp cộng dồn ~87 bước thời gian. Giai đoạn đầu công cụ chuyển đổi lỗi với các toán tử này nên em tạm dùng GRU (ít cổng hơn, dễ chuyển); sau đó phiên bản công cụ mới hỗ trợ tốt hơn và em quantize trực tiếp CNN-BiLSTM-Attention.

## B4. Softmax là gì mà ra được %?

**[Ngắn]** Softmax biến vector điểm số bất kỳ thành phân bố xác suất: p_i = e^(z_i)/Σe^(z_j). Hàm mũ đảm bảo mọi p_i dương, mẫu số đảm bảo tổng bằng 1, và chênh lệch điểm số càng lớn thì xác suất càng "dứt khoát". Ví dụ logit (2,0; −1,0) → e²≈7,39, e⁻¹≈0,37 → p = (0,952; 0,048) — mô hình nói "95,2% là còi".

---

# C. XỬ LÝ TÍN HIỆU ÂM THANH

## C1. Vì sao lấy mẫu 22.050 Hz? Aliasing là gì?

**[Ngắn]** Định lý Nyquist yêu cầu f_s > 2·f_max. Năng lượng còi ưu tiên tập trung dưới ~2 kHz, đặc trưng Mel của em cắt ở 3,5 kHz → f_s = 22.050 Hz cho biên dự trữ hơn 3 lần, đồng thời chỉ bằng nửa chuẩn 44,1 kHz nên giảm nửa khối lượng tính toán trên Pi.

**[Sâu]** Aliasing: nếu tín hiệu chứa thành phần f > f_s/2, sau lấy mẫu nó "gấp" về tần số giả f_s − f, không thể phân biệt và không thể sửa. Chống bằng lọc thông thấp trước lấy mẫu — trong micro số, bộ lọc decimation của ADC Sigma-Delta đảm nhiệm việc này.

## C1b. Phổ còi chỉ khoảng 500–1600 Hz, sao trong bài dùng nhiều con số tần số thế?

**[Ngắn]** Các con số không mâu thuẫn mà **lồng nhau như một cái phễu**, mỗi số một tầng của chuỗi đo:
- **500–1600 Hz**: dải **tần số cơ bản** của còi theo quy chuẩn thiết bị — cao độ tiếng còi quét trong khoảng này.
- **Lọc thông dải 500–1800 Hz**: đặt rộng hơn dải cơ bản vì (1) **hiệu ứng Doppler** — xe 70 km/h tiến lại làm 1600 Hz dịch lên ~1700 Hz (f′ = f·c/(c−v) = 1600×343/323 ≈ 1699); (2) bộ lọc thực có **sườn chuyển tiếp thoải** (−3 dB ngay tại tần số cắt) nên biên cắt phải nằm ngoài dải tín hiệu cần giữ.
- **Mel 300–3500 Hz**: **khung quan sát đặc trưng** — còi không phải sóng sin thuần mà có **hài bậc 2, 3** (2×1600 = 3200 Hz < 3500); cấu trúc hài là "âm sắc" giúp phân biệt còi thật với âm khác trùng tần số cơ bản.
- **fs 22.050 Hz**: tần số lấy mẫu, > 2× thành phần cao nhất quan sát (3500 Hz) theo Nyquist; chọn bằng nửa chuẩn 44,1 kHz để tương thích dữ liệu sẵn có.

Sơ đồ phễu (vẽ được lên bảng): fs/2 = 11.025 ⊃ Mel 300–3500 ⊃ Lọc 500–1800 ⊃ Cơ bản 500–1600.

**[Sâu]** Nếu hỏi "đã lọc 1800 thì Mel lên 3500 làm gì": sườn Butterworth thoải nên hài trên 1800 Hz chỉ bị suy giảm chứ không triệt tiêu — dải Mel cao vẫn thu phần còn lại; đồng thời "phần dư phổ" vùng cao của nhiễu (còi hơi, phanh rít) khác hẳn còi thật, thành đặc trưng phân biệt cho mô hình. Còn **1–5 Hz** là miền đo khác hoàn toàn: tần số nhấp nháy ánh sáng đèn trên chuỗi khung hình, không thuộc phổ âm thanh.
⚠️ Câu này chỉ đứng vững khi quyển đã chốt số nhất quán (mục A3 `ra_soat_quyen_do_an.md`) — nếu quyển còn ghi 600–1500 ở 2.3.2 thì phải sửa trước.

## C2. Bộ lọc Butterworth là gì, vì sao chọn nó, "bậc 4" nghĩa là gì?

**[Ngắn]** Butterworth là bộ lọc có đáp ứng biên độ **phẳng tối đa trong dải thông** — không gợn sóng, nên không làm méo tương quan năng lượng giữa các tần số trong dải giữ lại, điều quan trọng khi phía sau còn trích đặc trưng phổ. "Bậc 4" quyết định độ dốc sườn chắn: mỗi bậc cho 20 dB/decade, bậc 4 cho 80 dB/decade — đủ dốc để chặn tiếng động cơ tần thấp mà chi phí tính toán vẫn nhỏ.

**[Sâu]** So sánh nếu bị hỏi: Chebyshev sườn dốc hơn cùng bậc nhưng gợn sóng trong dải thông; elliptic dốc nhất nhưng gợn cả hai dải; Bessel pha tuyến tính nhất nhưng sườn thoải. Butterworth là cân bằng tốt khi cần biên độ trung thực. Triển khai số: biến đổi bilinear sang miền z, thực hiện dạng **chuỗi khâu bậc hai (SOS/biquad)** để ổn định số học.

## C3. Pre-emphasis 0,97 để làm gì?

**[Ngắn]** y[n] = x[n] − 0,97·x[n−1] là bộ lọc thông cao bậc nhất, nâng các thành phần tần số cao vốn suy hao nhanh khi lan truyền. Nó cân bằng lại độ nghiêng phổ để bước MFCC phía sau không bị các thành phần tần thấp lấn át. Hệ số 0,95–0,97 là giá trị kinh điển trong xử lý tiếng nói.

## C4. Mel Spectrogram: vì sao thang Mel, vì sao 64 dải?

**[Ngắn]** Thang Mel mô phỏng tai người: phân giải mịn ở tần thấp, nén dần ở tần cao — Mel(f) = 2595·log₁₀(1 + f/700). Quy trình: STFT (FFT 1024 điểm, hop 512 → mỗi khung ~23 ms) → cho phổ qua dàn 64 bộ lọc tam giác đặt đều trên thang Mel từ 300–3500 Hz → lấy log năng lượng. 64 dải là cân bằng giữa độ phân giải phổ và chi phí tính toán; các nghiên cứu dùng 40–128.

**[Sâu]** Vì sao phải cắt khung + cửa sổ: tín hiệu còi là **phi tĩnh** (tần số đổi liên tục) nên phải phân tích từng đoạn ngắn coi như dừng; nhân cửa sổ (Hann) trước FFT để giảm **rò rỉ phổ** — hiện tượng cắt đột ngột ở biên khung sinh ra năng lượng giả tràn sang các tần số lân cận.

## C5. MFCC là gì, vì sao thêm DCT, vì sao dùng CẢ HAI đặc trưng?

**[Ngắn]** MFCC = lấy log năng lượng các dải Mel rồi biến đổi **cosine rời rạc (DCT)**, giữ 40 hệ số đầu. DCT làm hai việc: **nén** phần lớn thông tin hình dạng phổ vào ít hệ số đầu, và **giải tương quan** giữa các dải Mel vốn chồng lấn nhau. Em dùng cả hai vì chúng bổ sung: Mel Spectrogram giữ nguyên cấu trúc thời gian–tần số (hợp với CNN học "hình dạng" đường quét tần số của còi WAIL/YELP), MFCC cho bản mô tả cô đọng, bền với nhiễu. Thực nghiệm mô hình 2 nhánh cho kết quả tốt hơn từng nhánh riêng.

## C6. CNN "học" cái gì trên ảnh phổ? BiLSTM và Attention làm gì?

**[Ngắn]** CNN trượt các bộ lọc nhỏ (kernel) trên ảnh phổ — mỗi kernel là một mẫu cục bộ như "vệt năng lượng chéo lên" (đặc trưng WAIL quét tần số); tích chập cho đáp ứng lớn ở nơi phổ khớp mẫu. BiLSTM đọc chuỗi đặc trưng theo trục thời gian **cả hai chiều**, ghi nhớ ngữ cảnh dài — vì còi được định nghĩa bởi quy luật biến thiên trong hàng giây chứ không phải một khoảnh khắc. Attention chấm điểm mức quan trọng từng bước thời gian, lấy tổng có trọng số — để 0,3 giây có còi rõ không bị pha loãng bởi 1,7 giây nhiễu nền trong cùng cửa sổ.

**[Sâu]** LSTM giải quyết vanishing gradient của RNN thường bằng ô nhớ c_t và 3 cổng (quên f_t, vào i_t, ra o_t — mỗi cổng là sigmoid của tổ hợp tuyến tính đầu vào và trạng thái trước): c_t = f_t⊙c_{t−1} + i_t⊙tanh(...). Bi-directional = 2 LSTM chạy xuôi và ngược, ghép trạng thái [h→; h←]. Attention: e_i = f(h_i), α_i = softmax(e_i), context = Σα_i·h_i.

## C7. Voting 3/5 — vì sao không lấy luôn từng dự đoán?

**[Ngắn]** Dự đoán từng cửa sổ đơn lẻ có thể nhảy sai do một khoảnh khắc nhiễu — nếu kích hoạt/tắt hệ thị giác theo từng cửa sổ thì hệ sẽ "giật" liên tục. Voting 3/5 là bộ lọc quyết định: cần đa số trong 5 cửa sổ gần nhất (≈0,85 giây) đồng thuận. Bản chất là đánh đổi ~0,3–0,5 giây độ trễ lấy sự ổn định — với bài toán điều khiển pha đèn, nửa giây không đáng kể còn báo giả thì rất đắt. Số liệu thực địa: trước voting có các phát hiện sai lẻ tẻ, sau voting FP giảm từ 40 xuống 33 và FN từ 217 xuống 183 trên tập cửa sổ đánh giá.

---

# D. THỊ GIÁC MÁY TÍNH

## D1. YOLO hoạt động thế nào, một câu?

**[Ngắn]** YOLO nhìn toàn ảnh **một lượt duy nhất**: mạng tích chập chia ảnh thành lưới ô, mỗi vị trí dự đoán trực tiếp (tọa độ hộp, độ tin cậy, xác suất lớp) — nên nhanh hơn hẳn họ hai giai đoạn như Faster R-CNN vốn phải đề xuất vùng rồi phân loại lại. YOLO26n là bản nano: ít tham số, bỏ hậu xử lý NMS (dùng đầu dự đoán một-một khi suy luận), tối ưu cho CPU thiết bị biên.

**[Sâu]** mAP là gì (chắc chắn nên thuộc): với mỗi lớp, khớp dự đoán với nhãn thật theo điều kiện IoU ≥ 0,5; quét ngưỡng tin cậy từ cao xuống thấp vẽ đường Precision–Recall; **AP = diện tích dưới đường PR**; mAP = trung bình AP các lớp. mAP@0.5 = 0,607 của em: cao ở lớp lớn xuất hiện nhiều (car 0,931), thấp ở lớp hiếm (pedestrian 0,209 — ít mẫu) — nhưng nhiệm vụ của khối này chỉ là cấp ROI cho xe cơ giới, các lớp yếu không nằm trên đường quyết định xe ưu tiên.

## D2. Bộ lọc Kalman trong ByteTrack — nó "dự đoán" kiểu gì?

**[Ngắn]** Kalman duy trì trạng thái 8 chiều cho mỗi xe: tâm hộp, tỷ lệ khung, chiều cao và 4 vận tốc tương ứng, theo mô hình **vận tốc không đổi**. Giữa hai lần YOLO chạy, bước *predict* ngoại suy vị trí: x̂ = F·x (vị trí mới = vị trí cũ + vận tốc × thời gian) kèm tăng độ bất định P = FPFᵀ + Q. Khi YOLO trả kết quả mới, bước *update* trộn dự đoán với phép đo theo trọng số Kalman gain — tin phép đo nhiều hay tin mô hình nhiều tùy độ bất định từng bên. Nhờ vậy ROI được cập nhật mượt 15 FPS dù YOLO chỉ chạy ~1,7 lần/giây.

## D3. Thuật toán Hungarian và ghép cặp 2 tầng để làm gì?

**[Ngắn]** Sau khi có N track đang theo dõi và M hộp mới phát hiện, cần quyết định hộp nào thuộc xe nào — đây là bài toán gán tối ưu với chi phí = 1 − IoU giữa track dự đoán và hộp mới; thuật toán Hungarian giải chính xác trong thời gian đa thức. ByteTrack làm **2 tầng**: tầng 1 chỉ ghép các hộp tin cậy cao; tầng 2 đem các track chưa ghép được thử với các hộp **tin cậy thấp** — vì xe bị che khuất một phần thường vẫn được YOLO phát hiện nhưng điểm thấp; nhờ tận dụng chúng mà không mất dấu xe qua che khuất.

## D4. Vì sao phân tích màu trong HSV mà kênh đỏ phải 2 dải?

**[Ngắn]** Trong không gian HSV, màu sắc (Hue) tách riêng khỏi độ sáng nên bền hơn với thay đổi ánh sáng so với RGB thô. Trục Hue là **vòng tròn 0–360°** và màu đỏ nằm vắt qua điểm gấp 0°/360° — nên phải lấy hai dải [0–12°] và [168–180°] (thang OpenCV 0–180) ghép lại; màu xanh dương nằm gọn một dải nên chỉ cần một.

---

# E. FFT VÀ PHÉP ĐO ĐÈN

## E1. FFT khác DFT chỗ nào? Vì sao "nhanh"?

**[Ngắn]** FFT là thuật toán tính đúng kết quả của DFT nhưng bằng chia-để-trị: tách chuỗi N mẫu thành chẵn/lẻ đệ quy, tái sử dụng kết quả trung gian — độ phức tạp từ O(N²) xuống **O(N·logN)**. Với chuỗi ~75 mẫu (5 giây × 15 FPS) chi phí không đáng kể — đo thực tế 1,23 ms trên Pi.

## E2. Vì sao phải loại thành phần DC trước khi tìm đỉnh?

**[Ngắn]** Thành phần DC (trung bình tín hiệu) là "đỉnh" khổng lồ tại 0 Hz — chính là độ sáng nền của cả vùng xe. Không loại thì nó và các vệt tần số cực thấp của nó lấn át mọi đỉnh thật. Phép đo của em quan tâm **dao động quanh mức nền**, không quan tâm mức nền.

## E3. Độ phân giải và độ chính xác của phép đo tần số đèn?

**[Ngắn]** Độ phân giải phổ Δf = 1/T_quan_sát: cửa sổ 5 giây → 0,2 Hz — đủ mịn cho dải đèn vài Hz. Có 2 nguồn sai số cần lưu ý: (1) đỉnh rơi giữa hai vạch phổ (scalloping) — sai lệch tối đa ±Δf/2; (2) **jitter chu kỳ khung hình** — thực chất là lấy mẫu không đều, làm loang đỉnh; khắc phục được bằng nội suy tín hiệu về lưới thời gian đều trước FFT.

**[Sâu]** Trade-off nói được thành lời: cửa sổ dài hơn → Δf mịn hơn nhưng trễ phát hiện tăng và giả định "tín hiệu dừng trong cửa sổ" yếu đi (xe đi ngang khung hình chỉ vài giây). 5 giây là điểm cân bằng thực nghiệm.

## E4. Vì sao dùng trung vị chứ không dùng trung bình làm nền phổ?

**[Ngắn]** Trung bình bị chính đỉnh tín hiệu và vài đỉnh nhiễu lớn kéo lên — nền ước lượng sai cao, tỷ số đỉnh/nền bị nén lại. Trung vị là thống kê **bền vững**: 50% số vạch phổ có giá trị lớn bất thường cũng không dịch được nó — nên nó phản ánh đúng "mức sàn" của phổ. Đây là lý do tỷ số đỉnh/trung vị so sánh được giữa các điều kiện quan sát khác nhau.

## E5. Trường hợp ID 104: PNR "giả cao" thì loại bằng gì?

**[Ngắn]** Xe thường di chuyển qua khung tạo đường năng lượng hình chuông — sau khi trừ nền, thành phần biến thiên chậm này vẫn tạo đỉnh phổ ở biên dưới (~1 Hz, đúng chu kỳ xe đi qua khung). Hệ loại nó bằng tổ hợp tiêu chí: đỉnh phải nằm **trong dải tần đèn hợp lệ** (không phải sát biên), và ở bản cải tiến sau đồ án còn thêm **ngưỡng năng lượng màu tuyệt đối** — xe không có đèn đỏ/xanh thì năng lượng màu gần 0, dù phổ có đỉnh giả cũng bị chặn từ đầu.

## E6. Bộ lọc zero-phase là gì, vì sao cần? (phần mở rộng)

**[Ngắn]** Mọi bộ lọc nhân quả đều gây trễ pha phụ thuộc tần số — làm méo dạng sóng, dịch thời điểm các xung nhấp nháy. Kỹ thuật filtfilt lọc **xuôi rồi lọc ngược** cùng bộ lọc: pha của hai lượt triệt tiêu nhau → trễ pha bằng 0, biên độ được lọc hai lần (bậc hiệu dụng gấp đôi). Làm được vì xử lý **offline trên cửa sổ đệm** — ta đã có sẵn cả đoạn tín hiệu, không phải lọc thời gian thực từng mẫu.

## E7. Con số +366% PNR nghĩa là gì, có "ăn gian" không?

**[Ngắn]** Cùng một tín hiệu xe ID 13, cùng một phép FFT — chỉ khác khâu tiền xử lý: detrend thường cho PNR 5,97; lọc Butterworth 1–5 Hz zero-phase cho PNR 27,84. Bộ lọc không tạo thêm thông tin — nó **loại bỏ năng lượng ngoài dải quan tâm** (trôi nền, rung tần cao) nên nền phổ tụt xuống, đỉnh thật nổi lên. Tần số đỉnh không đổi (2,34 Hz) trước và sau lọc — chứng tỏ phép đo trung thực, chỉ tăng tỷ số tín hiệu trên nhiễu.

---

# F. HỆ THỐNG & VẬN HÀNH

## F1. Tổng độ trễ từ lúc còi vang đến lúc GPIO kích là bao nhiêu?

**[Ngắn]** Ba thành phần nối tiếp: xác nhận còi cần ≥3/5 cửa sổ ≈ 0,5–0,85 s; khởi động camera và tích lũy đủ ~2 s tín hiệu màu cho FFT; chu kỳ quyết định 0,5 s → tổng cỡ **3–4 giây** từ khi xe vào tầm nghe–nhìn. Với điều khiển pha đèn giao thông (chu kỳ đèn hàng chục giây, xe ưu tiên nghe thấy từ hàng trăm mét), mức trễ này nằm trong yêu cầu.

## F2. Ground truth 79 xe ưu tiên trong 12 ngày lấy bằng gì?

**[Ngắn]** Hệ đặt tại chốt bảo vệ cạnh đường (có nguồn điện, trông giữ được thiết bị), chạy liên tục 12 ngày, **vừa phát hiện thời gian thực vừa ghi âm lưu trữ toàn bộ**. Ground truth rà soát thủ công theo **hai chiều**: (1) kiểm định phát hiện — cuối ngày nghe lại từng đoạn hệ gắn cờ, phân loại thật/giả → 76 đúng, 8 báo giả; (2) tìm bỏ sót — quét lại bản ghi lưu trữ bằng chính mô hình nhưng **hạ ngưỡng nhạy** (gắn cờ mọi ứng viên), nghe xác minh từng ứng viên → tìm được 3 lượt còi thật bản online không báo. Tổng 79 lượt. "Một lượt" = một xe đi qua tầm thu một lần; còi ngắt quãng trong cùng lần đi qua vẫn tính một.

**[Sâu — câu thòng chủ động về giới hạn]** Ground truth này định nghĩa **trong tầm thu của hệ đo** — xe quá xa mà cả máy lẫn tai người không nghe được nằm ngoài phạm vi đánh giá; nguồn tham chiếu độc lập tuyệt đối (dữ liệu điều phối 115/114) là đề xuất cho giai đoạn thử nghiệm lớn hơn. Nói chủ động câu này = ghi điểm "hiểu phạm vi định nghĩa của phép đo".
⚠️ **Điều kiện tiên quyết**: chiều rà soát thứ (2) phải THỰC SỰ đã làm — nếu mới chỉ nghe lại các phát hiện thì con số "79 thực tế / 3 bỏ sót" không có phương pháp chống lưng ("không nghe đoạn hệ không báo sao biết sót 3?"). Bản ghi 12 ngày còn đó → chạy offline ngưỡng thấp (prob>0,3, voting 1/5) + nghe xác minh, một buổi tối là xong.

## F3. Chạy 24/7 ngoài trời — nhiệt độ, ổn định thế nào?

**[Ngắn]** Hệ đọc cảm biến nhiệt CPU định kỳ; cảnh báo ở 75°C và giảm tải ở 80°C bằng cách giãn tần suất suy luận — bản chất là **bộ điều khiển on/off có trễ** điều tiết tải theo nhiệt. Camera mất kết nối thì tự nối lại theo backoff mũ; log xoay vòng để không đầy thẻ nhớ. (Các cơ chế này thuộc phần hoàn thiện sau đồ án.)

## F4. Nếu hai xe ưu tiên cùng lúc? Nếu còi vang mà đèn bị che?

**[Ngắn]** Nhiều xe: mỗi xe một track ID riêng, phép đo màu/FFT chạy **độc lập theo từng ID** — hệ báo danh sách mọi ID thỏa điều kiện, không giới hạn một xe. Che đèn: hệ dừng ở mức "có còi, có xe, chưa xác thực đèn" — chấp nhận trễ thay vì báo bừa; đây là lựa chọn thiết kế nghiêng về chống báo giả, và là lý do hướng phát triển có đa camera.

## F5. Vì sao tin rằng AND 3 điều kiện giảm báo giả "theo cấp số nhân"?

**[Ngắn]** Ba kênh bằng chứng dựa trên ba hiện tượng vật lý khác nhau (âm thanh, hiện diện hình học, nhấp nháy quang học) nên các nguyên nhân gây giả gần như độc lập: còi hơi không làm đèn nháy 2–4 Hz; biển quảng cáo nhấp nháy không phát ra còi. Nếu xác suất giả từng kênh trong một khung thời gian là p₁, p₂, p₃ thì xác suất cả ba cùng giả ≈ p₁·p₂·p₃ — nhỏ hơn nhiều bậc. Em nói "gần đúng" vì độc lập không tuyệt đối (ví dụ mưa lớn ảnh hưởng cả âm thanh lẫn hình ảnh).

## F6. Hệ này khác gì một camera AI thương mại?

**[Ngắn]** Ba điểm: (1) luôn-lắng-nghe bằng âm thanh với tải cực thấp — camera AI thương mại phân tích hình liên tục nên tốn điện và tài nguyên hơn nhiều; (2) xác thực bằng **phép đo vật lý tần số đèn**, không phụ thuộc việc mô hình ảnh từng "nhìn thấy" loại xe ưu tiên đó trong dữ liệu huấn luyện; (3) chi phí — tận dụng camera giám sát sẵn có, chỉ thêm Pi và micro.

---

# G. ĐIỀU KHIỂN (PHẦN MỞ RỘNG — chỉ dùng khi hội đồng hỏi tới)

## G1. Vòng điều khiển iris: setpoint, đối tượng, bộ điều khiển là gì?

**[Ngắn]** Vòng bám giá trị đặt kinh điển: biến quá trình = độ sáng trung bình ROI; giá trị đặt I_ref = mức sáng cho chất lượng phép đo tốt nhất (rút từ khảo sát exposure); cơ cấu chấp hành = động cơ bước P-Iris; sai lệch e = I_ref − I_ROI đưa vào bộ PI, đầu ra là số bước dịch khẩu độ. Đối tượng thực chất là khâu khuếch đại tĩnh (tuyến tính hóa quanh điểm làm việc) cộng **trễ vận chuyển 1–3 khung hình** — nhận dạng bằng đáp ứng bậc thang, chỉnh Ki theo dự trữ pha, có anti-windup vì khẩu độ bão hòa hai đầu.

## G2. Autofocus không có setpoint sao gọi là vòng kín?

**[Ngắn]** Nó là vòng kín thuộc lớp khác: **điều khiển tìm cực trị**. Không đặt được "độ nét mong muốn" vì giá trị đỉnh không biết trước; nhưng tại đúng điểm nét, đạo hàm độ nét theo vị trí bằng 0 — nên "giá trị đặt" chính là **gradient = 0**. Bộ điều khiển nhiễu loạn nhỏ vị trí focus, quan sát độ nét tăng hay giảm, đi về phía tăng — perturb-and-observe, cùng nguyên lý MPPT điện mặt trời. Lưu ý sâu: tại đỉnh, khuếch đại tuyến tính hóa bằng 0 nên công cụ LTI bất lực đúng tại điểm làm việc — đó là lý do bản chất phải dùng nhiễu loạn dò, không phải chọn cho lạ.

## G3. Đo "độ nét" bằng gì?

**[Ngắn]** Chỉ số kinh điển là **phương sai của ảnh sau toán tử Laplacian**: Laplacian là đạo hàm bậc hai không gian, nhạy với biên; ảnh nét có nhiều biên sắc → phân bố đáp ứng Laplacian rộng → phương sai lớn; ảnh mờ thì biên bị nhòe → phương sai nhỏ. Chỉ vài phép tích chập 3×3, chạy tốt trên Pi. Thay thế: Tenengrad (năng lượng gradient Sobel) hoặc năng lượng dải tần cao của FFT ảnh.

---

# H. CÂU HỎI "BẪY" & CÂU KHÓ XỬ

## H1. "Phần mở rộng này có trong quyển không?"

> Dạ không ạ. Các nội dung ở phần 5 em thực hiện **sau khi hoàn thành quyển báo cáo**, với quan điểm đồ án là khởi đầu của một sản phẩm chứ không kết thúc ở việc nộp quyển. Toàn bộ mã nguồn, phần cứng và số liệu của phần này em có sẵn ở đây và có thể demo ngay nếu Hội đồng cho phép.

## H2. "mAP 0,6 là thấp, YOLO của em kém à?"

> Dạ, mAP tổng bị kéo xuống bởi các lớp hiếm mẫu như pedestrian (0,209); các lớp nằm trên đường quyết định của hệ — ô tô 0,931, xe máy 0,883 — đều cao. Và trong kiến trúc này YOLO không phải người ra quyết định: chỉ cần nó cấp ROI đủ ổn định cho phép đo đèn, sai sót còn lại được chặn bởi hai bằng chứng độc lập kia. Hướng cải thiện là bổ sung dữ liệu cho các lớp hiếm.

## H3. "873 ảnh mà đòi huấn luyện YOLO?"

> Dạ, em không huấn luyện từ đầu mà **fine-tune từ trọng số pretrained** trên tập dữ liệu lớn — mô hình đã biết "hình dạng ô tô", em chỉ dạy thêm điều kiện góc nhìn camera giao thông Việt Nam. Miền ứng dụng hẹp (góc camera cố định) + augmentation nên 873 ảnh cho kết quả chấp nhận được; mở rộng dữ liệu nằm trong hướng phát triển.

## H4. "Nếu xe ưu tiên tắt còi (đi làm nhiệm vụ im lặng) thì hệ mù à?"

> Dạ đúng — theo thiết kế, còi là điều kiện kích hoạt nên xe không phát tín hiệu ưu tiên sẽ không được nhận diện. Em chấp nhận giới hạn này có chủ đích: theo luật, xe ưu tiên muốn được nhường đường phải phát tín hiệu; xe đi im lặng tức không yêu cầu quyền ưu tiên tại nút giao. Đánh đổi lấy luôn-lắng-nghe tải thấp là hợp lý cho bài toán đặt ra.

## H5. "Còi giả / người phát nhạc còi trên loa thì sao?"

> Dạ chính vì kịch bản này mà em cần đủ 3 bằng chứng: loa phát tiếng còi sẽ kích hoạt được tầng âm thanh, nhưng không có phương tiện gắn đèn nhấp nháy đúng tần số trong khung hình nên hệ dừng ở mức cảnh giác, không kết luận. Đây là ưu thế căn bản của xác thực chéo đa cảm biến so với đơn cảm biến.

## H6. "Số 71,6 ms này đo với model nào?" (nếu chưa kịp benchmark lại)

> Dạ, số trong bảng đo với phiên bản INT8 tại thời điểm viết quyển. Em đang chuẩn hóa lại phép đo với đúng phiên bản đang triển khai và sẽ bổ sung; điểm quan trọng về mặt thiết kế là ngân sách thời gian: chu kỳ đánh giá 170 ms, nên suy luận âm thanh còn biên dự trữ trên 2 lần.

---

# I. BA CÂU HỎI TỰ ĐẶT ĐỂ LUYỆN (không có đáp án sẵn — tự viết trước ngày bảo vệ)

1. Ground truth 79 xe: ai đếm, đếm bằng gì, một "lượt" định nghĩa thế nào? (điền vào F2)
2. Con số float32 ↔ INT8 chính xác từ notebook quantize? (điền vào B3 và backup B2 của slide)
3. Dải lọc thông dải âm thanh cuối cùng chốt là bao nhiêu — và phải khớp ở: quyển (3 chỗ), slide 7, và câu trả lời miệng.
