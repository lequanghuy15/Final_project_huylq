#!/usr/bin/env python3
"""
main.py — Entry point cho hệ thống nhận diện xe ưu tiên 24/7.

Kiến trúc 3 threads:
    Thread 1 (Audio):   Microphone → Siren GRU → Voting (always ON)
    Thread 2 (Vision):  Camera → YOLO → ByteTrack → HSV → FFT (ON khi có còi)
    Thread 3 (Main):    Decision Engine → Output (GPIO/MQTT/Log)

Usage:
    python3 main.py
    python3 main.py --camera 0                # Webcam
    python3 main.py --camera rtsp://...       # IP Camera
    python3 main.py --video ~/test.mkv        # Video file (debug)
    python3 main.py --no-audio                # Bỏ qua audio (debug vision)
"""

import argparse
import threading
import time
import gc
import logging
import logging.handlers
import os
import sys
import signal

# Add deploy dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from audio.mic_stream import MicStream
from audio.siren_detector import SirenDetector
from vision.camera import Camera
from vision.yolo_detector import YOLODetector
from vision.byte_tracker import ByteTracker
from vision.color_analyzer import ColorAnalyzer
from decision.engine import DecisionEngine, SystemState
from decision.output import OutputManager

# ============================================================
# LOGGING
# ============================================================
def setup_logging():
    os.makedirs(config.LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] %(name)-20s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    # File handler with rotation
    fh = logging.handlers.RotatingFileHandler(
        os.path.join(config.LOG_DIR, "system.log"),
        maxBytes=config.LOG_MAX_SIZE_MB * 1024 * 1024,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(ch)
    root.addHandler(fh)


logger = logging.getLogger("main")


# ============================================================
# GLOBAL STOP EVENT
# ============================================================
stop_event = threading.Event()


def signal_handler(sig, frame):
    logger.info(f"Signal {sig} received. Shutting down...")
    stop_event.set()


# ============================================================
# THREAD 1: AUDIO MONITOR
# ============================================================
def audio_thread(mic, siren_detector, shared_state):
    """
    Thu âm liên tục, chạy siren detection mỗi stride (170ms).
    Cập nhật shared_state['siren_active'] và shared_state['siren_prob'].
    """
    logger.info("Audio thread started.")
    stride_sec = config.AUDIO_STRIDE_SEC

    while not stop_event.is_set():
        t0 = time.monotonic()

        # Lấy cửa sổ audio 2 giây
        audio = mic.get_window(duration_sec=config.AUDIO_CLIP_SEC)

        if audio is not None:
            try:
                prob, active = siren_detector.process_window(audio)
                shared_state['siren_active'] = active
                shared_state['siren_prob'] = prob

                if active and not shared_state.get('_was_active', False):
                    logger.info(f"🔊 SIREN DETECTED! prob={prob:.3f}")
                elif not active and shared_state.get('_was_active', False):
                    logger.info(f"🔇 Siren stopped. prob={prob:.3f}")

                shared_state['_was_active'] = active

            except Exception as e:
                logger.error(f"Siren detection error: {e}")

        # Sleep đến stride tiếp theo
        elapsed = time.monotonic() - t0
        sleep_time = stride_sec - elapsed
        if sleep_time > 0:
            stop_event.wait(sleep_time)

    logger.info("Audio thread stopped.")


# ============================================================
# THREAD 2: VISION PIPELINE
# ============================================================
def vision_thread(camera, yolo, tracker, color_analyzer, shared_state):
    """
    Chạy YOLO + ByteTrack + HSV + FFT.
    Chỉ active khi shared_state['camera_active'] = True.
    """
    logger.info("Vision thread started.")
    frame_count = 0
    yolo_interval = config.YOLO_INTERVAL
    last_frame_id = 0

    while not stop_event.is_set():
        # Chờ camera được kích hoạt
        if not shared_state.get('camera_active', False):
            # Camera OFF → reset tracker, sleep
            if camera.is_running:
                camera.stop()
                tracker.reset()
                color_analyzer.reset()
                gc.collect()
                logger.info("Camera stopped (no siren).")
            stop_event.wait(0.5)
            continue

        # Camera ON
        if not camera.is_running:
            try:
                camera.start()
                frame_count = 0
                logger.info("Camera started (siren detected).")
            except Exception as e:
                logger.error(f"Camera start failed: {e}")
                stop_event.wait(2.0)
                continue

        # Lấy frame
        frame, frame_id = camera.get_frame()
        if frame is None or frame_id == last_frame_id:
            time.sleep(0.005)  # 5ms wait
            continue

        last_frame_id = frame_id
        frame_count += 1

        try:
            # YOLO detection (mỗi yolo_interval frames)
            if frame_count % yolo_interval == 1:
                detections = yolo.detect(frame)
                tracks = tracker.update(detections)
            else:
                # Chỉ predict (Kalman only)
                tracks = tracker.predict_only()

            # HSV color extraction + FFT cho tất cả tracks
            color_analyzer.process_tracks(frame, tracks)

            # Cập nhật shared state
            shared_state['fft_results'] = color_analyzer.get_results()
            shared_state['active_tracks'] = tracks
            shared_state['strobe_ids'] = color_analyzer.get_strobe_vehicles()
            shared_state['last_frame'] = frame
            shared_state['vision_frame_count'] = frame_count

        except Exception as e:
            logger.error(f"Vision pipeline error: {e}", exc_info=True)

    # Cleanup
    if camera.is_running:
        camera.stop()
    logger.info("Vision thread stopped.")


# ============================================================
# THERMAL MONITORING
# ============================================================
def get_cpu_temp():
    """Đọc nhiệt độ CPU (Linux/Pi only)."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip()) / 1000.0
    except Exception:
        return 0.0


# ============================================================
# MAIN LOOP (Thread 3: Decision Engine)
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Emergency Vehicle Detection System")
    parser.add_argument("--camera", default=None, help="Camera source (index or RTSP URL)")
    parser.add_argument("--video", default=None, help="Video file for testing")
    parser.add_argument("--no-audio", action="store_true", help="Disable audio (debug mode)")
    parser.add_argument("--force-alert", action="store_true",
                        help="Force ALERT state (skip siren detection)")
    args = parser.parse_args()

    setup_logging()
    logger.info("=" * 60)
    logger.info("  HỆ THỐNG NHẬN DIỆN XE ƯU TIÊN")
    logger.info("  Starting 24/7 operation...")
    logger.info("=" * 60)

    # Signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Camera source
    cam_source = config.CAMERA_SOURCE
    if args.video:
        cam_source = args.video
    elif args.camera:
        cam_source = int(args.camera) if args.camera.isdigit() else args.camera

    # ============================
    # KHỞI TẠO CÁC MODULE
    # ============================

    # Shared state between threads (protected by GIL for simple types)
    shared_state = {
        'siren_active': False,
        'siren_prob': 0.0,
        'camera_active': False,
        'fft_results': {},
        'active_tracks': [],
        'strobe_ids': [],
        'last_frame': None,
        'vision_frame_count': 0,
    }

    # Audio
    mic = None
    siren = None
    audio_t = None

    if not args.no_audio:
        try:
            mic = MicStream(
                sr=config.AUDIO_SR,
                channels=config.AUDIO_CHANNELS,
                chunk_sec=config.AUDIO_STRIDE_SEC,
                device_index=config.AUDIO_DEVICE_INDEX
            )
            siren = SirenDetector(
                model_path=config.SIREN_MODEL,
                sr=config.AUDIO_SR,
                lo_freq=config.AUDIO_LO_FREQ,
                hi_freq=config.AUDIO_HI_FREQ,
                pre_emph=config.AUDIO_PRE_EMPH,
                n_fft=config.AUDIO_N_FFT,
                hop_len=config.AUDIO_HOP_LEN,
                n_mels=config.AUDIO_N_MELS,
                n_mfcc=config.AUDIO_N_MFCC,
                fmin=config.AUDIO_FMIN,
                fmax=config.AUDIO_FMAX,
                clip_sec=config.AUDIO_CLIP_SEC,
                threshold=config.SIREN_THRESHOLD,
                voting_window=config.SIREN_VOTING_WINDOW,
                voting_min=config.SIREN_VOTING_MIN,
            )
            mic.start()
            logger.info("Audio pipeline initialized.")
        except Exception as e:
            logger.error(f"Audio init failed: {e}. Running without audio.")
            args.no_audio = True
    else:
        logger.warning("Audio disabled (--no-audio). Using force-alert mode.")
        args.force_alert = True

    # Vision
    camera = Camera(
        source=cam_source,
        fps=config.CAMERA_FPS,
        width=config.CAMERA_WIDTH,
        height=config.CAMERA_HEIGHT,
    )

    yolo = YOLODetector(
        model_path=config.YOLO_MODEL,
        imgsz=config.YOLO_IMGSZ,
        conf_thresh=config.YOLO_CONF_THRESH,
        iou_thresh=config.YOLO_IOU_THRESH,
    )

    tracker = ByteTracker(
        track_thresh=config.BT_TRACK_THRESH,
        track_low=config.BT_TRACK_LOW,
        match_thresh=config.BT_MATCH_THRESH,
        max_time_lost=config.BT_MAX_TIME_LOST,
    )

    color_analyzer = ColorAnalyzer(
        fps=config.CAMERA_FPS,
        red1_low=config.HSV_RED1_LOW,
        red1_high=config.HSV_RED1_HIGH,
        red2_low=config.HSV_RED2_LOW,
        red2_high=config.HSV_RED2_HIGH,
        blue_low=config.HSV_BLUE_LOW,
        blue_high=config.HSV_BLUE_HIGH,
        min_frames=config.FFT_MIN_FRAMES,
        freq_min=config.FFT_FREQ_MIN,
        freq_max=config.FFT_FREQ_MAX,
        peak_ratio_thresh=config.FFT_PEAK_RATIO_THRESH,
        color_energy_thresh=config.COLOR_ENERGY_THRESH,
        window_sec=config.FFT_WINDOW_SEC,
    )

    # Decision Engine
    engine = DecisionEngine(alert_timeout_sec=config.ALERT_TIMEOUT_SEC)

    # Output
    output = OutputManager(
        gpio_enabled=config.GPIO_ENABLED,
        gpio_pin=config.GPIO_PIN,
        mqtt_enabled=config.MQTT_ENABLED,
        mqtt_broker=config.MQTT_BROKER,
        mqtt_port=config.MQTT_PORT,
        mqtt_topic=config.MQTT_TOPIC,
        log_dir=config.LOG_DIR,
        save_frames=config.LOG_SAVE_FRAMES,
    )

    logger.info("All modules initialized.")

    # ============================
    # KHỞI CHẠY THREADS
    # ============================

    # Thread 1: Audio
    if not args.no_audio:
        audio_t = threading.Thread(
            target=audio_thread,
            args=(mic, siren, shared_state),
            daemon=True,
            name="AudioThread"
        )
        audio_t.start()

    # Thread 2: Vision
    vision_t = threading.Thread(
        target=vision_thread,
        args=(camera, yolo, tracker, color_analyzer, shared_state),
        daemon=True,
        name="VisionThread"
    )
    vision_t.start()

    # ============================
    # MAIN LOOP (Thread 3: Decision)
    # ============================
    logger.info("Entering main decision loop.")
    status_interval = 10.0  # In trạng thái mỗi 10 giây
    last_status_time = time.monotonic()

    try:
        while not stop_event.is_set():
            t0 = time.monotonic()

            siren_active = shared_state['siren_active']
            if args.force_alert:
                siren_active = True
                shared_state['siren_active'] = True

            # Cập nhật camera active flag
            # → Vision thread sẽ đọc flag này
            fft_results = shared_state.get('fft_results', {})
            active_tracks = shared_state.get('active_tracks', [])

            # Decision update
            state, confirmed_ids, state_changed = engine.update(
                siren_active=siren_active,
                fft_results=fft_results,
                active_tracks=active_tracks,
            )

            # Cập nhật camera flag
            shared_state['camera_active'] = engine.should_activate_camera()

            # Output
            if state == SystemState.CONFIRMED and confirmed_ids:
                output.signal_emergency(confirmed_ids, fft_results)
                frame = shared_state.get('last_frame')
                output.save_frame(frame, confirmed_ids, active_tracks)
            elif state == SystemState.LISTENING:
                output.signal_clear()

            # Status log
            if t0 - last_status_time >= status_interval:
                temp = get_cpu_temp()
                vfc = shared_state.get('vision_frame_count', 0)
                prob = shared_state.get('siren_prob', 0)
                strobe_ids = shared_state.get('strobe_ids', [])
                logger.info(
                    f"STATUS: {engine.get_status_str()} | "
                    f"Prob={prob:.2f} | Strobes={strobe_ids} | "
                    f"V_frames={vfc} | Temp={temp:.1f}°C"
                )
                last_status_time = t0

                # Thermal check
                if temp > config.THERMAL_THROTTLE_TEMP:
                    logger.warning(
                        f"⚠️ CPU temp {temp:.1f}°C > {config.THERMAL_THROTTLE_TEMP}°C! "
                        f"Consider reducing workload."
                    )

            # Decision interval
            elapsed = time.monotonic() - t0
            sleep_time = config.DECISION_INTERVAL_SEC - elapsed
            if sleep_time > 0:
                stop_event.wait(sleep_time)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt.")
    finally:
        # ============================
        # CLEANUP
        # ============================
        logger.info("Shutting down...")
        stop_event.set()

        if mic:
            mic.stop()
        if camera.is_running:
            camera.stop()
        output.cleanup()

        # Wait for threads
        if audio_t and audio_t.is_alive():
            audio_t.join(timeout=3.0)
        if vision_t.is_alive():
            vision_t.join(timeout=3.0)

        gc.collect()
        logger.info("System shutdown complete.")


if __name__ == "__main__":
    main()
