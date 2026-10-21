"""System-idle awareness — battery manners for the camera.

A locked or abandoned machine shouldn't keep pinging the webcam forever.
`seconds_idle()` reads global input activity through Windows or macOS native
APIs via ctypes; `should_idle_stop` is the pure policy the app polls:

    stop the camera after IDLE_STOP_S of no keyboard/mouse input anywhere
    in the system — unless the user manually paused (their call wins) or
    a calibration is in flight (never interrupt the guided flow).

On any input returning, the app restarts the camera automatically.
"""
from __future__ import annotations

import ctypes
import sys

IDLE_STOP_S = 300.0  # 5 minutes

# LASTINPUTINFO: cbSize, dwTime (tick count of last input)
_info = None  # cached ctypes struct
_mac_idle = None


def seconds_idle() -> float:
    """Seconds since the last keyboard/mouse input system-wide. 0.0 when
    unavailable — callers then never idle-stop."""
    if sys.platform == "darwin":
        global _mac_idle
        try:
            if _mac_idle is None:
                library = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
                _mac_idle = library.CGEventSourceSecondsSinceLastEventType
                _mac_idle.argtypes = [ctypes.c_int32, ctypes.c_uint32]
                _mac_idle.restype = ctypes.c_double
            # Combined session state; any keyboard, mouse, or tablet event.
            return max(0.0, _mac_idle(0, 0xFFFFFFFF))
        except (OSError, AttributeError):
            return 0.0
    if sys.platform != "win32":
        return 0.0
    global _info
    if _info is None:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        _info = LASTINPUTINFO()
        _info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(_info)):
        return 0.0
    tick_now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
    elapsed_ms = (tick_now - _info.dwTime) & 0xFFFFFFFF  # handles wraparound
    return elapsed_ms / 1000.0


def should_idle_stop(idle_s: float, calibrating: bool, manually_paused: bool) -> bool:
    """Pure policy — unit-tested."""
    if calibrating or manually_paused:
        return False  # never fight the user, never interrupt calibration
    return idle_s >= IDLE_STOP_S
