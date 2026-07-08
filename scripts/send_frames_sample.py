"""
send_frames_sample.py — Script mẫu gửi luồng ảnh RAW (Zero-CPU Decode) từ PC sang Raspberry Pi.
Chạy script này trên thiết bị phát (PC/Bộ giải mã cứng) để truyền frame qua LAN sang Pi.
"""

import cv2
import socket
import struct
import time
import argparse

def main():
    parser = argparse.ArgumentParser(description="RAW Frame TCP Sender")
    parser.add_argument("--source", default="0", help="Camera index, RTSP link, hoặc đường dẫn video file")
    parser.add_argument("--host", required=True, help="Địa chỉ IP của Raspberry Pi (nhận luồng)")
    parser.add_argument("--port", type=int, default=8089, help="Cổng TCP nhận luồng trên Pi (mặc định: 8089)")
    parser.add_argument("--fps", type=int, default=15, help="Tốc độ gửi frame mong muốn")
    args = parser.parse_args()

    # Thử convert index sang số nguyên nếu là webcam
    source = args.source
    if source.isdigit():
        source = int(source)

    # Khởi tạo camera
    print(f"Đang mở nguồn video: {source}...")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Lỗi: Không thể mở nguồn video.")
        return

    # Kết nối TCP Client tới Pi (Pi đóng vai trò Server socket nhận luồng)
    print(f"Đang kết nối tới Raspberry Pi tại {args.host}:{args.port}...")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((args.host, args.port))
        print("Kết nối thành công! Đang bắt đầu truyền luồng ảnh...")
    except Exception as e:
        print(f"Lỗi kết nối tới Pi: {e}")
        cap.release()
        return

    interval = 1.0 / args.fps
    frame_count = 0

    try:
        while True:
            t0 = time.monotonic()

            ret, frame = cap.read()
            if not ret:
                print("Hết luồng video hoặc lỗi đọc frame.")
                break

            # 1. Giải quyết khâu nặng nhất: Resize về đúng 640x640 tại thiết bị phát
            resized_frame = cv2.resize(frame, (640, 640))

            # 2. Lấy mảng byte thô hệ màu BGR (Width * Height * 3 = 1,228,800 bytes)
            raw_bytes = resized_frame.tobytes()
            payload_len = len(raw_bytes)

            # 3. Đóng gói Header (4 bytes chứa độ dài payload) + Payload (raw bytes)
            header = struct.pack("!I", payload_len)

            # 4. Gửi qua socket LAN
            client_socket.sendall(header + raw_bytes)

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Đã truyền {frame_count} frames...")

            # Duy trì đúng tốc độ gửi FPS
            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nĐã dừng truyền luồng bởi người dùng.")
    except Exception as e:
        print(f"\nLỗi đường truyền socket: {e}")
    finally:
        print("Đang giải phóng tài nguyên...")
        client_socket.close()
        cap.release()
        print("Hoàn tất.")

if __name__ == "__main__":
    main()
