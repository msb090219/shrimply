"""The ordinary desktop home for Unshrimp; closing it leaves tracking in the tray."""
from __future__ import annotations

import math
import time
from datetime import date

from PySide6.QtCore import QTimer, Qt, QSize, QEvent
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QMenu,
)

from . import theme
from .stats import StatsTab
from .sections import section
from .icons import settings_icon, tracking_icon, IconButton
from .status import camera_status, calibration_status


DAILY_LINES = (
    "Stop shrimping. Start shining.",
    "Keep calm and unshrimp on.",
    "Just keep unshrimping.",
    "Seas the day—unshrimp your way.",
    "Fall seven times, unshrimp eight.",
    "Where there's a will, there's an unshrimp.",
    "Every journey begins with one unshrimp.",
    "Good things come to those who unshrimp.",
    "Dream big. Start small. Unshrimp now.",
    "If at first you don't unshrimp, try again.",
    "There's no time like now to unshrimp.",
    "Believe you can, and you're halfway unshrimped.",
    "Rise and shine. Leave shrimp mode behind.",
    "When life curls you up, unshrimp again.",
    "Progress, not prawn-fection.",
    "The world is your oyster. Unshrimp first.",
    "Be the change you wish to sea.",
    "Shell yeah, you've got this.",
    "One day or day one? Unshrimp today.",
    "Never give up. Never shrimp in.",
)


def _scroll_page(widget):
    scroll = QScrollArea()
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setWidget(widget)
    return scroll


class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Unshrimp")
        self.resize(760, 620)
        self.setMinimumSize(620, 480)
        theme.apply_desktop_theme(self)

        root = QWidget()
        root.setAttribute(Qt.WA_ContentsMarginsRespectsSafeArea, False)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 0, 16, 16)
        layout.setSpacing(12)
        settings = self.settings_button = IconButton()
        settings.setObjectName("settingsButton")
        settings.setFixedSize(32, 32)
        settings.setIconSize(QSize(18, 18))
        settings.setIcon(settings_icon(self.palette().text().color()))
        settings.setToolTip("Settings")
        settings.setAccessibleName("Settings")
        settings.setShortcut("Alt+S")
        settings.setFocusPolicy(Qt.StrongFocus)
        settings.clicked.connect(controller._open_settings)
        header = QHBoxLayout()
        header.setContentsMargins(16, 4, 16, 0)
        heading = self.dashboard_heading = QLabel("Dashboard")
        heading_font = QFont(heading.font())
        heading_font.setPointSize(13)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        header.addWidget(heading, 1)
        header.addWidget(settings)
        layout.addLayout(header)
        today = QWidget()
        content = QVBoxLayout(today)
        content.setContentsMargins(16, 16, 16, 16)
        content.setSpacing(16)
        self.daily_line = QLabel()
        quote_font = QFont(self.daily_line.font())
        quote_font.setItalic(True)
        self.daily_line.setFont(quote_font)
        self.daily_line.setWordWrap(True)
        content.addWidget(self.daily_line)
        tracking, form = section("Tracking")
        self.status = QLabel()
        font = QFont(self.status.font())
        font.setPointSize(13)
        font.setBold(True)
        self.status.setFont(font)
        self.status.setWordWrap(True)
        self.description = QLabel()
        self.description.setWordWrap(True)
        form.addRow(self.status)
        form.addRow(self.description)
        actions = QHBoxLayout()
        self.pause = QPushButton()
        self.pause.setIconSize(QSize(18, 18))
        self.pause.clicked.connect(self._toggle_pause)
        self.calibrate = QPushButton("Calibrate…")
        self.calibrate.clicked.connect(controller.start_calibration)
        actions.addWidget(self.pause)
        actions.addWidget(self.calibrate)
        self.tracking_settings = QPushButton("Camera settings…")
        self.tracking_settings.clicked.connect(lambda: controller._open_settings_page("Tracking"))
        actions.addWidget(self.tracking_settings)
        actions.addStretch()
        form.addRow(actions)
        self.camera = QLabel()
        self.camera.setWordWrap(True)
        self.baseline = QLabel()
        self.baseline.setWordWrap(True)
        camera_actions = QHBoxLayout()
        camera_actions.addWidget(self.camera, 1)
        self.camera_preview = QPushButton("Camera preview…")
        self.camera_preview.clicked.connect(controller.open_camera_preview)
        camera_actions.addWidget(self.camera_preview)
        self.camera_retry = QPushButton("Retry camera")
        self.camera_retry.clicked.connect(controller.restart_camera)
        camera_actions.addWidget(self.camera_retry)
        form.addRow("Camera", camera_actions)
        self.camera_detail = QLabel()
        self.camera_detail.setWordWrap(True)
        form.addRow(self.camera_detail)
        form.addRow("Calibration", self.baseline)
        content.addWidget(tracking)
        breaks, breaks_form = section("Break reminders")
        self.reminders = QLabel()
        self.reminders.setWordWrap(True)
        breaks_form.addRow(self.reminders)
        self.break_actions = QWidget()
        break_actions = QHBoxLayout(self.break_actions)
        break_actions.setContentsMargins(0, 0, 0, 0)
        self.take_break = QPushButton()
        self.take_break.clicked.connect(self._break_action)
        self.later_break = QPushButton("Later")
        later_menu = QMenu(self.later_break)
        later_menu.addAction("In 5 min", lambda: controller._snooze_break(5))
        later_menu.addAction("In 10 min", lambda: controller._snooze_break(10))
        later_menu.addAction("Skip this reminder", controller._skip_break)
        self.later_break.setMenu(later_menu)
        break_actions.addWidget(self.take_break)
        break_actions.addWidget(self.later_break)
        reminder_actions = QHBoxLayout()
        reminder_actions.addWidget(self.break_actions)
        reminder_actions.addStretch()
        self.reminder_settings = QPushButton("Break settings…")
        self.reminder_settings.clicked.connect(lambda: controller._open_settings_page("Alerts and breaks"))
        reminder_actions.addWidget(self.reminder_settings)
        breaks_form.addRow(reminder_actions)
        content.addWidget(breaks)
        self.progress = StatsTab(controller.log)
        self.progress.layout().setContentsMargins(0, 0, 0, 0)
        content.addWidget(self.progress)
        content.addStretch()
        self.dashboard_page = _scroll_page(today)
        layout.addWidget(self.dashboard_page)
        footer = QLabel("Close this window to keep tracking in the system tray. Use tray → Quit to exit.")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.refresh()
        screen = self.screen()
        if screen is not None:
            area = screen.availableGeometry()
            self.resize(min(760, max(620, area.width() - 48)),
                        min(620, max(480, area.height() - 64)))

    def _toggle_pause(self):
        self.controller._on_pause_toggled(self.controller.machine.state.value != "paused")
        self.refresh()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange) and hasattr(self, "settings_button"):
            self.settings_button.setIcon(settings_icon(self.palette().text().color()))
            if hasattr(self, "pause"):
                self.pause.setIcon(tracking_icon(self.palette().text().color(),
                                                 self.controller.machine.state.value == "paused"))

    def _break_action(self):
        if self.controller.breaks.in_break:
            self.controller._end_break()
        else:
            self.controller._take_break()
        self.refresh()

    def refresh(self):
        today = date.today()
        if getattr(self, "_daily_line_date", None) != today:
            self._daily_line_date = today
            self.daily_line.setText(DAILY_LINES[today.toordinal() % len(DAILY_LINES)])
        app = self.controller
        state = app.machine.state.value
        paused = state == "paused"
        states = {
            "good": ("Sitting comfortably", "Your posture is within your calibrated range."),
            "drifting": ("Posture drifting", "Check your position and settle into your usual posture."),
            "bad": ("Time to adjust", "Your posture has moved outside your calibrated range."),
            "away": ("Away from the desk", "Tracking will pick up when you return."),
            "paused": ("Tracking paused", "Posture scoring is paused. Camera preview can run separately for framing."),
            "camera_error": ("Camera unavailable", "Check the camera connection and permissions. Unshrimp will retry."),
            "uncalibrated": ("Set up your posture baseline", "Calibrate in your usual working position to start tracking."),
        }
        title, description = states.get(state, ("Getting ready", "Waiting for a usable camera reading."))
        if app._suspended:
            title, description = "Sleeping", "Capture is stopped while the system is suspended."
        elif app._idle_stopped and not paused:
            title, description = "Tracking stopped while idle", "Tracking resumes when computer activity returns."
        elif app._cal is not None:
            title, description = "Calibration in progress", "Normal posture tracking is suspended. Follow the pose instructions."
        elif not paused and state in ("good", "drifting", "bad") and app._display_deviation is None:
            title, description = "Finding your posture", "Waiting for enough usable camera readings to score posture."
        self.status.setText(title)
        self.description.setText(description)
        self.pause.setText("Resume tracking" if paused else "Pause tracking")
        if self.pause.property("pausedIcon") != paused:
            self.pause.setIcon(tracking_icon(self.palette().text().color(), paused))
            self.pause.setProperty("pausedIcon", paused)
        self.calibrate.setEnabled(app._cal is None and not app._suspended)
        self.pause.setEnabled(app._cal is None and not app._suspended)
        camera_state, detail = camera_status(app)
        self.camera.setText(f"Camera {app.cfg['camera_index']} · {camera_state.capitalize()}")
        self.camera_detail.setText(detail)
        self.camera_detail.setVisible(camera_state != "running")
        self.camera_retry.setVisible(camera_state in ("reconnecting", "off")
                                     and not app._suspended and not app._idle_stopped)
        self.baseline.setText(calibration_status(app))
        reminder = app.breaks
        if not reminder.enabled:
            reminder_text = "Break reminders are off. Enable them in Settings → Alerts and breaks."
        elif reminder.in_break:
            seconds = math.ceil(reminder.break_remaining(time.monotonic()))
            reminder_text = f"Break in progress · {seconds // 60}:{seconds % 60:02d} remaining. Your sitting timer is paused."
        elif reminder.pending:
            reminder_text = "A break is due. Take a short walk or a comfortable stretch."
        else:
            minutes = math.ceil(reminder.remaining / 60)
            reminder_text = (f"Snoozed · {minutes} min of sitting remaining." if reminder.snoozed
                             else f"Next reminder in {minutes} min of detected sitting.")
        self.reminders.setText(reminder_text + (
            "\nTime away, pauses and calibration do not count."
            if reminder.enabled else ""))
        self.break_actions.setVisible(reminder.enabled and (reminder.pending or reminder.in_break))
        self.take_break.setText("End break" if reminder.in_break else
                                f"Start break · {app.cfg['reminder_break_min']} min")
        self.later_break.setVisible(not reminder.in_break)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self.progress.refresh()
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        # Closing the home window must not quit the tray app or stop capture.
        self.hide()
        event.ignore()
