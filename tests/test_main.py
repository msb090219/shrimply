"""Startup locking must precede shared data, logging, and camera startup."""
import os
import subprocess
import sys
from unittest.mock import Mock

from PySide6.QtCore import QLockFile
import pytest

import main as entry


@pytest.fixture
def startup(tmp_path, monkeypatch):
    monkeypatch.setattr(entry.sys, "argv", ["unshrimp"])
    monkeypatch.setattr(entry.config_mod, "APP_DIR", tmp_path)
    monkeypatch.setattr(entry, "QApplication", Mock())
    monkeypatch.setattr(entry, "QMessageBox", Mock())
    monkeypatch.setattr(entry.config_mod, "migrate_legacy", Mock())
    monkeypatch.setattr(entry.diag, "start", Mock())
    monkeypatch.setattr(entry, "UnshrimpApp", Mock())
    monkeypatch.setattr(entry, "_activate_existing", Mock(return_value=False))
    return tmp_path


def test_second_launch_exits_before_shared_data_or_camera(startup):
    owner = QLockFile(str(startup / "instance.lock"))
    owner.setStaleLockTime(0)
    assert owner.tryLock(0)
    try:
        original = (startup / "instance.lock").read_bytes()
        assert entry.main() == 0
        entry.QMessageBox.information.assert_called_once()
        entry.config_mod.migrate_legacy.assert_not_called()
        entry.diag.start.assert_not_called()
        entry.UnshrimpApp.assert_not_called()
        assert (startup / "instance.lock").read_bytes() == original
    finally:
        owner.unlock()


def test_lock_error_is_not_reported_as_running(startup, monkeypatch):
    lock = Mock()
    lock.tryLock.return_value = False
    lock.error.return_value = QLockFile.PermissionError
    factory = Mock(return_value=lock)
    factory.LockFailedError = QLockFile.LockFailedError
    monkeypatch.setattr(entry, "QLockFile", factory)
    assert entry.main() == 1
    entry.QMessageBox.critical.assert_called_once()
    entry.QMessageBox.information.assert_not_called()
    entry.UnshrimpApp.assert_not_called()


@pytest.mark.parametrize("background", [False, True])
def test_duplicate_launch_activation_policy(startup, monkeypatch, background):
    owner = QLockFile(str(startup / "instance.lock"))
    assert owner.tryLock(0)
    monkeypatch.setattr(entry.sys, "argv", ["unshrimp"] + (["--background"] if background else []))
    entry._activate_existing.return_value = True
    try:
        assert entry.main() == 0
        assert entry._activate_existing.call_count == (0 if background else 1)
        entry.QMessageBox.information.assert_not_called()
        entry.UnshrimpApp.assert_not_called()
    finally:
        owner.unlock()


def test_local_activation_opens_existing_controller(tmp_path, monkeypatch):
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(entry.config_mod, "APP_DIR", tmp_path)
    controller = QObject()
    controller._open_main_window = Mock()
    server = entry._activation_server(controller)
    try:
        assert server.isListening()
        assert entry._activate_existing()
        for _ in range(10):
            app.processEvents()
        controller._open_main_window.assert_called_once()
    finally:
        server.close()


@pytest.mark.parametrize("background", [False, True])
@pytest.mark.parametrize("login_enabled", [False, True])
def test_launch_forwards_mode_and_refreshes_only_enabled_login(startup, monkeypatch, background, login_enabled):
    from unshrimp import autostart
    from unshrimp.ui import power

    monkeypatch.setattr(entry.sys, "argv", ["unshrimp"] + (["--background"] if background else []))
    monkeypatch.setattr(autostart, "is_enabled", Mock(return_value=login_enabled))
    monkeypatch.setattr(autostart, "set_enabled", Mock())
    monkeypatch.setattr(power, "PowerMonitor", Mock())
    monkeypatch.setattr(entry, "_activation_server", Mock())
    entry.QApplication.return_value.exec.return_value = 0
    assert entry.main() == 0
    entry.UnshrimpApp.return_value.start.assert_called_once_with(background=background)
    assert autostart.set_enabled.call_count == int(login_enabled)
    if login_enabled:
        autostart.set_enabled.assert_called_once_with(True)
    entry.UnshrimpApp.return_value.shutdown.assert_called_once()


def test_process_lock_survives_old_timestamp_and_recovers_after_owner_exit(startup):
    path = startup / "instance.lock"
    # Child holds the same lock protocol used by source and packaged startup.
    program = "from PySide6.QtCore import QLockFile; import sys; lock=QLockFile(sys.argv[1]); lock.setStaleLockTime(0); assert lock.tryLock(0); print('ready', flush=True); sys.stdin.readline()"
    child = subprocess.Popen([sys.executable, "-c", program, str(path)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "ready"
        os.utime(path, (1, 1))
        assert entry.main() == 0
        entry.UnshrimpApp.assert_not_called()
        child.kill()  # only this disposable test child; simulate an unclean exit
        child.wait(timeout=10)
        recovered = QLockFile(str(path))
        recovered.setStaleLockTime(0)
        assert recovered.tryLock(0)
        recovered.unlock()
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)
