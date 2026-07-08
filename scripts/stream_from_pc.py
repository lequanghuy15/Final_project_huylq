#!/usr/bin/env python3
"""
stream_from_pc.py — Chạy trên máy tính (PC) đóng vai trò bộ xử lý / phát hình ảnh.
Đọc từ camera hoặc file video và stream luồng MJPEG qua mạng LAN để Pi nhận qua HTTP.

Cách sử dụng trên PC:
    python stream_from_pc.py --source Xeuutien.mp4 --port 5000 --fps 15

Cách chạy trên Pi để nhận luồng:
    python3 main.py --camera http://<IP_CUA_PC>:5000/video_feed
"""

import argparse
import time
import cv2
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# Global variables for thread synchronization
output_frame = None
lock = threading.Lock()


class StreamServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP Server"""
    allow_reuse_address = True


class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global output_frame, lock
        
        if self.path == '/video_feed':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            
            try:
                while True:
                    with lock:
                        if output_frame is None:
                            time.sleep(0.01)
                            continue
                        # Encode frame to JPEG
                        ret, jpeg = cv2.imencode('.jpg', output_frame)
                        if not ret:
                            continue
                        frame_bytes = jpeg.tobytes()

                    # Send the frame boundary and header
                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame_bytes))
                    self.end_headers()
                    self.wfile.write(frame_bytes)
                    self.wfile.write(b'\r\n')
                    
                    # Sleep slightly to prevent high CPU usage on thread
                    time.sleep(0.03)
            except Exception as e:
                pass
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Page not found')


def capture_loop(source, target_fps, width, height, stop_event):
    global output_frame, lock
    
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Cannot open video source '{source}'")
        stop_event.set()
        return

    # Try setting size
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    fps = cap.get(cv2.CAP_PROP_FPS) or target_fps
    interval = 1.0 / fps
    print(f"Capturing from '{source}' at {fps:.1f} FPS...")
    
    while not stop_event.is_set():
        t0 = time.monotonic()
        ret, frame = cap.read()
        
        if not ret:
            # If reading a file, loop back to the beginning
            if isinstance(source, str) and source.lower().endswith(('.mp4', '.mkv', '.avi')):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                print("Failed to grab frame. Reconnecting...")
                time.sleep(1.0)
                cap = cv2.VideoCapture(source)
                continue

        with lock:
            output_frame = frame.copy()
            
        elapsed = time.monotonic() - t0
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
            
    cap.release()


def main():
    parser = argparse.ArgumentParser(description="MJPEG Streamer from PC to Pi")
    parser.add_argument("--source", default="0", help="Video source (index like 0 or file path/RTSP)")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default 5000)")
    parser.add_argument("--fps", type=int, default=15, help="Target FPS (default 15)")
    parser.add_argument("--width", type=int, default=1280, help="Width (default 1280)")
    parser.add_argument("--height", type=int, default=720, help="Height (default 720)")
    args = parser.parse_args()

    # Convert source to int if it's a digit
    src = int(args.source) if args.source.isdigit() else args.source
    
    stop_event = threading.Event()
    
    # Start capture thread
    cap_thread = threading.Thread(
        target=capture_loop,
        args=(src, args.fps, args.width, args.height, stop_event),
        daemon=True
    )
    cap_thread.start()
    
    # Start server
    server_address = ('', args.port)
    server = StreamServer(server_address, StreamingHandler)
    
    print(f"============================================================")
    print(f" MJPEG Server started at http://localhost:{args.port}/video_feed")
    print(f" Stream from PC over LAN to Pi: http://<PC_IP_OR_HOSTNAME>:{args.port}/video_feed")
    print(f" Press Ctrl+C to stop.")
    print(f"============================================================")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        stop_event.set()
        server.server_close()
        print("Server stopped.")


if __name__ == '__main__':
    main()
