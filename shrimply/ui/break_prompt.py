"""A small, modeless break prompt; posture feedback keeps its own space."""
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu
import math

from . import theme
from .macos_windows import join_fullscreen_spaces


class BreakPrompt(QFrame):
    take_requested = Signal()
    later_requested = Signal(int)
    skip_requested = Signal()
    end_requested = Signal()
    example_action = Signal(str)

    def __init__(self, example=False, break_minutes=2):
        super().__init__()
        self.example = example
        self.break_minutes = break_minutes
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Shrimply — Break reminder")
        self.setObjectName("breakPrompt")
        self.setFrameShape(QFrame.NoFrame)
        self.setFixedWidth(340)
        theme.apply_desktop_theme(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self._in_break = False
        self._suggestion = "Take a short walk or a comfortable stretch."
        title = self.title = QLabel()
        title.setWordWrap(True)
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet(f"color: {theme.SHRIMP};")
        layout.addWidget(title)
        self.suggestion = QLabel()
        self.suggestion.setWordWrap(True)
        self.suggestion.setTextFormat(Qt.PlainText)
        layout.addWidget(self.suggestion)
        buttons = QHBoxLayout()
        self.take_button = QPushButton()
        self.take_button.clicked.connect(self._primary_action)
        self.later_button = QPushButton("Later")
        self.later_button.setToolTip("Choose when to remind you again.")
        later_menu = QMenu(self.later_button)
        later_menu.addAction("In 5 min", lambda: self._later_action(5))
        later_menu.addAction("In 10 min", lambda: self._later_action(10))
        later_menu.addAction("Skip this reminder", self._skip_action)
        self.later_button.setMenu(later_menu)
        buttons.addWidget(self.take_button, 1)
        buttons.addWidget(self.later_button, 1)
        layout.addLayout(buttons)
        self.set_break_minutes(break_minutes)
        self.set_suggestion(self._suggestion)

    def showEvent(self, event):
        super().showEvent(event)
        if self.isWindow():
            join_fullscreen_spaces(self)

    def set_break_minutes(self, minutes):
        self.break_minutes = minutes
        if not self._in_break:
            self.title.setText(f"Take a {minutes}-minute break")
            self.take_button.setText("Start")
            self.take_button.setToolTip(
                f"Start a {minutes}-minute break. Camera tracking continues; the sitting timer pauses.")
            self.adjustSize()

    def set_suggestion(self, text):
        self._suggestion = text
        self.suggestion.setText(text)
        self.adjustSize()

    def set_break_state(self, remaining=None):
        self._in_break = remaining is not None
        if self._in_break:
            seconds = math.ceil(remaining)
            self.title.setText(f"Break in progress · {seconds // 60}:{seconds % 60:02d}")
            self.suggestion.setText("Walk around or stretch comfortably. Your sitting timer is paused; camera tracking continues.")
            self.take_button.setText("End break")
            self.take_button.setToolTip("End the break early and start a fresh sitting interval.")
        else:
            self.suggestion.setText(self._suggestion)
            self.set_break_minutes(self.break_minutes)
        self.later_button.setVisible(not self._in_break)
        self.adjustSize()

    def _primary_action(self):
        if self.example:
            self.set_break_state(None if self._in_break else self.break_minutes * 60)
            self.example_action.emit("Preview only · your sitting timer is unchanged.")
            return
        (self.end_requested if self._in_break else self.take_requested).emit()

    def _later_action(self, minutes):
        if self.example:
            self.set_break_state(None)
            self.example_action.emit(f"Preview only · would remind you again in {minutes} min of detected sitting.")
        else:
            self.later_requested.emit(minutes)

    def _skip_action(self):
        if self.example:
            self.set_break_state(None)
            self.example_action.emit("Preview only · would restart the sitting interval.")
        else:
            self.skip_requested.emit()

    def closeEvent(self, event):
        if self.example:
            event.accept()
            return
        if self._in_break:
            self.end_requested.emit()
        else:
            self.later_requested.emit(5)
        event.ignore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(self.palette().mid().color(), 1))
        painter.setBrush(self.palette().window())
        painter.drawRoundedRect(QRectF(.5, .5, self.width() - 1, self.height() - 1),
                                theme.R_HUD, theme.R_HUD)
