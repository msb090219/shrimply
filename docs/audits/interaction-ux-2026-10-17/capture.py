from __future__ import annotations

import copy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path.cwd()))

import config
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication
from unshrimp.core.breaks import BreakReminder
from unshrimp.core.states import State
from unshrimp.ui.break_prompt import BreakPrompt
from unshrimp.ui.hud import Hud
from unshrimp.ui.main_window import MainWindow
from unshrimp.ui.preview import PreviewWindow
from unshrimp.ui.settings import SettingsDialog
from unshrimp.ui.tray import Tray
from unshrimp.ui.welcome import WelcomeDialog

out = Path(__file__).parent
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
    worker=Mock(), baseline=None, _suspended=False, _idle_stopped=False,
    _cal=None, _display_deviation=.2, log=Mock(), _restart_pending=False,
    breaks=BreakReminder(True, 2400),
    _open_settings=Mock(), _open_settings_page=Mock(),
    _on_pause_toggled=Mock(), start_calibration=Mock(),
    _take_break=Mock(), _snooze_break=Mock(), _end_break=Mock(),
    save_cfg=Mock(), apply_thresholds=Mock(), apply_breaks=Mock(),
    open_camera_preview=Mock(), restart_camera=Mock(),
)
controller.worker.isRunning.return_value = True
controller.log.day_summaries.return_value = []
main = MainWindow(controller)
settings = SettingsDialog(controller.cfg, controller)
preview = PreviewWindow()
preview.set_instruction("Camera setup", "Keep your face and shoulders visible.")
preview.set_caption("Checking the camera framing.")
preview.set_checks({"present": True, "level": True})
hud = Hud()
hud.set_live(.5, "good")
prompt = BreakPrompt()
prompt.set_suggestion("Take a short walk.")
tray = Tray()
about = WelcomeDialog(about_mode=True)

widgets = [main, settings, preview, hud, prompt, about]
for widget in widgets:
    widget.setAttribute(Qt.WA_DontShowOnScreen)
    widget.show()
tray.menu.adjustSize()

def capture():
    for name, widget in (
        ("01-main.png", main), ("02-settings.png", settings),
        ("03-camera-setup.png", preview), ("04-posture-indicator.png", hud),
        ("05-break-prompt.png", prompt), ("06-tray-menu.png", tray.menu),
        ("07-about.png", about),
    ):
        widget.grab().save(str(out / name))
    for widget in widgets:
        widget.close()
    app.quit()

QTimer.singleShot(350, capture)
app.exec()
