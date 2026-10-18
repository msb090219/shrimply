"""Welcome and About use the same compact desktop surfaces as the rest of the app."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from unshrimp import __version__
from . import theme
from .sections import section


class WelcomeDialog(QDialog):
    def __init__(self, parent=None, about_mode=False):
        super().__init__(parent)
        self.calibrate_requested = False
        self.setWindowTitle("About" if about_mode else "Welcome")
        self.resize(480, 380 if about_mode else 540)
        self.setMinimumWidth(420)
        theme.apply_desktop_theme(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        body = QWidget()
        content = QVBoxLayout(body)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(12)
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        brand, form = section("Unshrimp" if about_mode else "Welcome to Unshrimp")
        if about_mode:
            form.addRow(QLabel(f"Version {__version__}"))
        description = QLabel("A private posture companion for your desk. Gentle posture cues and break reminders help you notice your sitting habits.")
        description.setWordWrap(True)
        form.addRow(description)
        content.addWidget(brand)
        if not about_mode:
            setup, form = section("A minute to get set up")
            for text in (
                "Keep your face and both shoulders visible. The live mirror will help you check your framing.",
                "Sit tall to show your upright range, sit normally to set your everyday baseline, then demonstrate a comfortable slouch so Unshrimp can tell them apart.",
                "Finally, sit normally again to check the result. Preparation cues guide each pose; setup may take longer if tracking is interrupted.",
            ):
                label = QLabel(text)
                label.setWordWrap(True)
                form.addRow(label)
            content.addWidget(setup)
        privacy, form = section("Camera and privacy")
        text = (
            "Camera frames are processed on this device and are not saved. "
            "Your settings and posture history are stored locally. No account is needed."
        )
        if not about_mode:
            text += " You can pause tracking at any time. Choosing Later leaves the camera off."
        body = QLabel(text)
        body.setWordWrap(True)
        form.addRow(body)
        content.addWidget(privacy)
        content.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton("Close" if about_mode else "Later")
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        if not about_mode:
            calibrate = QPushButton("Calibrate now")
            calibrate.setDefault(True)
            calibrate.clicked.connect(self._calibrate)
            buttons.addWidget(calibrate)
        layout.addLayout(buttons)

    def _calibrate(self):
        self.calibrate_requested = True
        self.accept()
