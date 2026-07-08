#!/usr/bin/env python3
import socket
import struct
import numpy as np
import cv2
import time
import os

PORT = 8089
EXPECTED_SIZE = 1228800 # 640 * 640 * 3 BGR bytes

def run_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(('0.0.0.0', PORT))
    except Exception as e:
        print(f"[Error] Failed to bind to port {PORT}: {e}")
        return
        
    server_socket.listen(1)
    print(f"[*] TCP Receiver listening on port {PORT}...")
    print(f"[*] Waiting for camera connection...")

    conn, addr = server_socket.accept()
    print(f"[+] Camera connected from {addr[0]}:{addr[1]}")

    frame_count = 0
    start_time = time.time()
    
    # Create directory to save debug frames if needed
    os.makedirs('received_frames', exist_ok=True)

    try:
        while True:
            # 1. Read 4-byte length header (Big-Endian uint32)
            header_data = b""
            while len(header_data) < 4:
                packet = conn.recv(4 - len(header_data))
                if not packet:
                    print("[-] Connection closed by sender (no header).")
                    return
                header_data += packet
            
            # Unpack the size
            size = struct.unpack("!I", header_data)[0]
            if size != EXPECTED_SIZE:
                print(f"[Warning] Unexpected size header: {size} bytes (expected {EXPECTED_SIZE})")
            
            # 2. Read 'size' bytes of image payload
            payload_data = bytearray()
            while len(payload_data) < size:
                remaining = size - len(payload_data)
                packet = conn.recv(min(remaining, 65536))
                if not packet:
                    print("[-] Connection closed by sender during payload transfer.")
                    return
                payload_data.extend(packet)
            
            frame_count += 1
            
            # 3. Convert bytes back to numpy array (BGR Image)
            frame_bytes = np.frombuffer(payload_data, dtype=np.uint8)
            image = frame_bytes.reshape((640, 640, 3))
            
            # Calculate and print FPS every 30 frames
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = 30.0 / elapsed
                print(f"[Stream] Received {frame_count} frames | Current FPS: {fps:.2f} | Size: {size} bytes")
                start_time = time.time()
                
                # Save a debug image frame to verify the content visually
                save_path = f"received_frames/frame_{frame_count}.jpg"
                cv2.imwrite(save_path, image)
                print(f"    -> Frame saved to {save_path} for visual check.")
            
            # 4. (Optional) Show image if GUI is available
            try:
                cv2.imshow("CV25 Camera Stream (640x640)", image)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception:
                # GUI not available (e.g. running headlessly over SSH)
                pass

    except KeyboardInterrupt:
        print("\n[*] Stopping receiver...")
    finally:
        conn.close()
        server_socket.close()
        cv2.destroyAllWindows()
        print("[*] TCP Receiver stopped.")

if __name__ == "__main__":
    run_server()
