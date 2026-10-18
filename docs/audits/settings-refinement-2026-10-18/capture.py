"""Render Settings with synthetic data; never touches camera or user files."""
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
from PySide6.QtWidgets import QApplication, QAbstractButton, QLabel, QScrollArea
import config
from unshrimp.core.states import State
from unshrimp.ui.settings import SettingsDialog
from unshrimp.ui.break_prompt import BreakPrompt

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
app = QApplication([])
app.setFont(QFont("Segoe UI", 10))
palette = app.palette()
for group in (QPalette.Active, QPalette.Inactive):
    for role, color in ((QPalette.Window, "#1e1e1e"), (QPalette.WindowText, "#f3f4f6"),
                        (QPalette.Base, "#181818"), (QPalette.Text, "#f3f4f6"),
                        (QPalette.Button, "#2b2b2b"), (QPalette.ButtonText, "#f3f4f6"),
                        (QPalette.Mid, "#393939"), (QPalette.Midlight, "#343434"),
                        (QPalette.Dark, "#121212")):
        palette.setColor(group, role, QColor(color))
app.setPalette(palette)
controller = SimpleNamespace(cfg=copy.deepcopy(config.DEFAULTS),
    machine=SimpleNamespace(state=State.PAUSED), worker=Mock(camera_state="running"),
    _quitting=False, _suspended=False, _idle_stopped=False, _restart_pending=False,
    _cal=None, _camera_preview=None, baseline=SimpleNamespace(created_at=1700000000.),
    open_camera_preview=Mock(), restart_camera=Mock(), _show_about=Mock(),
    tray=Mock(), apply_preferences=Mock())
dialog = SettingsDialog(controller.cfg, controller)
dialog.setAttribute(Qt.WA_DontShowOnScreen)
dialog.show()
records = []

def save(name, widget=dialog):
    app.processEvents()
    app.processEvents()
    widget.grab().save(str(out / f"{name}.png"))
    buttons = [b.text() for b in widget.findChildren(QAbstractButton)
               if b.isVisibleTo(widget) and (b.width() < b.minimumSizeHint().width()
                                             or b.height() < b.minimumSizeHint().height())]
    labels = [l.text() for l in widget.findChildren(QLabel)
              if l.isVisibleTo(widget) and l.wordWrap() and l.height()+1 < l.heightForWidth(l.width())]
    overflow = [s.horizontalScrollBar().maximum() for s in widget.findChildren(QScrollArea)
                if s.isVisibleTo(widget) and s.horizontalScrollBar().maximum() > 0]
    records.append(dict(screen=name, size=[widget.width(), widget.height()],
                        short_buttons=buttons, short_labels=labels, horizontal_overflow=overflow))

for width, height in ((900, 700), (760, 640), (620, 500)):
    dialog.resize(width, height)
    for page in ("Tracking", "Reminders", "Appearance", "General"):
        dialog.select_page(page)
        scroll = dialog.tabs.currentWidget()
        scroll.verticalScrollBar().setValue(0)
        save(f"{width}-{page.lower()}-top")
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
        save(f"{width}-{page.lower()}-bottom")
dialog.select_page("Appearance")
dialog.hud_size.setCurrentIndex(2)
dialog.mascot_size.setCurrentIndex(2)
save("620-appearance-large")
dialog.mascot_on.setChecked(False)
dialog.hud_visible.setChecked(False)
save("620-appearance-disabled")
controller.apply_preferences.side_effect = OSError("The settings file could not be written")
dialog.mascot_on.setChecked(True)
save("620-save-error")
controller.apply_preferences.side_effect = None
dialog.select_page("Reminders")
dialog.reminder.setChecked(False)
save("620-reminders-disabled")
dialog._show_example()
dialog._example.setAttribute(Qt.WA_DontShowOnScreen)
save("reminder-example", dialog._example)
dialog._example.take_button.click()
save("break-example", dialog._example)
dialog._open_exercise_editor()
save("suggestions", dialog._exercise_dialog)
dialog._close_exercise_editor()
dialog._close_example()
dialog.reject()
report = dict(scale=os.environ.get("QT_SCALE_FACTOR", "1"), screens=records,
              ok=all(not (r["short_buttons"] or r["short_labels"] or r["horizontal_overflow"]) for r in records))
(out / "layout-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
assert report["ok"], "See layout-report.json"
