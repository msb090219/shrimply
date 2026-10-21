"""Exercise production close policies through real Cocoa keyboard events."""
import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="native Mac window shortcuts")
def test_native_mac_windows_preferences_activation_and_history():
    result = subprocess.run(
        [sys.executable, "-c", "import runpy, sys; runpy.run_path(sys.argv[1], run_name='__main__')", __file__],
        env=dict(os.environ, QT_QPA_PLATFORM="cocoa"),
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def check_windows():
    from unittest.mock import Mock
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.welcome import WelcomeDialog
    from shrimply.ui.preview import PreviewWindow, CameraPreviewWindow
    from shrimply.ui import theme

    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)

    def close(window):
        theme.apply_desktop_theme(window)  # reapplying must not duplicate shortcuts
        shortcuts = [s for s in window.findChildren(QShortcut)
                     if s.key() == QKeySequence(QKeySequence.Close)]
        assert len(shortcuts) == 1
        window.show()
        window.raise_()
        window.activateWindow()
        app.processEvents()
        QTest.qWait(50)
        QTest.keySequence(window, QKeySequence(QKeySequence.Close))
        app.processEvents()

    about = WelcomeDialog(about_mode=True)
    close(about)
    assert not about.isVisible()

    controller = Mock()
    controller.cfg = {"camera_index": 0}
    controller._quitting = True  # off-camera status; no capture owner in this check
    controller.worker.isRunning.return_value = False
    camera_preview = CameraPreviewWindow(controller)
    close(camera_preview)
    assert not camera_preview.isVisible() and not camera_preview.timer.isActive()
    assert controller._preview_changed.call_count == 2

    calibration = PreviewWindow()
    cancel = Mock()
    calibration.cancel_requested.connect(cancel)
    close(calibration)
    cancel.assert_called_once()
    calibration.show_result(True, "Saved")
    close(calibration)
    cancel.assert_called_once()
    assert not calibration.isVisible()

    for window in (about, camera_preview, calibration):
        window.hide()
        window.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    check_preferences_and_history(app)
    check_rebrand_upgrade(app)


def check_rebrand_upgrade(app):
    import copy
    import tempfile
    import time
    from pathlib import Path
    from unittest.mock import patch
    from PySide6.QtCore import QTimer, QEvent
    from PySide6.QtWidgets import QPushButton
    import config
    from shrimply.core.baseline import Baseline, SignalCal
    from shrimply.storage.db import PostureLog
    from shrimply.ui.app import ShrimplyApp
    from shrimply.ui.welcome import WelcomeDialog

    with tempfile.TemporaryDirectory(prefix="shrimply-rebrand-") as folder:
        root = Path(folder)
        old, new = root / "Unshrimp", root / "Shrimply"
        old.mkdir()
        saved = copy.deepcopy(config.DEFAULTS)
        saved.update(welcome_seen=True, tracking_paused=True, mascot_style="text",
                     baseline=Baseline({"head_pitch": SignalCal(5., 8., 1)},
                                       created_at=time.time()).to_dict())
        saved["hud"]["visible"] = False
        with patch.object(config, "APP_DIR", old), patch.object(config, "CONFIG_PATH", old / "config.json"):
            config.save(saved)
        history = PostureLog(old / "log.db")
        history.record_duration(int(time.time() // 60) * 60, 25., 10., 5.)
        history.close()
        originals = {name: (old / name).read_bytes() for name in ("config.json", "log.db")}
        with (patch.object(config, "APP_DIR", new),
              patch.object(config, "CONFIG_PATH", new / "config.json"),
              patch.object(config, "LEGACY_APP_DIR", old),
              patch.object(config, "_data_dir", lambda name: root / name)):
            config.migrate_legacy()
            controller = ShrimplyApp(Path.cwd() / "models")
            try:
                controller.start(background=True)
                app.processEvents()
                assert controller.baseline is not None
                assert controller.cfg["mascot_style"] == "text"
                assert controller.log.today()["seconds"] == 40.
                assert controller.main_window.windowTitle() == "Shrimply"
                assert not controller.worker.isRunning()
                controller._show_about()
                assert controller._about_dlg.windowTitle() == "About"
            finally:
                assert controller.shutdown()
                controller.main_window.hide()
                controller.main_window.deleteLater()
                app.sendPostedEvents(None, QEvent.DeferredDelete)
                controller.tray.icon.hide()
            assert all((old / name).read_bytes() == data for name, data in originals.items())

            # A genuinely fresh profile must allow Later without starting capture.
            fresh = root / "Fresh Shrimply"
            with patch.object(config, "APP_DIR", fresh), patch.object(config, "CONFIG_PATH", fresh / "config.json"):
                controller = ShrimplyApp(Path.cwd() / "models")
                def defer_setup():
                    dialog = next(w for w in app.topLevelWidgets()
                                  if isinstance(w, WelcomeDialog) and w.isVisible())
                    next(b for b in dialog.findChildren(QPushButton) if b.text() == "Later").click()
                QTimer.singleShot(0, defer_setup)
                try:
                    controller.start()
                    app.processEvents()
                    assert controller.cfg["tracking_paused"] and controller.cfg["welcome_seen"]
                    assert not controller.worker.isRunning()
                    assert controller.main_window.windowTitle() == "Shrimply"
                finally:
                    assert controller.shutdown()
                    controller.main_window.hide()
                    controller.main_window.deleteLater()
                    app.sendPostedEvents(None, QEvent.DeferredDelete)
                    controller.tray.icon.hide()


def check_preferences_and_history(app):
    import copy
    import tempfile
    import time
    from pathlib import Path
    from unittest.mock import patch
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeySequence
    from PySide6.QtTest import QTest
    import config
    import main as entry
    from shrimply import autostart
    from shrimply.core.states import State
    from shrimply.storage.db import PostureLog
    from shrimply.ui.app import ShrimplyApp
    from shrimply.ui import theme

    with tempfile.TemporaryDirectory(prefix="shrimply-mac-parity-") as folder:
        root = Path(folder)
        with (patch.object(config, "APP_DIR", root),
              patch.object(config, "CONFIG_PATH", root / "config.json"),
              patch.object(autostart, "_mac_path", lambda: root / "login.plist")):
            cfg = copy.deepcopy(config.DEFAULTS)
            cfg.update(tracking_paused=True, welcome_seen=True)
            cfg["hud"]["visible"] = False
            config.save(cfg)
            controller = ShrimplyApp(Path.cwd() / "models")
            server = None
            try:
                controller.start(background=True)
                app.processEvents()
                assert controller.machine.state is State.PAUSED
                assert not controller.worker.isRunning()
                assert not controller.main_window.isVisible()
                server = entry._activation_server(controller)
                assert entry._activate_existing()
                QTest.qWait(100)  # allow the native socket notification to reach Qt
                assert controller.main_window.isVisible()
                controller._open_settings()
                dialog = controller._settings_dlg
                app.processEvents()
                for page in ("Tracking", "Alerts and breaks", "Appearance", "General"):
                    dialog.select_page(page)
                    assert dialog.tabs.tabText(dialog.tabs.currentIndex()) == page
                assert controller.main_window.pages.currentWidget() is dialog
                assert not dialog.isWindow()
                controller.main_window.toggle_sidebar()
                assert controller.main_window.sidebar.width() == 56
                controller.main_window.toggle_sidebar()
                dialog.grace.setValue(60)
                dialog.reminder_min.setValue(25)
                dialog.theme_mode.setCurrentIndex(dialog.theme_mode.findData("light"))
                dialog.hud_size.setCurrentIndex(dialog.hud_size.findData("l"))
                dialog.hud_visible.setChecked(True)
                dialog.hud_orientation.setCurrentIndex(dialog.hud_orientation.findData("vertical"))
                dialog.mascot_style.setCurrentIndex(dialog.mascot_style.findData("text"))
                dialog.mascot_entrance.setCurrentIndex(dialog.mascot_entrance.findData("fade"))
                artifacts = os.environ.get("SHRIMPLY_MAC_CHECK_DIR")
                if artifacts:
                    output = Path(artifacts)
                    output.mkdir(parents=True, exist_ok=True)
                    window = controller.main_window
                    for mode in ("light", "dark"):
                        dialog.theme_mode.setCurrentIndex(dialog.theme_mode.findData(mode))
                        for width in (620, 960):
                            window.resize(width, 680)
                            for page in ("Tracking", "Alerts and breaks", "Appearance", "General"):
                                dialog.select_page(page)
                                scroll = dialog.tabs.currentWidget()
                                scroll.verticalScrollBar().setValue(0)
                                app.processEvents()
                                assert window.grab().save(str(output / f"{mode}-{width}-{page.split()[0].lower()}.png"))
                                if page == "Appearance":
                                    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
                                    app.processEvents()
                                    assert window.grab().save(str(output / f"{mode}-{width}-appearance-previews.png"))
                    dialog.theme_mode.setCurrentIndex(dialog.theme_mode.findData("light"))
                dialog.autostart.setChecked(True)
                assert autostart.is_enabled()
                dialog.autostart.setChecked(False)
                assert not autostart.is_enabled()
                controller.main_window.activateWindow()
                app.processEvents()
                QTest.qWait(50)
                QTest.keySequence(controller.main_window, QKeySequence(QKeySequence.Close))
                QTest.qWait(100)
                assert not controller.main_window.isVisible()
                assert controller._settings_dlg is None
                saved = config.load()
                assert (saved["grace_s"], saved["reminder_interval_min"], saved["theme_mode"],
                        saved["hud"]["size"]) == (60, 25, "light", "l")
                assert saved["hud"]["orientation"] == "vertical"
                assert saved["mascot_style"] == "text" and saved["mascot_entrance"] == "fade"
                assert not controller.worker.isRunning()
                minute = int(time.time() // 60) * 60
                controller.log.record_duration(minute, 30, 20, 10)
                controller.main_window.refresh()
                assert controller.log.today()["seconds"] == 60
                if artifacts:
                    controller.main_window.dashboard_button.click()
                    controller.main_window.show()
                    for mode in ("light", "dark"):
                        theme.set_mode(mode)
                        for width in (620, 960):
                            controller.main_window.resize(width, 680)
                            app.processEvents()
                            assert controller.main_window.grab().save(str(output / f"{mode}-{width}-dashboard.png"))
                controller.main_window.close()
                assert not controller.main_window.isVisible()
            finally:
                if server is not None:
                    server.close()
                assert controller.shutdown()
                controller.tray.icon.hide()
                controller.main_window.hide()
                controller.main_window.deleteLater()
                app.sendPostedEvents(None, QEvent.DeferredDelete)
            persisted = PostureLog(root / "log.db")
            try:
                assert persisted.today()["seconds"] == 60
            finally:
                persisted.close()


if __name__ == "__main__":
    check_windows()
