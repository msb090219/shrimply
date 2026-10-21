import sys
import subprocess
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS native notifications")


def test_native_workspace_notifications_hold_camera_until_all_reasons_clear():
    # Cocoa owns process-global application state; isolate it from tests that
    # repeatedly create and destroy Qt applications using the offscreen plugin.
    result = subprocess.run(
        [sys.executable, "-c", "import runpy, sys; runpy.run_path(sys.argv[1], run_name='__main__')", __file__],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _check_native_notifications():
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    from AppKit import NSWorkspace
    from Foundation import NSNotification
    from shrimply.ui.macos_power import MacPowerMonitor
    suspend, resume = Mock(), Mock()
    monitor = MacPowerMonitor(suspend, resume)
    center = NSWorkspace.sharedWorkspace().notificationCenter()

    def workspace(name):
        center.postNotificationName_object_(name, None)
        application.processEvents()

    def lock(name):
        monitor._observer.powerChanged_(NSNotification.notificationWithName_object_(name, None))
        application.processEvents()

    try:
        workspace("NSWorkspaceWillSleepNotification")
        workspace("NSWorkspaceWillSleepNotification")
        workspace("NSWorkspaceScreensDidSleepNotification")
        lock("com.apple.screenIsLocked")
        suspend.assert_called_once()
        workspace("NSWorkspaceDidWakeNotification")
        workspace("NSWorkspaceScreensDidWakeNotification")
        resume.assert_not_called()
        lock("com.apple.screenIsUnlocked")
        resume.assert_called_once()
        workspace("NSWorkspaceDidWakeNotification")
        resume.assert_called_once()
        workspace("NSWorkspaceSessionDidResignActiveNotification")
        assert suspend.call_count == 2
        workspace("NSWorkspaceSessionDidBecomeActiveNotification")
        assert resume.call_count == 2
    finally:
        monitor.close()
    monitor.close()
    workspace("NSWorkspaceWillSleepNotification")
    assert suspend.call_count == 2
    # Ignore a notification that was queued before cleanup.
    monitor.notification.emit("com.apple.screenIsLocked")
    assert suspend.call_count == 2


if __name__ == "__main__":
    _check_native_notifications()
