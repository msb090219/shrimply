"""Real Qt widget and motion checks; synthetic state, no camera or saved settings."""
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path.cwd()))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractButton, QLabel, QScrollArea

import config
from unshrimp.core.breaks import BreakReminder
from unshrimp.core.calibration import StepResult
from unshrimp.core.states import State
from unshrimp.ui.app import _CAL_INSTRUCTIONS
from unshrimp.ui.hud import Hud
from unshrimp.ui.mascot import MascotWindow
from unshrimp.ui.main_window import MainWindow
from unshrimp.ui.preview import PreviewWindow, CameraPreviewWindow
from unshrimp.ui.settings import SettingsDialog

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
app = QApplication([])
app.setFont(QFont("Segoe UI", 10))
palette = app.palette()
for group in (QPalette.Active, QPalette.Inactive):
    for role, color in (
        (QPalette.Window, "#1e1e1e"), (QPalette.WindowText, "#f3f4f6"),
        (QPalette.Base, "#181818"), (QPalette.Text, "#f3f4f6"),
        (QPalette.Button, "#2b2b2b"), (QPalette.ButtonText, "#f3f4f6"),
        (QPalette.Mid, "#393939"), (QPalette.Midlight, "#343434"),
        (QPalette.Dark, "#121212"),
    ):
        palette.setColor(group, role, QColor(color))
app.setPalette(palette)
measurements = []


def save(name, widget):
    app.processEvents()
    app.processEvents()
    assert widget.grab().save(str(out / (name + ".png")))
    short_buttons = [b.text() for b in widget.findChildren(QAbstractButton)
                     if b.isVisibleTo(widget) and (b.width() < b.minimumSizeHint().width()
                                                 or b.height() < b.minimumSizeHint().height())]
    short_labels = [label.text() for label in widget.findChildren(QLabel)
                    if label.isVisibleTo(widget) and label.wordWrap() and
                    label.height() + 1 < label.heightForWidth(label.width())]
    overflow = [s.horizontalScrollBar().maximum() for s in widget.findChildren(QScrollArea)
                if s.isVisibleTo(widget) and s.horizontalScrollBar().maximum() > 0]
    measurements.append(dict(screen=name, pixel_ratio=widget.devicePixelRatioF(),
                             size=[widget.width(), widget.height()], short_buttons=short_buttons,
                             short_labels=short_labels, horizontal_overflow=overflow,
                             calibration_slots=preview.countdown.slots if widget is preview else None,
                             used_slots=preview.countdown.used_slots if widget is preview else None))


controller = SimpleNamespace(
    cfg=copy.deepcopy(config.DEFAULTS), _quitting=False, _suspended=False,
    _idle_stopped=False, _restart_pending=False, _cal=None, _camera_preview=None,
    _display_deviation=None, baseline=SimpleNamespace(created_at=1700000000.),
    machine=SimpleNamespace(state=State.PAUSED), worker=Mock(camera_state="running"),
    breaks=BreakReminder(True, 2400), log=Mock(), _preview_changed=Mock(),
    _on_pause_toggled=Mock(), start_calibration=Mock(), restart_camera=Mock(),
    open_camera_preview=Mock(), _open_settings=Mock(), _open_settings_page=Mock(),
    _take_break=Mock(), _snooze_break=Mock(), _end_break=Mock(),
    save_cfg=Mock(), apply_thresholds=Mock(), apply_breaks=Mock(),
    apply_mascot_settings=Mock(),
)
controller.worker.isRunning.return_value = True
controller.log.day_summaries.return_value = []
preview = PreviewWindow()
preview.resize(480, 540)
mirror = CameraPreviewWindow(controller)
controller._camera_preview = mirror
main = MainWindow(controller)
settings = SettingsDialog(controller.cfg, controller)
hud = Hud()
widgets = (preview, mirror, main, settings, hud)
for widget in widgets:
    widget.setAttribute(Qt.WA_DontShowOnScreen)
    widget.show()

preview.set_instruction(*_CAL_INSTRUCTIONS["setup"])
preview.set_caption("Checking your camera…")
save("00-setup-neutral", preview)
assert preview.countdown.slots == 12 and preview.countdown.used_slots == 0
preview.details_button.click()
save("00-setup-details-expanded", preview)
preview.details_button.click()
preview.set_phase("normal")
preview.set_instruction(*_CAL_INSTRUCTIONS["enter_normal"])
preview.set_caption("Get ready")
preview.countdown.set_progress(StepResult("normal", activity="preparing", duration_s=3, pose_duration_s=8))
save("01-prepare", preview)
first = preview.countdown.grab().toImage()
QTest.qWait(240)
wave_moves = first != preview.countdown.grab().toImage()
assert wave_moves and preview.countdown.remaining == 3
preview.countdown.set_reduced_motion(True)
still = preview.countdown.grab().toImage()
QTest.qWait(240)
reduced_is_static = still == preview.countdown.grab().toImage()
assert reduced_is_static and not preview.countdown.timer.isActive()
preview.countdown.set_reduced_motion(False)
preview.set_caption("Hold still")
preview.countdown.set_progress(StepResult("normal", activity="capturing", duration_s=8, pose_duration_s=8))
save("02-eight-start", preview)
assert preview.countdown.slots == 12 and preview.countdown.used_slots == 8
preview.countdown.set_progress(StepResult("normal", activity="capturing", elapsed_s=3, duration_s=8, pose_duration_s=8))
save("02-capture", preview)
preview.set_caption("Collection paused · Face the camera.")
preview.countdown.set_progress(StepResult("normal", activity="paused", elapsed_s=3, duration_s=8, pose_duration_s=8))
save("03-paused", preview)
preview.set_phase("verify")
preview.set_instruction(*_CAL_INSTRUCTIONS["enter_verify"])
preview.set_caption("Hold still")
preview.countdown.set_progress(StepResult("verify", activity="capturing", duration_s=12, pose_duration_s=12))
preview.resize(480, 500)
save("04-verify-compact", preview)
preview.set_phase("tall")
preview.set_instruction(*_CAL_INSTRUCTIONS["enter_tall"])
preview.set_caption("Keep holding · Checking sample quality")
preview.countdown.set_progress(StepResult("tall", activity="checking", elapsed_s=12, duration_s=10, pose_duration_s=10))
save("05-extra-quality", preview)
preview.camera_unavailable("Could not open camera 0. Is another app using it?")
save("06-camera-error", preview)
mirror.refresh()
save("07-preview-only", mirror)
main.refresh()
save("08-main-paused-preview", main)
settings.select_page("Appearance")
save("09-appearance", settings)
for score, name in ((0., "10-hud-low"), (1., "10-hud-middle"), (2.5, "11-hud-high"), (None, "12-hud-unknown")):
    hud.set_live(score, "")
    save(name, hud)
hud.set_live(0., "")
low_count = hud.shrimp.lit_count
hud.set_live(2., "")
meter_fills = hud.shrimp.lit_count > low_count
hud.set_compact(True)
save("15-hud-compact", hud)
hud.set_status("paused", "paused")
save("16-hud-compact-paused", hud)
hud.set_status("cam_error", "camera unavailable")
save("17-hud-compact-error", hud)
hud.set_status("uncalibrated", "calibration required")
save("18-hud-compact-uncalibrated", hud)
hud.set_compact(False)
hud.set_status("calibrating", "NORMAL 8/10s")
save("19-hud-calibrating", hud)
for key, name in (("s", "small"), ("m", "medium"), ("l", "large")):
    hud.set_size(key)
    hud.set_live(1.1, "")
    save(f"20-hud-{name}", hud)
settings.mascot_size.setCurrentIndex(2)
settings.hud_size.setCurrentIndex(2)
save("21-appearance-large-top", settings)
settings.tabs.currentWidget().verticalScrollBar().setValue(
    settings.tabs.currentWidget().verticalScrollBar().maximum())
save("22-appearance-large-bottom", settings)
mascot = MascotWindow()
mascot.setAttribute(Qt.WA_DontShowOnScreen)
for key, name in (("s", "small"), ("m", "medium"), ("l", "large")):
    mascot.set_options(.87, key, False)
    mascot._cur = .87
    mascot._cur_lift = 110
    mascot.show()
    save(f"23-mascot-{name}", mascot)
mascot.force_hide()
mascot.deleteLater()
settings.resize(620, 500)
save("24-settings-compact-appearance", settings)
settings.select_page("Tracking")
save("25-settings-compact-tracking", settings)
settings._open_exercise_editor()
settings._exercise_dialog.resize(540, 320)
save("26-suggestions-compact", settings._exercise_dialog)
settings._close_exercise_editor()
assert meter_fills
hud.hide()
preview.show_result(True, "Your new baseline was saved.")
save("13-complete", preview)
preview.help_button.click()
save("14-complete-help", preview)
motion = dict(preparation_moves=wave_moves, reduced_motion_static=reduced_is_static,
              meter_fills=meter_fills)
report = dict(scale=os.environ.get("QT_SCALE_FACTOR", "1"), motion=motion, screens=measurements,
              ok=all(not (r["short_buttons"] or r["short_labels"] or r["horizontal_overflow"])
                     for r in measurements))
(out / "layout-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
preview.stop_preview()
for widget in widgets:
    if widget is settings:
        widget._discard()
    else:
        widget.close()
assert report["ok"], "See layout-report.json for overflow/clipping"
