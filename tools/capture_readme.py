"""Capture current Windows widgets with example history and no camera or user data."""
from __future__ import annotations

import copy
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
from unshrimp.core.breaks import BreakReminder
from unshrimp.core.states import State
from unshrimp.ui import theme
from unshrimp.ui.main_window import MainWindow
from unshrimp.ui.settings import SettingsDialog


OUT = ROOT / "docs" / "shots" / "landing"


class ExampleHistory:
    def day_summaries(self, _days):
        rows = []
        for offset in range(19):
            day = date.today() - timedelta(days=offset * 2)
            seconds = 3600 + (offset % 5) * 720
            good = seconds * (0.72 + (offset % 4) * 0.04)
            drifting = (seconds - good) * 0.65
            rows.append({
                "ts": datetime.combine(day, time.min).timestamp(),
                "measurement": "time", "seconds": seconds,
                "good_s": good, "drifting_s": drifting,
                "bad_s": seconds - good - drifting,
                "pct_good": good / seconds * 100,
            })
        return rows


def save(widget, name):
    path = OUT / name
    assert widget.grab().save(str(path), "WEBP", 88), path
    print(path.relative_to(OUT.parent.parent.parent))


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    theme.set_mode("dark")
    controller = Mock()
    controller.cfg = copy.deepcopy(config.DEFAULTS)
    controller.machine = SimpleNamespace(state=State.GOOD)
    controller.worker.isRunning.return_value = True
    controller.worker.camera_state = "running"
    controller.baseline = SimpleNamespace(created_at=datetime.now().timestamp())
    controller._suspended = controller._idle_stopped = controller._restart_pending = False
    controller._quitting = False
    controller._cal = controller._camera_preview = None
    controller._display_deviation = 0.3
    controller.breaks = BreakReminder(True, 2400)
    controller.log = ExampleHistory()

    window = MainWindow(controller)
    window.setAttribute(Qt.WA_DontShowOnScreen)
    window.resize(980, 900)
    window.show()
    for _ in range(3):
        app.processEvents()
    window.progress.refresh()
    save(window, "dashboard.webp")
    save(window.progress, "progress.webp")

    settings = SettingsDialog(controller.cfg, controller, parent=window.pages)
    settings.setWindowFlags(Qt.Widget)
    settings.select_page("Appearance")
    window.pages.addWidget(settings)
    window.pages.setCurrentWidget(settings)
    window.settings_heading.show()
    window._set_active_page("Settings")
    for _ in range(3):
        app.processEvents()
    settings.tabs.currentWidget().verticalScrollBar().setValue(145)
    app.processEvents()
    save(window, "settings.webp")
    window.hide()


if __name__ == "__main__":
    main()
