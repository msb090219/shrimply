"""Render real onboarding widgets without a camera or user settings."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QAbstractButton, QLabel, QScrollArea

from unshrimp.ui.app import _CAL_INSTRUCTIONS
from unshrimp.ui.preview import PreviewWindow
from unshrimp.ui.welcome import WelcomeDialog

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
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
rows = []


def save(name, window):
    window.setAttribute(Qt.WA_DontShowOnScreen)
    window.show()
    app.processEvents()
    app.processEvents()
    assert window.grab().save(str(out / (name + ".png")))
    short_buttons = [b.text() for b in window.findChildren(QAbstractButton)
                     if b.isVisibleTo(window) and
                     (b.width() < b.minimumSizeHint().width() or
                      b.height() < b.minimumSizeHint().height())]
    short_labels = [label.text() for label in window.findChildren(QLabel)
                    if label.isVisibleTo(window) and label.wordWrap() and
                    label.height() + 1 < label.heightForWidth(label.width())]
    overflow = [s.horizontalScrollBar().maximum() for s in window.findChildren(QScrollArea)
                if s.isVisibleTo(window) and s.horizontalScrollBar().maximum() > 0]
    rows.append(dict(screen=name, pixel_ratio=window.devicePixelRatioF(),
                     size=[window.width(), window.height()], short_buttons=short_buttons,
                     short_labels=short_labels, horizontal_overflow=overflow))


welcome = WelcomeDialog()
save("01-welcome", welcome)
welcome.resize(420, 400)
save("02-welcome-compact", welcome)
preview = PreviewWindow()
preview.set_instruction(*_CAL_INSTRUCTIONS["setup"])
preview.set_caption("Checking your camera…")
save("03-setup", preview)
preview.set_checks({"present": True, "level": True, "gaze": False})
preview.set_override_available(True)
save("03-setup-details", preview)
preview.begin()
for phase in ("tall", "normal", "hunch"):
    preview.set_phase(phase)
    preview.set_instruction(*_CAL_INSTRUCTIONS["enter_" + phase])
    preview.set_caption("Get ready · 3s")
    save("03-" + phase, preview)
preview.show_result(True, "Your new baseline was saved. The camera can now track against it.")
save("04-ready", preview)
preview.help_button.click()
save("04-how-it-works", preview)
preview.help_button.click()
preview.resize(480, 500)
save("05-ready-compact", preview)
preview.begin()
preview.show_result(False, "Poses were too similar. Your previous calibration is still active.")
save("06-retry-compact", preview)
preview.begin()
preview.set_instruction(*_CAL_INSTRUCTIONS["setup"])
preview.camera_unavailable("Could not open camera 0. Is another app using it?")
save("06-camera-error-compact", preview)
about = WelcomeDialog(about_mode=True)
save("07-about", about)
result = dict(scale=os.environ.get("QT_SCALE_FACTOR", "1"), screens=rows,
              ok=all(not (r["short_buttons"] or r["short_labels"] or r["horizontal_overflow"])
                     for r in rows))
(out / "layout-report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
preview.stop_preview()
for window in (welcome, preview, about):
    window.close()
assert result["ok"], "See layout-report.json for clipping/overflow"
