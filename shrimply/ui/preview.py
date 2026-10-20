"""One calibration window: live mirror, readable guidance, checks, and actions."""
from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QToolButton, QSizePolicy, QScrollArea, QFrame,
)

from . import theme
from .sections import section
from .status import camera_status, camera_mode
from .tray import shrimp_icon
from .countdown import ShrimpCountdown
from ..vision.worker import PreviewPayload

PHASES = ("setup", "tall", "normal", "hunch", "verify")
CHECK_NAMES = {"present": "Face and shoulders", "level": "Camera level",
               "gaze": "Camera height", "framing": "Distance and framing", "light": "Lighting"}


def _disclosure(text):
    button = QToolButton()
    button.setText(text)
    button.setAccessibleName(text.replace("&", ""))
    button.setCheckable(True)
    button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    button.setArrowType(Qt.RightArrow)
    button.setAutoRaise(True)
    button.toggled.connect(lambda checked: button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow))
    button.setStyleSheet(f"""
        QToolButton {{ background: transparent; color: palette(text);
                       border: 1px solid transparent; padding: 3px 4px; }}
        QToolButton:checked, QToolButton:pressed {{ background: transparent; }}
        QToolButton:hover {{ color: {theme.SHRIMP}; }}
        QToolButton:focus {{ border: 1px dotted {theme.SHRIMP}; }}
    """)
    return button


class _CameraView(QWidget):
    def __init__(self):
        super().__init__()
        self.image: QImage | None = None
        self.placeholder = "Camera preview"
        self.marks = (None,) * 4
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAccessibleName("Live camera mirror")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#15181c"))
        image = self.image
        if image is None or image.isNull():
            painter.setPen(QColor("#b6bec9"))
            painter.drawText(self.rect(), Qt.AlignCenter, self.placeholder)
            return
        width, height = image.width(), image.height()
        scale = min(self.width() / width, self.height() / height)
        target = QRect(0, 0, round(width * scale), round(height * scale))
        target.moveCenter(self.rect().center())
        painter.drawImage(target, image)
        painter.setRenderHint(QPainter.Antialiasing)
        # The worker mirrors the image; landmark coordinates are still unmirrored.
        points = [None if point is None else (
            target.x() + (1 - point[0] / width) * target.width(),
            target.y() + point[1] / height * target.height()) for point in self.marks]
        if points[0] is not None and points[1] is not None:
            painter.setPen(QPen(QColor(theme.SHRIMP), 2))
            painter.drawLine(round(points[0][0]), round(points[0][1]), round(points[1][0]), round(points[1][1]))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.SHRIMP))
        for point in points:
            if point is not None:
                painter.drawEllipse(round(point[0]) - 3, round(point[1]) - 3, 6, 6)


class CameraPreviewWindow(QWidget):
    """A framing mirror that follows the existing camera policy."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Camera preview")
        self.resize(540, 420)
        theme.apply_desktop_theme(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.status = QLabel()
        layout.addWidget(self.status)
        self.video = _CameraView()
        layout.addWidget(self.video, 1)
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)
        privacy = QLabel("Live mirror · Frames stay on this device and are not saved.")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        actions = QHBoxLayout()
        self.retry_button = QPushButton("Retry camera")
        self.retry_button.clicked.connect(controller.restart_camera)
        actions.addWidget(self.retry_button)
        actions.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        actions.addWidget(close)
        layout.addLayout(actions)
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.refresh)

    def _clear_frame(self):
        self.video.image = None
        self.video.marks = (None,) * 4
        self.video.update()

    def refresh(self):
        app = self.controller
        state, detail = camera_status(app)
        self.status.setText(f"Camera {app.cfg['camera_index']} · {state.capitalize()}")
        self.detail.setText(detail)
        self.retry_button.setVisible(state in ("reconnecting", "off")
                                     and camera_mode(app) != "off")
        if state not in ("running", "preview"):
            self.video.placeholder = "Camera " + state
            self._clear_frame()

    def update_frame(self, payload):
        if self.sender() is not None and self.sender() is not self.controller.worker:
            return
        if self.isVisible() and camera_status(self.controller)[0] in ("running", "preview"):
            self.video.image = payload.image
            self.video.marks = (payload.ls, payload.rs, payload.le, payload.re)
            self.video.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.controller._preview_changed()
        self.refresh()
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        self.controller._preview_changed()
        self._clear_frame()
        super().hideEvent(event)


class PreviewWindow(QWidget):
    cancel_requested = Signal()
    retry_requested = Signal()
    camera_retry_requested = Signal()
    continue_requested = Signal()
    start_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("calibrationWindow")
        self.setWindowTitle("Calibration")
        self.resize(540, 680)
        self.setMinimumSize(480, 500)
        theme.apply_desktop_theme(self)
        self._active = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.step_label = QLabel()
        self.step_label.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED};")
        layout.addWidget(self.step_label)
        guidance = QWidget()
        guidance_layout = QVBoxLayout(guidance)
        guidance_layout.setContentsMargins(0, 0, 0, 0)
        guidance_layout.setSpacing(6)
        self.instruction = QLabel()
        self.instruction.setStyleSheet("font-size: 24px; font-weight: 600;")
        self.instruction.setWordWrap(True)
        guidance_layout.addWidget(self.instruction)
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_DIM};")
        guidance_layout.addWidget(self.detail)
        layout.addWidget(guidance)
        self.timing = QFrame()
        self.timing.setObjectName("calibrationTiming")
        self.timing.setStyleSheet("""
            QFrame#calibrationTiming { background: palette(base);
                border: 1px solid palette(mid); border-radius: 6px; }
        """)
        timing_layout = QVBoxLayout(self.timing)
        timing_layout.setContentsMargins(12, 10, 12, 10)
        timing_layout.setSpacing(2)
        self.caption = QLabel()
        self.caption.setWordWrap(True)
        self.caption.setStyleSheet("font-size: 13px; font-weight: 600;")
        timing_layout.addWidget(self.caption)
        self.countdown = ShrimpCountdown(self)
        timing_layout.addWidget(self.countdown)
        layout.addWidget(self.timing)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(12)
        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(body)
        layout.addWidget(self.scroll, 1)
        self.video = _CameraView()
        body_layout.addWidget(self.video, 1)
        self.help_button = _disclosure("How it works")
        body_layout.addWidget(self.help_button, 0, Qt.AlignLeft)
        self.feedback_group, feedback_form = section("What you'll see")
        for title, text in (
            ("Posture indicator", "Sitting comfortably → Posture drifting → Adjust posture. These labels compare your position with your saved baseline."),
            ("Shrimp cue", "If enabled, the shrimp appears as you slouch. Settle back into range and it fades away."),
            ("Break reminders", "If enabled, reminders count detected sitting time. Take a break starts a two-minute countdown; Later snoozes for five more detected minutes."),
        ):
            label = QLabel(text)
            label.setWordWrap(True)
            if title == "Shrimp cue":
                example = QWidget()
                row = QHBoxLayout(example)
                row.setContentsMargins(0, 0, 0, 0)
                cue = QLabel()
                cue.setPixmap(shrimp_icon(theme.SHRIMP).pixmap(32, 32))
                cue.setAccessibleName("Example shrimp cue")
                row.addWidget(cue)
                row.addWidget(label, 1)
                feedback_form.addRow(title, example)
            else:
                feedback_form.addRow(title, label)
        body_layout.addWidget(self.feedback_group)
        self.help_button.toggled.connect(lambda expanded: self._show_optional(self.feedback_group, expanded))
        self.camera_footer = QWidget()
        footer_layout = QHBoxLayout(self.camera_footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(8)
        self.privacy = QLabel("Live preview · Not recorded")
        self.privacy.setWordWrap(True)
        self.privacy.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED};")
        self.privacy.setToolTip("Camera frames stay on this device and are not saved.")
        self.privacy.setAccessibleDescription(self.privacy.toolTip())
        footer_layout.addWidget(self.privacy, 1)
        self.details_button = _disclosure("Camera details")
        footer_layout.addWidget(self.details_button)
        body_layout.addWidget(self.camera_footer)
        self.check_group, check_form = section("Camera setup checks")
        self.check_heading = self.check_group.findChild(QLabel, "sectionTitle")
        check_body = QWidget()
        checks = QGridLayout(check_body)
        checks.setContentsMargins(0, 0, 0, 0)
        checks.setVerticalSpacing(6)
        self.check_labels = {}
        for index, (key, name) in enumerate(CHECK_NAMES.items()):
            label = QLabel(f"{name}: Waiting")
            label.setWordWrap(True)
            checks.addWidget(label, index // 2, index % 2)
            self.check_labels[key] = label
        check_form.addRow(check_body)
        body_layout.addWidget(self.check_group)
        self.details_button.toggled.connect(lambda expanded: self._show_optional(self.check_group, expanded))
        body_layout.addStretch()
        buttons = QHBoxLayout()
        self.skip_button = QPushButton("Continue anyway…")
        self.skip_button.setToolTip("Skip camera setup checks. This may make posture scoring less reliable.")
        self.skip_button.clicked.connect(self.continue_requested.emit)
        buttons.addWidget(self.skip_button)
        self.camera_retry_button = QPushButton("Retry camera")
        self.camera_retry_button.clicked.connect(self.camera_retry_requested.emit)
        buttons.addWidget(self.camera_retry_button)
        buttons.addStretch()
        self.retry_button = QPushButton("Retry calibration")
        self.retry_button.clicked.connect(self.retry_requested.emit)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.hide)
        self.start_button = QPushButton("Start tracking")
        self.start_button.clicked.connect(self.start_requested.emit)
        for button in (self.retry_button, self.cancel_button, self.close_button, self.start_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.apply_theme()
        self.begin()
        screen = self.screen()
        if screen is not None:
            area = screen.availableGeometry()
            self.resize(min(540, max(480, area.width() - 48)),
                        min(680, max(500, area.height() - 64)))

    def apply_theme(self):
        self.step_label.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED};")
        self.detail.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_DIM};")
        self.privacy.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED};")
        self.countdown.apply_theme()
        self.update()

    def begin(self):
        self._active = True
        self.countdown.clear()
        self.video.placeholder = "Camera preview"
        self.video.image = None
        self.video.marks = (None,) * 4
        self.video.update()
        self.skip_button.hide()
        self.camera_retry_button.hide()
        self.retry_button.hide()
        self.close_button.hide()
        self.start_button.hide()
        self.feedback_group.hide()
        self.help_button.setChecked(False)
        self.help_button.hide()
        self.details_button.setChecked(False)
        self.details_button.show()
        self.camera_footer.show()
        self.video.show()
        self.privacy.show()
        self.cancel_button.show()
        self.check_group.hide()
        self.set_phase("setup")
        self.set_checks({})
        self.set_caption("Checking your camera. Keep your face and shoulders visible.")
        self.scroll.verticalScrollBar().setValue(0)

    def _show_optional(self, widget, expanded):
        widget.setVisible(expanded)
        if expanded:
            QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(widget, 0, 8))

    def set_phase(self, phase):
        if phase in PHASES:
            index = PHASES.index(phase)
            self.phase = phase
            self.step_label.setText(f"Step {index + 1} of 5")
            title = "Camera setup checks" if phase == "setup" else "Setup check results"
            self.check_heading.setText(title)
            self.check_group.setAccessibleName(title)

    def set_checks(self, checks):
        for key, label in self.check_labels.items():
            state = "Passed" if checks.get(key) else "Needs attention" if key in checks else "Waiting"
            label.setText(f"{CHECK_NAMES[key]}: {state}")

    def set_override_available(self, available):
        self.skip_button.setVisible(available and self._active)
        if available and self._active:
            self.details_button.setChecked(True)

    def update_frame(self, payload: PreviewPayload):
        if self._active:
            self.camera_retry_button.hide()
            self.video.image = payload.image
            self.video.marks = (payload.ls, payload.rs, payload.le, payload.re)
            self.video.update()

    def stop_preview(self):
        self._active = False
        self.countdown.clear()
        self.video.placeholder = "Camera preview stopped"
        self.video.image = None
        self.video.marks = (None,) * 4
        self.video.update()

    def set_caption(self, text):
        self.caption.setText(text)

    def camera_unavailable(self, message, retry=True):
        self.countdown.pause()
        self.video.image = None
        self.video.marks = (None,) * 4
        self.video.placeholder = "Camera reconnecting"
        self.video.update()
        if self.phase == "setup":
            self.set_checks({})
        self.camera_retry_button.setVisible(retry)
        self.set_caption(message + (" Retrying automatically. Calibration will continue when frames return."
                                    if retry else " Calibration will continue after the computer wakes."))

    def set_instruction(self, title, detail=""):
        self.instruction.setText(title)
        self.detail.setText(detail)

    def show_result(self, success, message):
        self.stop_preview()
        self.phase = "done" if success else "failed"
        self.step_label.setText("Calibration saved" if success else "Calibration was not saved")
        self.set_instruction("Ready to track" if success else "Let's try again", message)
        self.set_caption("Tracking is paused. Choose Start tracking when you're ready."
                         if success else "Adjust your setup before retrying.")
        self.video.setVisible(not success)
        self.privacy.setVisible(not success)
        self.details_button.setChecked(False)
        self.details_button.hide()
        self.camera_footer.hide()
        self.check_group.hide()
        self.help_button.setChecked(False)
        self.help_button.setVisible(success)
        self.feedback_group.hide()
        self.skip_button.hide()
        self.camera_retry_button.hide()
        self.cancel_button.hide()
        self.retry_button.setVisible(not success)
        self.close_button.show()
        self.close_button.setText("Later" if success else "Close")
        self.start_button.setVisible(success)
        self.show()
        self.raise_()
        self.scroll.verticalScrollBar().setValue(0)
        (self.start_button if success else self.retry_button).setFocus()

    def closeEvent(self, event):
        if self._active:
            self.cancel_requested.emit()
            event.ignore()
        else:
            super().closeEvent(event)
