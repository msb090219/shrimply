import ctypes
from ctypes import wintypes
from unittest.mock import Mock
import sys

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from shrimply.ui import power


def test_windows_notifications_are_scoped_and_resume_is_not_duplicated(monkeypatch):
    application, api = Mock(), Mock()
    api.RegisterSuspendResumeNotification.return_value = 987
    monkeypatch.setattr(power.sys, "platform", "win32")
    monkeypatch.setattr(power.ctypes, "WinDLL", lambda *_args, **_kwargs: api, raising=False)
    monkeypatch.setattr(power.QApplication, "instance", lambda: application)
    suspend, resume = Mock(), Mock()
    monitor = power.PowerMonitor(123, suspend, resume)
    application.installNativeEventFilter.assert_called_once_with(monitor)
    for window, message, event in [(999, 0x218, 4), (123, 1, 4),
                                   (123, 0x218, 4), (123, 0x218, 0x12), (123, 0x218, 7)]:
        msg = wintypes.MSG()
        msg.hWnd, msg.message, msg.wParam = window, message, event
        assert monitor.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg)) == (False, 0)
    suspend.assert_called_once()
    resume.assert_called_once()
    monitor.close()
    monitor.close()
    application.removeNativeEventFilter.assert_called_once_with(monitor)
    api.UnregisterSuspendResumeNotification.assert_called_once_with(987)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows native message delivery")
def test_real_windows_registration_and_message_delivery():
    application = QApplication.instance() or QApplication([])
    if application.platformName() == "offscreen":
        pytest.skip("Offscreen Qt does not deliver native Windows messages")
    window = QWidget()
    suspend, resume = Mock(), Mock()
    monitor = power.PowerMonitor(window.winId(), suspend, resume)
    api = ctypes.WinDLL("user32", use_last_error=True)
    send = api.SendMessageW
    send.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    send.restype = ctypes.c_ssize_t
    try:
        send(int(window.winId()), 0x218, 4, 0)
        send(int(window.winId()), 0x218, 0x12, 0)
        application.processEvents()
        suspend.assert_called_once()
        resume.assert_called_once()
    finally:
        monitor.close()
        window.close()
