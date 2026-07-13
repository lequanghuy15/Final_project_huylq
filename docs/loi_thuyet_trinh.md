# LỜI THUYẾT TRÌNH BẢO VỆ ĐỒ ÁN (bám deck DATN_Slide_LeQuangHuy.pptx)

Tổng thời lượng mục tiêu: **12–13 phút** (trần 15). Số trong ngoặc là thời gian nói cho slide đó.
Nguyên tắc nói: câu ngắn, chủ động dừng 1 nhịp sau mỗi con số quan trọng; tay chỉ vào đúng vị trí trên hình khi nhắc đến.

---

## Slide 1–2 — Bìa (30 giây)

> Kính thưa Hội đồng, em là Lê Quang Huy, mã số sinh viên 20222297, ngành Kỹ thuật Điều khiển và Tự động hóa. Em xin trình bày đồ án tốt nghiệp với đề tài: **"Thiết kế hệ thống nhận diện xe ưu tiên tại biên sử dụng đa cảm biến phục vụ điều khiển giao thông thông minh"**, dưới sự hướng dẫn của thầy TS. Lê Minh Hoàng và cô PGS.TS. Nguyễn Thanh Hường.

## Slide 3 — Nội dung (15 giây)

> Bài trình bày của em gồm 6 phần: đặt vấn đề và mục tiêu, thiết kế hệ thống, kết quả thực nghiệm, kết luận, phần triển khai mở rộng sau đồ án, và hướng phát triển.

*(Không đọc từng dòng — lướt một câu là đủ.)*

## Slide 4 — Đặt vấn đề (60 giây)

> Tại các nút giao đô thị giờ cao điểm, xe cứu thương, cứu hỏa, công an rất khó lưu thông. Việc nhường đường hiện nay phụ thuộc hoàn toàn vào quan sát của người dân và điều tiết thủ công của cảnh sát giao thông.
>
> Trên thế giới, bài toán này được giải bằng V2X, GPS hoặc RFID — nhưng các giải pháp này đòi hỏi đầu tư hạ tầng đồng bộ trên cả phương tiện lẫn nút giao, chi phí rất lớn, chưa khả thi ở Việt Nam. Ngược lại, nếu chỉ dùng camera thì gặp che khuất và điều kiện ánh sáng; chỉ dùng âm thanh thì nhiễu và không định vị được xe.
>
> Vì vậy em đề xuất một hệ **đa cảm biến xử lý tại biên**: tận dụng hạ tầng camera giám sát đã phủ rộng ở đô thị, bổ sung một module thu âm chi phí thấp, toàn bộ xử lý chạy ngay tại nút giao trên một máy tính nhúng.

## Slide 5 — Mục tiêu (45 giây)

> Đồ án đặt ra 5 mục tiêu — và cuối bài em sẽ đối chiếu lại từng mục.
>
> Một, nhận diện xe ưu tiên bằng **ba bằng chứng độc lập**: nghe thấy còi, nhìn thấy phương tiện, và xác thực đèn nhấp nháy đúng đặc tính tuần hoàn. Hai, chạy liên tục trên thiết bị biên Raspberry Pi, không phụ thuộc máy chủ. Ba, khối thị giác — vốn tốn tài nguyên — chỉ được kích hoạt khi có còi. Bốn, chống báo động giả trong môi trường nhiễu thực tế. Năm, phạm vi là một nút giao với một micro và một camera.

## Slide 6 — Kiến trúc (60 giây)

*(Chỉ tay theo sơ đồ, đi từ trái sang phải.)*

> Đây là kiến trúc tổng thể, xây dựng trên nguyên tắc **kích hoạt theo sự kiện**. Thành phần duy nhất chạy thường trực là microphone và mô hình nhận dạng còi — đây là khối tiêu thụ tài nguyên thấp nhất. Khi và chỉ khi khối âm thanh xác nhận có còi ưu tiên, hệ thống mới đánh thức chuỗi thị giác: camera, mô hình phát hiện phương tiện YOLO26n, bộ bám vết ByteTrack, và khối phân tích đèn bằng FFT.
>
> Quyết định cuối cùng chỉ được đưa ra khi **cả ba điều kiện đồng thời thỏa mãn**. Thiết kế này vừa tiết kiệm năng lượng tính toán, vừa giảm báo động giả theo cấp số nhân — vì ba nguồn bằng chứng độc lập nhau về mặt vật lý.

## Slide 7 — Khối âm thanh (75 giây)

> Khối âm thanh được thiết kế như một chuỗi đo hoàn chỉnh. Tín hiệu được lấy mẫu ở 22.050 Hz — thỏa mãn tiêu chuẩn Nyquist với biên dự trữ rộng, vì năng lượng còi ưu tiên tập trung dưới 2 kHz. Tín hiệu đi qua **bộ lọc thông dải Butterworth** để giữ lại đúng dải tần đặc trưng của còi, loại tiếng động cơ tần thấp và nhiễu tần cao. Sau đó cắt thành cửa sổ 2 giây, trượt 0,17 giây — tức khoảng 6 lần đánh giá mỗi giây.
>
> Mỗi cửa sổ được trích xuất **hai đặc trưng song song**: Mel Spectrogram 64 dải giữ nguyên cấu trúc thời gian–tần số, và MFCC 40 hệ số cho biểu diễn phổ cô đọng. Hai đặc trưng bổ sung cho nhau, đi vào hai nhánh của mô hình **CNN-BiLSTM-Attention**: CNN học các mẫu năng lượng cục bộ trên phổ, BiLSTM học quy luật biến thiên tần số theo thời gian — đặc trưng của các kiểu còi WAIL, YELP, HI-LO — và Attention tập trung vào đoạn thực sự chứa còi.
>
> Cuối cùng, kết quả đi qua **cơ chế voting 3 trên 5 cửa sổ liên tiếp** — chỉ kích hoạt khi ít nhất 3 trong 5 lần đánh giá gần nhất vượt ngưỡng — để chống nhiễu giật cục.

## Slide 8 — Thị giác (45 giây)

> Trong hệ thống này, khối thị giác không trả lời câu hỏi "đây có phải xe ưu tiên không", mà chỉ trả lời "**trong khung hình có những phương tiện nào, ở đâu**" — vì hình dáng xe ưu tiên quá đa dạng để phân loại tin cậy bằng ngoại hình. Việc xác thực dành cho phép đo vật lý ở khối sau.
>
> Em dùng YOLO26n — phiên bản nano tối ưu cho thiết bị biên. Do tốc độ suy luận trên Pi thấp hơn tốc độ khung hình, em dùng **ByteTrack với bộ lọc Kalman**: giữa hai lần suy luận YOLO, vị trí từng xe được duy trì bằng dự đoán Kalman, mỗi xe giữ một mã ID ổn định kể cả khi bị che khuất một phần.

## Slide 9 — Xác thực đèn bằng FFT (75 giây)

> Đây là khối mang tính "đo lường" nhất của đồ án. Với mỗi xe đang được bám vết, em xây dựng một **tín hiệu một chiều theo thời gian**: cường độ trung bình của kênh màu đỏ và kênh xanh dương trong vùng ảnh của xe đó. Nếu xe có đèn ưu tiên đang nháy, tín hiệu này dao động tuần hoàn theo đúng nhịp chớp của đèn.
>
> Tín hiệu được loại thành phần một chiều rồi biến đổi **FFT**. Điểm mấu chốt là tiêu chí quyết định: em **không dùng ngưỡng biên độ tuyệt đối** — vì biên độ phụ thuộc khoảng cách, ánh sáng, thời gian phơi sáng — mà dùng **tỷ số giữa đỉnh phổ và trung vị nền phổ**. Trung vị là ước lượng nền bền vững, không bị kéo bởi vài đỉnh nhiễu cục bộ.
>
> Xe được kết luận có đèn ưu tiên khi tỷ số này vượt ngưỡng trên kênh đỏ **hoặc** kênh xanh — vì thực tế xe ưu tiên có loại chỉ đèn đỏ, chỉ đèn xanh, hoặc cả hai.

## Slide 10 — Tích hợp & phần cứng (45 giây)

> Ba bằng chứng được hợp nhất bằng điều kiện AND: còi **và** phương tiện **và** đèn nháy.
>
> Về phần cứng: em ước lượng tài nguyên trước khi chọn. Với STM32, công cụ STM32CubeAI cho thấy riêng YOLO cần khoảng 14 MB RAM — vượt mọi dòng STM32, chưa kể hệ thống cần OpenCV, SciPy. Vì vậy em chọn **Raspberry Pi 4**. Micro là **MEMS INMP441** — ADC tích hợp bên trong, truyền số qua I2S nên tránh nhiễu trên đường analog. Camera là loại RGB **điều chỉnh được exposure** — lựa chọn này có chủ đích, em sẽ chứng minh ở phần kết quả.

## Slide 11 — Kết quả mô hình âm thanh (45 giây)

> Trên tập kiểm thử độc lập 6.381 mẫu, mô hình đạt Precision và Recall xấp xỉ **0,98 đến 0,99** cho cả hai lớp, độ chính xác tổng thể khoảng **99%**, và diện tích dưới đường ROC đạt **0,9982**. *(Chỉ vào ma trận nhầm lẫn)* Đáng chú ý là tỷ lệ nhầm từ "không còi" sang "có còi" rất thấp — điều này quan trọng vì mỗi lần nhầm theo hướng đó là một lần đánh thức khối thị giác vô ích.

## Slide 12 — Kết quả thực địa (60 giây)

> Quan trọng hơn số liệu trên tập test, em đã triển khai hệ thống **chạy thật 12 ngày**, từ 15 đến 26 tháng 6, tại khu vực Hà Đông. Kết quả: phát hiện đúng **76 trên 79 lượt xe ưu tiên, đạt 96,2%**. Ba trường hợp bỏ sót đều rơi vào giờ cao điểm khi nhiều nguồn âm chồng lấn; tám trường hợp báo giả chủ yếu do còi hơi có phổ gần còi ưu tiên.
>
> *(Chỉ hình dưới)* Đây là hiệu quả của cơ chế voting: đường đứt màu đỏ là quyết định thô từng cửa sổ — có những cú nhảy sai; nền xanh là quyết định sau voting — ổn định, không kích hoạt–tắt liên tục.

## Slide 13 — Kết quả thị giác & đèn (60 giây)

> Khối phát hiện phương tiện đạt mAP@0.5 bằng **0,607** trên toàn bộ lớp, trong đó lớp ô tô đạt 0,931 — đủ để cung cấp vùng quan tâm ổn định cho phép đo.
>
> Phần xác thực đèn được đối chứng bằng **ba trường hợp**: nguồn sáng tĩnh cho phổ bẹt, không có đỉnh. Xe thường mang mã ID 104 cho đường năng lượng hình chuông trơn — tăng khi xe lại gần, giảm khi xe đi xa — đỉnh phổ chỉ ở 1,05 Hz, đó là chu kỳ chuyển động của cả chiếc xe chứ không phải đèn, và bị loại đúng. Còn xe ưu tiên ID 13 *(chỉ hình phải)* cho dao động bật–tắt rõ rệt và đỉnh phổ nổi bật trong dải tần đèn — được xác nhận đúng.

## Slide 14 — Exposure (45 giây)

> Trong quá trình thực nghiệm, em phát hiện một điều thú vị về phép đo: đèn ưu tiên là **nguồn sáng chủ động**, nên khi giảm thời gian phơi sáng, ảnh môi trường tối đi nhưng đèn vẫn đủ photon — kết quả là **độ tương phản giữa trạng thái bật và tắt tăng lên**, tín hiệu dao động sạch hơn, phổ rõ hơn. *(Chỉ hình: đường cam exposure 50% có biên độ dao động rõ hơn đường tím 100%.)*
>
> Phát hiện này chính là cơ sở cho vòng điều khiển tự động em trình bày ở phần mở rộng.

## Slide 15 — Tài nguyên (40 giây)

> Về tài nguyên trên Pi 4: mô hình âm thanh chiếm 61,8 MB, xử lý 71,6 mili-giây mỗi cửa sổ 2 giây — nhanh gấp đôi so với chu kỳ trượt 170 mili-giây. YOLO là nút thắt duy nhất với gần 600 mili-giây mỗi khung — và đã được giải bằng cơ chế bám vết Kalman giữa các lần suy luận. Tổng bộ nhớ toàn hệ khoảng **164,5 MB** — hoàn toàn trong khả năng của thiết bị biên giá rẻ.

## Slide 16 — Kết luận (50 giây)

> Đối chiếu với mục tiêu ban đầu: cả bốn nhóm mục tiêu đều đạt *(lướt tay theo bảng, mỗi dòng nửa câu)* — ba bằng chứng độc lập hoạt động, chạy ổn định trên Pi, kích hoạt theo sự kiện, và chống báo giả bằng voting cộng điều kiện AND.
>
> Em cũng xin nói thẳng các hạn chế: tầm phát hiện phụ thuộc khoảng cách micro; chất lượng phép đo đèn phụ thuộc ánh sáng và tham số camera; và tốc độ suy luận bị giới hạn bởi phần cứng. Chính các hạn chế này dẫn em đến phần tiếp theo.

## Slide 17 — Mở rộng: camera (50 giây)

> Sau khi hoàn thành quyển báo cáo, em quan niệm **nộp đồ án không có nghĩa là dừng nghiên cứu**, nên đã tiếp tục phát triển hệ thống.
>
> Thứ nhất là tự thiết kế phần cứng camera: board dựng quanh SoM Ambarella CV25, cảm biến Sony, ống kính varifocal với **ba động cơ bước điều khiển zoom, focus và khẩu độ P-Iris**. Mạch em vẽ trên Altium gồm 5 khối; firmware C++ bắt hình qua GStreamer, gửi frame về Pi qua TCP và nhận lệnh chỉnh ống kính qua UDP. Lý do làm việc này: **làm chủ hoàn toàn tham số thu nhận ảnh phục vụ phép đo** — đúng phát hiện về exposure em vừa trình bày.

## Slide 18 — Mở rộng: tín hiệu & điều khiển (60 giây)

> Thứ hai, em cải tiến khối đo đèn: bổ sung bộ lọc **Butterworth thông dải 1–5 Hz kiểu zero-phase** — lọc xuôi rồi lọc ngược để triệt tiêu trễ pha — đặt trước FFT. Bộ lọc khử được đường trôi nền hình chuông do xe di chuyển và nhiễu rung của khung bám. Kết quả trên xe ID 13: tỷ số đỉnh trên nhiễu tăng từ **5,97 lên 27,84 — tức tăng 366%** *(chỉ hình: hàng dưới cùng là tín hiệu và phổ sau lọc, đỉnh 2,34 Hz nổi hẳn)*.
>
> Em cũng hoàn thiện vận hành: máy trạng thái ba mức, đầu ra GPIO và MQTT để ghép với hệ điều khiển đèn tín hiệu, giám sát nhiệt.
>
> Hiện em đang phát triển tiếp **điều khiển ống kính vòng kín**: vòng PI giữ độ sáng vùng đo bằng khẩu độ P-Iris, và autofocus tìm cực trị theo độ nét ảnh.

## Slide 19 — Hướng phát triển (25 giây)

> Về hướng phát triển: mở rộng tập dữ liệu theo thời tiết và chủng loại xe; tăng tốc suy luận bằng NPU; kết hợp thêm V2X, GPS; tích hợp trực tiếp với tủ điều khiển đèn tín hiệu; và một hướng em thấy thú vị — ước lượng vận tốc xe ưu tiên qua độ dịch tần Doppler của còi.

## Slide 20 — Cảm ơn (10 giây)

> Em xin chân thành cảm ơn quý thầy cô đã lắng nghe. Em sẵn sàng nhận câu hỏi của Hội đồng.

---

## Ghi chú tổng

- Tổng theo phân bổ trên ≈ **12 phút 40 giây**. Nếu bị nhắc thời gian: cắt Slide 14 (exposure) xuống 1 câu và Slide 19 xuống 1 câu — tiết kiệm ~50 giây mà không mất mạch.
- Ba con số PHẢI thuộc lòng, nói không nhìn slide: **96,2% thực địa — 99%/0,9982 test — PNR +366%**.
- Khi hội đồng ngắt giữa chừng để hỏi: trả lời ngắn đúng câu hỏi rồi xin phép trình bày tiếp, đừng trả lời lan sang phần chưa nói đến.
- Câu chuyển giữa phần kết quả → mở rộng là "chính các hạn chế này dẫn em đến phần tiếp theo" — giữ đúng câu này, nó làm phần mở rộng nghe như tất yếu chứ không phải khoe thêm.
