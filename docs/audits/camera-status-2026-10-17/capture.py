from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path.cwd()))

import config
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QAbstractButton, QLabel, QScrollArea
from unshrimp.core.breaks import BreakReminder
from unshrimp.core.states import State
from unshrimp.ui.main_window import MainWindow
from unshrimp.ui.preview import PreviewWindow, CameraPreviewWindow
from unshrimp.ui.settings import SettingsDialog

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
out.mkdir(parents=True, exist_ok=True)
measurements = []
app = QApplication([])
app.setFont(QFont("Segoe UI", 10))
palette = app.palette()
for group in (QPalette.Active, QPalette.Inactive):
    for role, color in (
        (QPalette.Window, "#1e1e1e"), (QPalette.WindowText, "#f3f4f6"),
        (QPalette.Base, "#181818"), (QPalette.AlternateBase, "#222222"),
        (QPalette.Text, "#f3f4f6"), (QPalette.Button, "#2b2b2b"),
        (QPalette.ButtonText, "#f3f4f6"), (QPalette.Mid, "#393939"),
        (QPalette.Midlight, "#343434"), (QPalette.Dark, "#121212"),
        (QPalette.Highlight, "#ec8f6b"), (QPalette.HighlightedText, "#181b20"),
    ):
        palette.setColor(group, role, QColor(color))
app.setPalette(palette)
controller = SimpleNamespace(
    cfg=copy.deepcopy(config.DEFAULTS),
    machine=SimpleNamespace(state=State.GOOD),
    worker=Mock(), baseline=SimpleNamespace(created_at=1700000000.), _suspended=False, _idle_stopped=False,
    _cal=None, _display_deviation=.2, log=Mock(), _restart_pending=False,
    breaks=BreakReminder(True, 2400),
    _open_settings=Mock(), _open_settings_page=Mock(),
    _on_pause_toggled=Mock(), start_calibration=Mock(),
    _take_break=Mock(), _snooze_break=Mock(), _end_break=Mock(),
    save_cfg=Mock(), apply_thresholds=Mock(), apply_breaks=Mock(),
    open_camera_preview=Mock(), restart_camera=Mock(),
    _preview_changed=Mock(), _quitting=False, _camera_preview=None,
)
controller.worker.isRunning.return_value = True
controller.worker.camera_state = "running"
controller.log.day_summaries.return_value = []
main = MainWindow(controller)
settings = SettingsDialog(controller.cfg, controller)
preview = PreviewWindow()
preview.set_instruction("Camera setup", "Keep your face and shoulders visible.")
preview.set_caption("Checking the camera framing.")
preview.set_checks({"present": True, "level": True})
camera = CameraPreviewWindow(controller)
controller._camera_preview = camera

widgets = [main, settings, preview, camera]
for widget in widgets:
    widget.setAttribute(Qt.WA_DontShowOnScreen)
    widget.show()

def save(name, widget):
    app.processEvents()
    short_buttons = [button.text() for button in widget.findChildren(QAbstractButton)
                     if button.isVisibleTo(widget) and (button.width() < button.minimumSizeHint().width()
                                                       or button.height() < button.minimumSizeHint().height())]
    short_labels = [label.text() for label in widget.findChildren(QLabel)
                    if label.isVisibleTo(widget) and label.wordWrap()
                    and label.height() + 1 < label.heightForWidth(label.width())]
    overflow = [scroll.horizontalScrollBar().maximum() for scroll in widget.findChildren(QScrollArea)
                if scroll.isVisibleTo(widget) and scroll.horizontalScrollBar().maximum() > 0]
    pixmap = widget.grab()
    assert pixmap.save(str(out / name))
    measurements.append({"screen": name, "logical_size": [widget.width(), widget.height()],
                         "image_size": [pixmap.width(), pixmap.height()],
                         "pixel_ratio": widget.devicePixelRatioF(), "short_buttons": short_buttons,
                         "short_labels": short_labels, "horizontal_overflow": overflow})

def capture():
    save("01-main-running.png", main)
    save("02-settings-running.png", settings)
    controller.machine.state = State.CAMERA_ERROR
    controller.worker.camera_state = "reconnecting"
    controller.worker.camera_error = "Could not open camera 0. Is another app using it?"
    main.resize(620, 480)
    settings.resize(620, 500)
    main.refresh()
    settings.refresh_status()
    camera.refresh()
    app.processEvents()
    save("03-main-error-minimum.png", main)
    save("04-settings-error-minimum.png", settings)
    save("05-preview-error.png", camera)
    controller.machine.state = State.PAUSED
    controller.worker.isRunning.return_value = False
    camera.refresh()
    save("06-preview-paused.png", camera)
    preview.camera_unavailable("Camera disconnected.")
    app.processEvents()
    save("07-calibration-error.png", preview)
    result = {"requested_scale": os.environ.get("QT_SCALE_FACTOR", "1"),
              "ok": all(not (row["short_buttons"] or row["short_labels"] or row["horizontal_overflow"])
                        for row in measurements), "screens": measurements}
    (out / "layout-report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)
    for widget in widgets:
        widget.close()
    app.quit()

QTimer.singleShot(350, capture)
app.exec()
