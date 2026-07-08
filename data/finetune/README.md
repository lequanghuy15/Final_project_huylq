# `data/finetune/` — Dữ liệu thật thu thập sau triển khai

Thư mục này chứa các mẫu audio **thật** thu thập được khi hệ thống chạy thực tế (khác với `data/audio/` — dữ liệu còi tổng hợp dùng để train mô hình lần đầu). Dùng để finetune lại Siren GRU theo chu trình mô tả trong `drafts/siren_detection_colab.ipynb` (mục "Production Loop"): triển khai → thu thập mẫu thật → thêm vào đây → chạy lại notebook finetune → export model mới.

## Cấu trúc

```
data/finetune/
├── positive/         # Đoạn còi ưu tiên thật ghi được ngoài thực địa (label 1)
|── false_positives/  # Đoạn hệ thống báo động nhầm ngoài thực tế (label 0)
```

Định dạng file: `.wav`, cùng sample rate với pipeline suy diễn (`22050 Hz`, mono).

## Sử dụng

Đưa các file `.wav` mới vào đúng thư mục tương ứng, sau đó chạy lại notebook finetune (tham khảo `drafts/ELCOM_Siren_v4_finetune_cells.ipynb`, `drafts/siren_v4_gru_finetune.ipynb`) để cập nhật mô hình `models/siren_int8.tflite`.
