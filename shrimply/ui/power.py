"""Platform sleep/wake notifications feeding the shared camera policy."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys

from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtWidgets import QApplication


class PowerMonitor(QAbstractNativeEventFilter):
    def __init__(self, window_id, suspend, resume):
        super().__init__()
        self._window_id = int(window_id)
        self._suspend, self._resume = suspend, resume
        self._registration = None
        self._mac = None
        if sys.platform == "darwin":
            from .macos_power import MacPowerMonitor

            self._mac = MacPowerMonitor(suspend, resume)
        if sys.platform == "win32":
            self._user32 = ctypes.WinDLL("user32", use_last_error=True)
            register = self._user32.RegisterSuspendResumeNotification
            register.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            register.restype = wintypes.HANDLE
            self._registration = register(self._window_id, 0)  # DEVICE_NOTIFY_WINDOW_HANDLE
            if not self._registration:
                raise ctypes.WinError(ctypes.get_last_error())
            QApplication.instance().installNativeEventFilter(self)

    def nativeEventFilter(self, event_type, message):
        if event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.hWnd == self._window_id and msg.message == 0x218:  # WM_POWERBROADCAST
                if msg.wParam == 0x4:  # PBT_APMSUSPEND
                    self._suspend()
                elif msg.wParam in (0x12, 0x6):  # automatic resume or critical resume
                    self._resume()
                # Ignore RESUMESUSPEND: it follows RESUMEAUTOMATIC on user wake.
        return False, 0

    def close(self):
        if self._mac is not None:
            self._mac.close()
            self._mac = None
        if self._registration:
            QApplication.instance().removeNativeEventFilter(self)
            unregister = self._user32.UnregisterSuspendResumeNotification
            unregister.argtypes = [wintypes.HANDLE]
            unregister.restype = wintypes.BOOL
            unregister(self._registration)
            self._registration = None
