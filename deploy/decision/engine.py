"""
engine.py — State machine + Decision Engine.
Quản lý trạng thái hệ thống: LISTENING → ALERT → CONFIRMED.
Kết hợp 3 nguồn tin: còi (audio), phương tiện (YOLO+BT), đèn nhấp nháy (FFT).
"""

import time
import enum
import logging

logger = logging.getLogger(__name__)


class SystemState(enum.Enum):
    LISTENING = "LISTENING"   # Chỉ microphone ON, camera OFF
    ALERT = "ALERT"           # Phát hiện còi → camera ON, YOLO+BT+FFT ON
    CONFIRMED = "CONFIRMED"   # Xác nhận xe ưu tiên (còi + xe + đèn)


class DecisionEngine:
    """
    Máy trạng thái và logic quyết định kết hợp.
    
    State transitions:
        LISTENING → ALERT:     khi siren_active = True
        ALERT → CONFIRMED:     khi siren + vehicle + strobe = True
        ALERT → LISTENING:     khi hết timeout (30s không còn còi)
        CONFIRMED → ALERT:     khi mất tín hiệu FFT nhưng vẫn có còi
        CONFIRMED → LISTENING: khi hết timeout
    """

    def __init__(self, alert_timeout_sec=30.0):
        self.alert_timeout = alert_timeout_sec
        self._state = SystemState.LISTENING
        self._last_siren_time = 0.0
        self._alert_start_time = 0.0
        self._confirmed_ids = []

    @property
    def state(self):
        return self._state

    @property
    def confirmed_ids(self):
        return list(self._confirmed_ids)

    def update(self, siren_active, fft_results, active_tracks):
        """
        Cập nhật trạng thái hệ thống.
        
        Args:
            siren_active: bool — còi ưu tiên đang hoạt động
            fft_results: dict {vehicle_id: FFTResult}
            active_tracks: list of Track — tracks đang active
            
        Returns:
            (state, confirmed_vehicle_ids, state_changed)
        """
        now = time.monotonic()
        old_state = self._state

        if siren_active:
            self._last_siren_time = now

        # Tìm vehicles có đèn nhấp nháy
        strobe_ids = [
            tid for tid, r in fft_results.items()
            if r.is_strobe
        ]

        # Vehicles đang hiện diện
        vehicle_present = len(active_tracks) > 0

        # === State transitions ===

        if self._state == SystemState.LISTENING:
            if siren_active:
                self._state = SystemState.ALERT
                self._alert_start_time = now
                self._confirmed_ids = []
                logger.info("STATE: LISTENING → ALERT (siren detected)")

        elif self._state == SystemState.ALERT:
            # Check timeout
            time_since_siren = now - self._last_siren_time
            if time_since_siren > self.alert_timeout:
                self._state = SystemState.LISTENING
                self._confirmed_ids = []
                logger.info(
                    f"STATE: ALERT → LISTENING "
                    f"(timeout {time_since_siren:.0f}s > {self.alert_timeout:.0f}s)"
                )
            elif siren_active and vehicle_present and len(strobe_ids) > 0:
                self._state = SystemState.CONFIRMED
                self._confirmed_ids = strobe_ids
                logger.warning(
                    f"STATE: ALERT → CONFIRMED! "
                    f"Xe ưu tiên IDs: {strobe_ids}"
                )

        elif self._state == SystemState.CONFIRMED:
            # Check timeout
            time_since_siren = now - self._last_siren_time
            if time_since_siren > self.alert_timeout:
                self._state = SystemState.LISTENING
                self._confirmed_ids = []
                logger.info("STATE: CONFIRMED → LISTENING (timeout)")
            elif not siren_active and len(strobe_ids) == 0:
                # Mất cả còi và đèn → về ALERT chờ thêm
                self._state = SystemState.ALERT
                self._confirmed_ids = []
                logger.info("STATE: CONFIRMED → ALERT (lost signals)")
            else:
                # Cập nhật confirmed IDs
                self._confirmed_ids = strobe_ids

        state_changed = (self._state != old_state)
        return self._state, list(self._confirmed_ids), state_changed

    def should_activate_camera(self):
        """Camera có nên bật không."""
        return self._state in (SystemState.ALERT, SystemState.CONFIRMED)

    def is_confirmed(self):
        """Có đang xác nhận xe ưu tiên không."""
        return self._state == SystemState.CONFIRMED

    def get_status_str(self):
        """String mô tả trạng thái hiện tại."""
        elapsed = time.monotonic() - self._last_siren_time if self._last_siren_time > 0 else 0
        return (
            f"State={self._state.value} | "
            f"Confirmed={self._confirmed_ids} | "
            f"Since_siren={elapsed:.1f}s"
        )

    def reset(self):
        """Reset về LISTENING."""
        self._state = SystemState.LISTENING
        self._confirmed_ids = []
        self._last_siren_time = 0.0
