"""
output.py — Xuất tín hiệu khi phát hiện xe ưu tiên.
Hỗ trợ: GPIO (relay/đèn), MQTT, và logging.
"""

import time
import logging
import os

logger = logging.getLogger(__name__)


class OutputManager:
    """Quản lý tất cả output channels."""

    def __init__(self, gpio_enabled=False, gpio_pin=17,
                 mqtt_enabled=False, mqtt_broker="localhost",
                 mqtt_port=1883, mqtt_topic="emergency_vehicle/detected",
                 log_dir="logs", save_frames=False):

        self.gpio_enabled = gpio_enabled
        self.gpio_pin = gpio_pin
        self.mqtt_enabled = mqtt_enabled
        self.save_frames = save_frames
        self.log_dir = log_dir

        self._gpio = None
        self._mqtt_client = None
        self._gpio_state = False

        os.makedirs(log_dir, exist_ok=True)

        # Setup GPIO
        if gpio_enabled:
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(gpio_pin, GPIO.OUT, initial=GPIO.LOW)
                self._gpio = GPIO
                logger.info(f"GPIO initialized: pin {gpio_pin}")
            except Exception as e:
                logger.warning(f"GPIO init failed: {e}. Disabling GPIO.")
                self.gpio_enabled = False

        # Setup MQTT
        if mqtt_enabled:
            try:
                import paho.mqtt.client as mqtt
                self._mqtt_client = mqtt.Client()
                self._mqtt_client.connect(mqtt_broker, mqtt_port, 60)
                self._mqtt_client.loop_start()
                self._mqtt_topic = mqtt_topic
                logger.info(f"MQTT connected: {mqtt_broker}:{mqtt_port}")
            except Exception as e:
                logger.warning(f"MQTT init failed: {e}. Disabling MQTT.")
                self.mqtt_enabled = False

    def signal_emergency(self, vehicle_ids, fft_results=None):
        """
        Phát tín hiệu xe ưu tiên.
        
        Args:
            vehicle_ids: list of confirmed vehicle IDs
            fft_results: dict {id: FFTResult} (optional, for logging)
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"[{timestamp}] 🚨 XE ƯU TIÊN XÁC NHẬN! "
            f"IDs: {vehicle_ids}"
        )

        if fft_results:
            for vid in vehicle_ids:
                if vid in fft_results:
                    r = fft_results[vid]
                    msg += (
                        f"\n  ID {vid}: freq={r.peak_freq:.2f}Hz, "
                        f"PNR={r.peak_ratio:.1f}, "
                        f"red_max={r.red_max:.1f}, blue_max={r.blue_max:.1f}"
                    )

        logger.warning(msg)

        # GPIO
        if self.gpio_enabled and not self._gpio_state:
            self._gpio.output(self.gpio_pin, self._gpio.HIGH)
            self._gpio_state = True
            logger.info(f"GPIO pin {self.gpio_pin} → HIGH")

        # MQTT
        if self.mqtt_enabled and self._mqtt_client:
            import json
            payload = {
                "timestamp": timestamp,
                "vehicle_ids": vehicle_ids,
                "event": "emergency_vehicle_detected",
            }
            if fft_results:
                payload["details"] = {
                    str(vid): {
                        "peak_freq": fft_results[vid].peak_freq,
                        "peak_ratio": fft_results[vid].peak_ratio,
                    }
                    for vid in vehicle_ids if vid in fft_results
                }
            self._mqtt_client.publish(
                self._mqtt_topic,
                json.dumps(payload)
            )

    def signal_clear(self):
        """Tắt tín hiệu (không còn xe ưu tiên)."""
        if self.gpio_enabled and self._gpio_state:
            self._gpio.output(self.gpio_pin, self._gpio.LOW)
            self._gpio_state = False
            logger.info(f"GPIO pin {self.gpio_pin} → LOW")

        if self.mqtt_enabled and self._mqtt_client:
            import json
            self._mqtt_client.publish(
                self._mqtt_topic,
                json.dumps({"event": "clear", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
            )

    def save_frame(self, frame, vehicle_ids, active_tracks=None):
        """Lưu frame khi phát hiện xe ưu tiên (nếu bật)."""
        if not self.save_frames or frame is None:
            return
        try:
            import cv2
            
            # Vẽ bounding box lên bản sao của frame
            annotated_frame = frame.copy()
            if active_tracks:
                for track in active_tracks:
                    if track.id in vehicle_ids:
                        x1, y1, x2, y2 = map(int, track.bbox)
                        # Vẽ hình chữ nhật màu đỏ (hoặc cam)
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        # Vẽ label nền đỏ chữ trắng
                        label = f"🚨 XE UU TIEN ID: {track.id}"
                        # Lấy kích thước text
                        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                        # Vẽ background cho text
                        cv2.rectangle(annotated_frame, (x1, y1 - 25), (x1 + w, y1), (0, 0, 255), -1)
                        cv2.putText(annotated_frame, label, (x1, y1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            ts = time.strftime("%Y%m%d_%H%M%S")
            fname = os.path.join(self.log_dir, f"emergency_{ts}_ids{'_'.join(map(str, vehicle_ids))}.jpg")
            cv2.imwrite(fname, annotated_frame)
            logger.info(f"Saved annotated frame: {fname}")
        except Exception as e:
            logger.error(f"Save frame failed: {e}")

    def cleanup(self):
        """Giải phóng tài nguyên."""
        self.signal_clear()
        if self._gpio:
            try:
                self._gpio.cleanup()
            except Exception:
                pass
        if self._mqtt_client:
            try:
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
            except Exception:
                pass
        logger.info("OutputManager cleaned up.")
