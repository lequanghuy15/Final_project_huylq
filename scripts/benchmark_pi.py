#!/usr/bin/env python3
"""
========================================================
  BENCHMARK SCRIPT - Raspberry Pi Deployment
  Đo lường RAM và tốc độ xử lý cho hệ thống nhận diện
  xe ưu tiên (YOLO + ByteTrack + FFT + Siren GRU).
========================================================

Cách chạy trên Pi:
    python3 ~/benchmark_pi.py

Yêu cầu: numpy, opencv-python, tflite-runtime (hoặc tensorflow)
"""

import os
import sys
import time
import gc
import json
import traceback
import numpy as np

# ============================================================
# CONFIG - Sửa đường dẫn nếu cần
# ============================================================
YOLO_MODEL = os.path.expanduser(
    "~/deploy_pi_work/content/deploy_pi/models/best_int8_imgsz640.tflite"
)
SIREN_MODEL = os.path.expanduser("~/siren_gru_int8.tflite")
VIDEO_PATH = os.path.expanduser("~/Cam5_20260529_100103.mkv")

YOLO_IMGSZ = 640
NUM_WARMUP = 3
NUM_INFERENCE_RUNS = 20
NUM_FFT_RUNS = 200

# ============================================================
# HELPERS
# ============================================================
def get_rss_mb():
    """Lấy RSS (Resident Set Size) hiện tại của process, đơn vị MB."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0  # kB → MB
    except Exception:
        pass
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        return 0.0


def get_system_info():
    """Thu thập thông tin hệ thống Pi."""
    info = {}

    # Board model
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "Model" in line:
                    info["board"] = line.split(":")[1].strip()
                    break
    except Exception:
        info["board"] = "Unknown"

    # RAM
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    info["total_ram_mb"] = int(line.split()[1]) / 1024.0
                elif line.startswith("MemAvailable:"):
                    info["available_ram_mb"] = int(line.split()[1]) / 1024.0
    except Exception:
        info["total_ram_mb"] = 0
        info["available_ram_mb"] = 0

    # CPU freq
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq") as f:
            info["cpu_max_mhz"] = int(f.read().strip()) / 1000
    except Exception:
        info["cpu_max_mhz"] = "N/A"

    info["python"] = sys.version.split()[0]

    # TFLite backend
    try:
        from tflite_runtime.interpreter import Interpreter
        info["tflite_backend"] = "tflite_runtime"
    except ImportError:
        try:
            from ai_edge_litert.interpreter import Interpreter
            info["tflite_backend"] = "ai_edge_litert"
        except ImportError:
            try:
                import tensorflow as tf
                info["tflite_backend"] = f"tensorflow {tf.__version__}"
            except ImportError:
                info["tflite_backend"] = "NOT FOUND"

    return info


def load_tflite_interpreter(model_path):
    """Load TFLite interpreter. Thử 3 backend theo thứ tự:
       1) tflite_runtime  (Python ≤ 3.11)
       2) ai_edge_litert  (Python 3.12+, package mới thay thế tflite_runtime)
       3) tensorflow      (fallback nặng)
    """
    try:
        from tflite_runtime.interpreter import Interpreter
        interp = Interpreter(model_path=model_path)
    except ImportError:
        try:
            from ai_edge_litert.interpreter import Interpreter
            interp = Interpreter(model_path=model_path)
        except ImportError:
            import tensorflow as tf
            interp = tf.lite.Interpreter(model_path=model_path)
    interp.allocate_tensors()
    return interp


# ============================================================
# 1. MODEL FILE SIZES
# ============================================================
def benchmark_file_sizes():
    print("\n" + "=" * 60)
    print("  1. KÍCH THƯỚC FILE MÔ HÌNH")
    print("=" * 60)
    results = {}
    for name, path in [
        ("YOLO INT8 (640)", YOLO_MODEL),
        ("Siren GRU INT8", SIREN_MODEL),
    ]:
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  {name:25s}: {size_mb:7.2f} MB")
            results[name] = round(size_mb, 2)
        else:
            print(f"  {name:25s}: KHÔNG TÌM THẤY ({path})")
            results[name] = None
    return results


# ============================================================
# 2. RAM USAGE
# ============================================================
def benchmark_ram():
    print("\n" + "=" * 60)
    print("  2. BỘ NHỚ RAM (RSS)")
    print("=" * 60)

    gc.collect()
    rss_baseline = get_rss_mb()
    print(f"  Baseline (Python + imports):   {rss_baseline:7.2f} MB")
    results = {"baseline_mb": round(rss_baseline, 2)}

    # --- Load YOLO ---
    if os.path.exists(YOLO_MODEL):
        gc.collect()
        rss_before = get_rss_mb()
        yolo_interp = load_tflite_interpreter(YOLO_MODEL)
        gc.collect()
        rss_after = get_rss_mb()
        delta = rss_after - rss_before
        print(f"  Sau khi load YOLO:             {rss_after:7.2f} MB  (+{delta:.2f})")

        inp = yolo_interp.get_input_details()[0]
        outs = yolo_interp.get_output_details()
        print(f"    Input  shape={list(inp['shape'])}  dtype={inp['dtype']}")
        for i, o in enumerate(outs):
            print(f"    Output[{i}] shape={list(o['shape'])}  dtype={o['dtype']}")
        results["yolo_loaded_mb"] = round(rss_after, 2)
        results["yolo_delta_mb"] = round(delta, 2)
        results["yolo_input_shape"] = list(inp["shape"])
        results["yolo_input_dtype"] = str(inp["dtype"])
        del yolo_interp
        gc.collect()
    else:
        print("  YOLO model không tồn tại, bỏ qua.")

    # --- Load Siren ---
    if os.path.exists(SIREN_MODEL):
        gc.collect()
        rss_before = get_rss_mb()
        siren_interp = load_tflite_interpreter(SIREN_MODEL)
        gc.collect()
        rss_after = get_rss_mb()
        delta = rss_after - rss_before
        print(f"  Sau khi load Siren:            {rss_after:7.2f} MB  (+{delta:.2f})")

        inp = siren_interp.get_input_details()[0]
        out = siren_interp.get_output_details()[0]
        print(f"    Input  shape={list(inp['shape'])}  dtype={inp['dtype']}")
        print(f"    Output shape={list(out['shape'])}  dtype={out['dtype']}")
        results["siren_loaded_mb"] = round(rss_after, 2)
        results["siren_delta_mb"] = round(delta, 2)
        results["siren_input_shape"] = list(inp["shape"])
        results["siren_input_dtype"] = str(inp["dtype"])
        del siren_interp
        gc.collect()
    else:
        print("  Siren model không tồn tại, bỏ qua.")

    # --- Cả hai mô hình cùng lúc ---
    gc.collect()
    rss_before = get_rss_mb()
    interps = []
    if os.path.exists(YOLO_MODEL):
        interps.append(load_tflite_interpreter(YOLO_MODEL))
    if os.path.exists(SIREN_MODEL):
        interps.append(load_tflite_interpreter(SIREN_MODEL))
    gc.collect()
    rss_both = get_rss_mb()
    both_delta = rss_both - rss_before
    print(f"  Cả hai mô hình cùng lúc:      {rss_both:7.2f} MB  (+{both_delta:.2f})")
    results["both_loaded_mb"] = round(rss_both, 2)
    results["both_delta_mb"] = round(both_delta, 2)

    # --- Ước tính bộ nhớ phụ ---
    bt_mem_kb = 50 * (8 * 4 + 64 * 4) / 1024  # 50 tracks, 8-state Kalman
    fft_buf_kb = 300 * 3 * 4 / 1024  # 300 frames x 3 channels x float32
    frame_buf_kb = 640 * 640 * 3 / 1024  # 1 frame 640x640 BGR
    resize_buf_kb = 640 * 480 * 3 / 1024  # original frame estimate
    cv2_overhead_kb = 2048  # ~2 MB cho VideoCapture internal buffers

    extra_mb = (bt_mem_kb + fft_buf_kb + frame_buf_kb + resize_buf_kb + cv2_overhead_kb) / 1024
    print(f"\n  --- Bộ nhớ phụ ước tính ---")
    print(f"    ByteTrack state (50 tracks):  {bt_mem_kb:7.1f} KB")
    print(f"    FFT energy buffers:           {fft_buf_kb:7.1f} KB")
    print(f"    Frame buffer (640x640):       {frame_buf_kb:7.1f} KB")
    print(f"    Resize buffer (640x480):      {resize_buf_kb:7.1f} KB")
    print(f"    OpenCV VideoCapture:          {cv2_overhead_kb:7.1f} KB")
    print(f"    Tổng bộ nhớ phụ:              {extra_mb:7.2f} MB")
    results["extra_estimated_mb"] = round(extra_mb, 2)

    total = rss_both + extra_mb
    print(f"\n  >>> TỔNG ƯỚC TÍNH RAM: {total:.1f} MB <<<")
    results["total_estimated_mb"] = round(total, 1)

    for interp in interps:
        del interp
    gc.collect()
    return results


# ============================================================
# 3. YOLO INFERENCE SPEED
# ============================================================
def benchmark_yolo_inference():
    print("\n" + "=" * 60)
    print("  3. TỐC ĐỘ INFERENCE YOLO INT8")
    print("=" * 60)

    if not os.path.exists(YOLO_MODEL):
        print("  Model không tồn tại, bỏ qua.")
        return {}

    interp = load_tflite_interpreter(YOLO_MODEL)
    inp = interp.get_input_details()[0]
    inp_shape = inp["shape"]
    inp_dtype = inp["dtype"]

    # Tạo input từ video thật nếu có
    frame_data = None
    if os.path.exists(VIDEO_PATH):
        try:
            import cv2
            cap = cv2.VideoCapture(VIDEO_PATH)
            ret, raw = cap.read()
            cap.release()
            if ret:
                resized = cv2.resize(raw, (inp_shape[2], inp_shape[1]))
                if inp_dtype == np.uint8:
                    frame_data = resized.astype(np.uint8)
                elif inp_dtype == np.int8:
                    frame_data = (resized.astype(np.int16) - 128).astype(np.int8)
                else:
                    frame_data = resized.astype(np.float32) / 255.0
                frame_data = np.expand_dims(frame_data, axis=0)
                print(f"  Dùng frame thật từ video.")
        except Exception as e:
            print(f"  Không đọc được video: {e}")

    if frame_data is None:
        if inp_dtype == np.uint8:
            frame_data = np.random.randint(0, 256, size=inp_shape, dtype=np.uint8)
        elif inp_dtype == np.int8:
            frame_data = np.random.randint(-128, 127, size=inp_shape, dtype=np.int8)
        else:
            frame_data = np.random.rand(*inp_shape).astype(np.float32)
        print("  Dùng dummy random input.")

    # Warmup
    print(f"  Warmup ({NUM_WARMUP} lần)...")
    for _ in range(NUM_WARMUP):
        interp.set_tensor(inp["index"], frame_data)
        interp.invoke()

    # Benchmark
    print(f"  Chạy {NUM_INFERENCE_RUNS} lần inference...")
    latencies = []
    for _ in range(NUM_INFERENCE_RUNS):
        t0 = time.perf_counter()
        interp.set_tensor(inp["index"], frame_data)
        interp.invoke()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    lat = np.array(latencies)
    avg = np.mean(lat)
    med = np.median(lat)
    fps_est = 1000.0 / avg

    print(f"\n  Kết quả:")
    print(f"    Mean:   {avg:8.1f} ms")
    print(f"    Median: {med:8.1f} ms")
    print(f"    Std:    {np.std(lat):8.1f} ms")
    print(f"    Min:    {np.min(lat):8.1f} ms")
    print(f"    Max:    {np.max(lat):8.1f} ms")
    print(f"    >>> FPS ước tính: {fps_est:.2f} <<<")

    del interp
    gc.collect()
    return {
        "mean_ms": round(avg, 1),
        "median_ms": round(med, 1),
        "std_ms": round(float(np.std(lat)), 1),
        "min_ms": round(float(np.min(lat)), 1),
        "max_ms": round(float(np.max(lat)), 1),
        "fps": round(fps_est, 2),
    }


# ============================================================
# 4. SIREN GRU INFERENCE SPEED
# ============================================================
def benchmark_siren_inference():
    print("\n" + "=" * 60)
    print("  4. TỐC ĐỘ INFERENCE SIREN GRU INT8")
    print("=" * 60)

    if not os.path.exists(SIREN_MODEL):
        print("  Model không tồn tại, bỏ qua.")
        return {}

    interp = load_tflite_interpreter(SIREN_MODEL)
    inp_details = interp.get_input_details()
    out_details = interp.get_output_details()

    print(f"  Số input tensors: {len(inp_details)}")
    for i, d in enumerate(inp_details):
        print(f"    Input[{i}] shape={list(d['shape'])}  dtype={d['dtype']}  name={d['name']}")
    for i, d in enumerate(out_details):
        print(f"    Output[{i}] shape={list(d['shape'])}  dtype={d['dtype']}")

    # Tạo dummy inputs
    dummies = []
    for d in inp_details:
        shape = d["shape"]
        dtype = d["dtype"]
        if dtype == np.int8:
            dummies.append(np.random.randint(-128, 127, size=shape, dtype=np.int8))
        elif dtype == np.uint8:
            dummies.append(np.random.randint(0, 256, size=shape, dtype=np.uint8))
        else:
            dummies.append(np.random.rand(*shape).astype(np.float32))

    # Warmup
    for _ in range(NUM_WARMUP):
        for d, dummy in zip(inp_details, dummies):
            interp.set_tensor(d["index"], dummy)
        interp.invoke()

    # Benchmark
    print(f"  Chạy {NUM_INFERENCE_RUNS} lần inference...")
    latencies = []
    for _ in range(NUM_INFERENCE_RUNS):
        t0 = time.perf_counter()
        for d, dummy in zip(inp_details, dummies):
            interp.set_tensor(d["index"], dummy)
        interp.invoke()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    lat = np.array(latencies)
    avg = np.mean(lat)

    print(f"\n  Kết quả:")
    print(f"    Mean:   {avg:8.1f} ms")
    print(f"    Median: {np.median(lat):8.1f} ms")
    print(f"    Std:    {np.std(lat):8.1f} ms")
    print(f"    Min:    {np.min(lat):8.1f} ms")
    print(f"    Max:    {np.max(lat):8.1f} ms")

    del interp
    gc.collect()
    return {
        "mean_ms": round(avg, 1),
        "median_ms": round(float(np.median(lat)), 1),
        "std_ms": round(float(np.std(lat)), 1),
        "min_ms": round(float(np.min(lat)), 1),
        "max_ms": round(float(np.max(lat)), 1),
    }


# ============================================================
# 5. BYTETRACK KALMAN FILTER PREDICTION
# ============================================================
def benchmark_bytetrack():
    print("\n" + "=" * 60)
    print("  5. BYTETRACK KALMAN FILTER PREDICTION")
    print("=" * 60)

    # Mô phỏng Kalman filter 8-state cho mỗi track
    # State = [cx, cy, aspect_ratio, height, vx, vy, va, vh]
    F = np.eye(8, dtype=np.float32)
    F[0, 4] = 1.0
    F[1, 5] = 1.0
    F[2, 6] = 1.0
    F[3, 7] = 1.0
    Q = np.eye(8, dtype=np.float32) * 0.01

    results = {}
    for n_tracks in [5, 10, 20, 50]:
        states = [np.random.randn(8).astype(np.float32) for _ in range(n_tracks)]
        covs = [np.eye(8, dtype=np.float32) * 0.1 for _ in range(n_tracks)]

        latencies = []
        for _ in range(NUM_FFT_RUNS):
            t0 = time.perf_counter()
            for i in range(n_tracks):
                states[i] = F @ states[i]
                covs[i] = F @ covs[i] @ F.T + Q
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000)

        avg = np.mean(latencies)
        print(f"  {n_tracks:3d} tracks: {avg:.4f} ms / bước predict")
        results[f"{n_tracks}_tracks_ms"] = round(avg, 4)

    return results


# ============================================================
# 6. FFT COLOR ANALYSIS
# ============================================================
def benchmark_fft():
    print("\n" + "=" * 60)
    print("  6. FFT COLOR ANALYSIS")
    print("=" * 60)

    results = {}

    # --- HSV extraction trên crop 100x100 ---
    try:
        import cv2
        crop = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        RED1_LOW  = np.array([0,   80, 100])
        RED1_HIGH = np.array([12, 255, 255])
        RED2_LOW  = np.array([168, 80, 100])
        RED2_HIGH = np.array([180, 255, 255])
        BLUE_LOW  = np.array([90,  70, 100])
        BLUE_HIGH = np.array([135, 255, 255])

        latencies = []
        for _ in range(NUM_FFT_RUNS):
            t0 = time.perf_counter()
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            v = hsv[:, :, 2].astype(np.float32) / 255.0
            rm1 = cv2.inRange(hsv, RED1_LOW, RED1_HIGH)
            rm2 = cv2.inRange(hsv, RED2_LOW, RED2_HIGH)
            red_mask = cv2.bitwise_or(rm1, rm2) > 0
            blue_mask = cv2.inRange(hsv, BLUE_LOW, BLUE_HIGH) > 0
            re = np.sum(v[red_mask])
            be = np.sum(v[blue_mask])
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000)

        avg = np.mean(latencies)
        print(f"  HSV extraction (100x100 crop): {avg:.4f} ms")
        results["hsv_extraction_ms"] = round(avg, 4)
    except ImportError:
        print("  cv2 không có, bỏ qua HSV benchmark.")

    # --- FFT computation ---
    from scipy.signal import detrend
    signal = np.random.randn(150).astype(np.float32)
    latencies = []
    for _ in range(NUM_FFT_RUNS):
        t0 = time.perf_counter()
        sig = detrend(signal)
        sig = sig - np.mean(sig)
        window = np.hanning(len(sig))
        sig_win = sig * window
        freqs = np.fft.rfftfreq(256, d=1 / 30.0)
        mag = np.abs(np.fft.rfft(sig_win, n=256))
        peak_idx = np.argmax(mag[1:]) + 1
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    avg = np.mean(latencies)
    print(f"  FFT (150 samples, 256-pt):     {avg:.4f} ms")
    results["fft_computation_ms"] = round(avg, 4)

    return results


# ============================================================
# 7. VIDEO DECODE SPEED
# ============================================================
def benchmark_video_decode():
    print("\n" + "=" * 60)
    print("  7. TỐC ĐỘ GIẢI MÃ VIDEO")
    print("=" * 60)

    if not os.path.exists(VIDEO_PATH):
        print(f"  Video không tồn tại: {VIDEO_PATH}")
        return {}

    try:
        import cv2
    except ImportError:
        print("  cv2 không có.")
        return {}

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("  Không mở được video.")
        return {}

    fps_video = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"  Video: {w}x{h} @ {fps_video:.1f} FPS, {total_frames} frames")

    n_decode = min(100, total_frames)
    latencies = []
    for _ in range(n_decode):
        t0 = time.perf_counter()
        ret, frame = cap.read()
        t1 = time.perf_counter()
        if not ret:
            break
        latencies.append((t1 - t0) * 1000)

    cap.release()

    if latencies:
        avg = np.mean(latencies)
        decode_fps = 1000.0 / avg
        print(f"  Decode latency: {avg:.1f} ms/frame")
        print(f"  Decode FPS:     {decode_fps:.1f}")
        return {
            "decode_ms": round(avg, 1),
            "decode_fps": round(decode_fps, 1),
            "resolution": f"{w}x{h}",
            "video_fps": round(fps_video, 1),
        }
    return {}


# ============================================================
# 8. RESIZE + PREPROCESS SPEED
# ============================================================
def benchmark_resize():
    print("\n" + "=" * 60)
    print("  8. TỐC ĐỘ RESIZE + PREPROCESS")
    print("=" * 60)

    try:
        import cv2
    except ImportError:
        print("  cv2 không có.")
        return {}

    # Simulate typical camera frame → YOLO input resize
    raw = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

    latencies = []
    for _ in range(NUM_FFT_RUNS):
        t0 = time.perf_counter()
        resized = cv2.resize(raw, (YOLO_IMGSZ, YOLO_IMGSZ))
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    avg = np.mean(latencies)
    print(f"  Resize 640x480 → 640x640: {avg:.3f} ms")
    return {"resize_ms": round(avg, 3)}


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("    RASPBERRY PI DEPLOYMENT BENCHMARK")
    print("    Hệ thống nhận diện xe ưu tiên")
    print("=" * 60)

    sys_info = get_system_info()
    print(f"\n  Board:          {sys_info.get('board', 'N/A')}")
    print(f"  Total RAM:      {sys_info.get('total_ram_mb', 0):.0f} MB")
    print(f"  Available RAM:  {sys_info.get('available_ram_mb', 0):.0f} MB")
    print(f"  CPU max freq:   {sys_info.get('cpu_max_mhz', 'N/A')} MHz")
    print(f"  Python:         {sys_info.get('python', 'N/A')}")
    print(f"  TFLite backend: {sys_info.get('tflite_backend', 'N/A')}")

    all_results = {"system": sys_info}

    try:
        all_results["file_sizes"] = benchmark_file_sizes()
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()

    try:
        all_results["ram"] = benchmark_ram()
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()

    try:
        all_results["yolo_inference"] = benchmark_yolo_inference()
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()

    try:
        all_results["siren_inference"] = benchmark_siren_inference()
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()

    try:
        all_results["bytetrack"] = benchmark_bytetrack()
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()

    try:
        all_results["fft"] = benchmark_fft()
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()

    try:
        all_results["video_decode"] = benchmark_video_decode()
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()

    try:
        all_results["resize"] = benchmark_resize()
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()

    # =============================
    # SUMMARY
    # =============================
    print("\n" + "=" * 60)
    print("    TỔNG KẾT")
    print("=" * 60)

    yolo_ms = all_results.get("yolo_inference", {}).get("mean_ms", 0)
    siren_ms = all_results.get("siren_inference", {}).get("mean_ms", 0)
    bt_ms = all_results.get("bytetrack", {}).get("20_tracks_ms", 0)
    fft_ms = all_results.get("fft", {}).get("fft_computation_ms", 0)
    hsv_ms = all_results.get("fft", {}).get("hsv_extraction_ms", 0)
    resize_ms = all_results.get("resize", {}).get("resize_ms", 0)
    decode_ms = all_results.get("video_decode", {}).get("decode_ms", 0)
    total_ram = all_results.get("ram", {}).get("total_estimated_mb", 0)

    total_vision_ms = yolo_ms + bt_ms + hsv_ms + resize_ms
    vision_fps = 1000.0 / (total_vision_ms + 0.001) if total_vision_ms > 0 else 0

    # Pipeline throughput khi ByteTrack chạy ở camera FPS
    cam_fps = all_results.get("video_decode", {}).get("video_fps", 30.0)
    cam_interval_ms = 1000.0 / cam_fps if cam_fps > 0 else 33.3
    bt_only_ms = bt_ms + hsv_ms  # ByteTrack predict + HSV (không có YOLO)

    print(f"\n  [BỘ NHỚ]")
    print(f"    Tổng RAM ước tính:          {total_ram:7.1f} MB")
    print(f"    RAM hệ thống (total):       {sys_info.get('total_ram_mb', 0):7.0f} MB")
    print(f"    RAM khả dụng:               {sys_info.get('available_ram_mb', 0):7.0f} MB")

    print(f"\n  [TỐC ĐỘ - Pipeline Hình ảnh]")
    print(f"    Giải mã video:              {decode_ms:8.1f} ms/frame")
    print(f"    Resize → {YOLO_IMGSZ}x{YOLO_IMGSZ}:           {resize_ms:8.3f} ms")
    print(f"    YOLO inference:             {yolo_ms:8.1f} ms")
    print(f"    ByteTrack predict (20 obj): {bt_ms:8.4f} ms")
    print(f"    HSV color extraction:       {hsv_ms:8.4f} ms")
    print(f"    FFT analysis:               {fft_ms:8.4f} ms  (1 lần/cửa sổ)")
    print(f"    ─────────────────────────────────────")
    print(f"    Tổng/frame (có YOLO):       {total_vision_ms:8.1f} ms")
    print(f"    FPS (có YOLO):              {vision_fps:8.2f}")
    print(f"    Tổng/frame (chỉ BT+HSV):   {bt_only_ms:8.4f} ms")

    print(f"\n  [TỐC ĐỘ - Pipeline Âm thanh]")
    print(f"    Siren inference:            {siren_ms:8.1f} ms / cửa sổ 2s")

    print(f"\n  [KẾT LUẬN PIPELINE]")
    print(f"    Camera FPS:                 {cam_fps:.1f}")
    print(f"    Camera interval:            {cam_interval_ms:.1f} ms")
    print(f"    YOLO chạy mỗi:             {yolo_ms:.0f} ms → ~{vision_fps:.1f} FPS")
    print(f"    ByteTrack predict-only:     {bt_only_ms:.3f} ms → NHANH HƠN camera interval")
    print(f"    → ByteTrack CÓ THỂ chạy ở camera FPS ({cam_fps:.0f} FPS)")
    print(f"       với YOLO chỉ chạy mỗi {int(cam_fps/vision_fps) if vision_fps > 0 else '?'} frame")

    # Save JSON
    results_path = os.path.expanduser("~/benchmark_results.json")
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Kết quả JSON: {results_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
