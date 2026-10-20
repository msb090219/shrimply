"""System tray icon + menu. The icon is the shrimp glyph, drawn in code
and tinted by posture state (uncalibrated shows it in brand salmon).

Left-click opens the menu at the cursor (Windows only does that on
right-click by default); right-click still works too.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QRectF, Qt, QTimer, Signal, QSignalBlocker
from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget, QHBoxLayout, QVBoxLayout, QLabel

from . import theme
from .shrimp import paint_shrimp

STATE_COLORS = theme.STATE_COLORS
STATE_LABELS = {
    "good": "Sitting comfortably", "drifting": "Posture drifting",
    "bad": "Time to adjust", "away": "Away from the desk",
    "paused": "Tracking paused", "camera_error": "Camera unavailable",
    "uncalibrated": "Calibration required", "starting": "Finding your posture",
    "calibrating": "Calibration in progress", "idle": "Camera off while idle",
    "sleeping": "System sleeping", "break": "Break in progress",
    "preview": "Tracking paused · camera preview active",
}


def shrimp_icon(color_hex: str) -> QIcon:
    """The shrimp mark at tray sizes, tinted per state — the designed
    master art when provided, the code-drawn shrimp otherwise."""
    from . import assets as _assets

    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(QColor(0, 0, 0, 0))
        art = _assets.tinted_shrimp(color_hex, size - 2, size - 2)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        if art is not None:
            p.drawPixmap(
                (size - art.width()) // 2, (size - art.height()) // 2, art
            )
        else:
            body_h = int(size * 0.66)  # wide arch — letterbox it
            rect = QRectF(1, (size - body_h) / 2, size - 2, body_h)
            paint_shrimp(p, rect, color_hex, details=size >= 48)
        p.end()
        icon.addPixmap(pm)
    return icon


def shrimp_pixmap_sized(size: int, color_hex: str) -> QPixmap:
    """A square tinted shrimp pixmap (master art when provided)."""
    from . import assets as _assets

    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    art = _assets.tinted_shrimp(color_hex, size, size)
    if art is not None:
        p.drawPixmap((size - art.width()) // 2, (size - art.height()) // 2, art)
    else:
        body_h = int(size * 0.66)
        paint_shrimp(p, QRectF(0, (size - body_h) / 2, size, body_h), color_hex,
                     details=False)
    p.end()
    return pm


class Tray(QObject):
    unavailable = Signal()
    open_requested = Signal()
    calibrate_requested = Signal()
    pause_toggled = Signal(bool)  # True = now paused
    hud_toggled = Signal(bool)  # True = now visible
    compact_toggled = Signal(bool)
    settings_requested = Signal()
    quit_requested = Signal()
    about_requested = Signal()
    mascot_toggled = Signal(bool)  # quick toggle from the menu
    continue_anyway = Signal()  # skip a stuck setup check during calibration

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon = QSystemTrayIcon(self)
        self.icon.setIcon(shrimp_icon(STATE_COLORS["uncalibrated"]))
        self.icon.setToolTip("Unshrimp — not calibrated yet")
        # NOTE: .show() is deferred into the event loop via show_when_ready()
        # — status items created before the macOS event loop runs are the
        # classic "icon never appears" failure.

        from . import theme

        self.menu = QMenu()
        self.menu.setMinimumWidth(248)
        self.menu.setStyleSheet(theme.MENU_QSS)

        # status header: tinted mini shrimp + state name (not clickable)
        self._header_widget = QWidget()
        hrow = QHBoxLayout(self._header_widget)
        hrow.setContentsMargins(14, 8, 14, 8)
        hrow.setSpacing(8)
        self._header_shrimp = QLabel()
        self._header_shrimp.setPixmap(
            shrimp_pixmap_sized(22, STATE_COLORS["uncalibrated"])
        )
        self._header_text = QLabel("Finding your posture")
        self._header_text.setStyleSheet("font-weight: 600; border: none;")
        hrow.addWidget(self._header_shrimp)
        labels = self._header_labels = QVBoxLayout()
        labels.setSpacing(3)
        labels.setAlignment(Qt.AlignTop)
        labels.addWidget(QLabel("Unshrimp"))
        labels.addWidget(self._header_text)
        self._break_text = QLabel()
        self._break_text.hide()
        labels.addWidget(self._break_text)
        hrow.addLayout(labels)
        hrow.addStretch(1)
        from PySide6.QtWidgets import QWidgetAction

        header_action = QWidgetAction(self.menu)
        header_action.setDefaultWidget(self._header_widget)

        self.cal_action = QAction("&Calibrate…", self.menu)
        self.open_action = QAction("&Open Unshrimp", self.menu)
        self.cont_action = QAction("Continue setup &anyway…", self.menu)
        self.cont_action.setVisible(False)
        self.pause_action = QAction("&Pause tracking", self.menu)
        self.hud_action = QAction("Posture &indicator", self.menu)
        self.hud_action.setCheckable(True)
        self.hud_action.setChecked(True)
        self.mascot_action = QAction("Floating &shrimp", self.menu)
        self.mascot_action.setCheckable(True)
        self.mascot_action.setChecked(True)
        self.compact_action = QAction("&Hide brief adjustment cue", self.menu)
        self.compact_action.setCheckable(True)
        self.compact_action.toggled.connect(self.compact_toggled.emit)
        self.settings_action = QAction("&Settings…", self.menu)
        self.about_action = QAction("&About Unshrimp", self.menu)
        self.quit_action = QAction("&Quit", self.menu)

        self.menu.addAction(header_action)
        self.menu.addSeparator()
        for action in (self.open_action, self.pause_action, self.cal_action,
                       self.cont_action, self.settings_action):
            self.menu.addAction(action)
        self.menu.addSeparator()
        self.menu.addAction(self.compact_action)
        self.visibility_menu = self.menu.addMenu("&Visibility")
        self.visibility_menu.addAction(self.hud_action)
        self.visibility_menu.addAction(self.mascot_action)
        self.menu.addAction(self.about_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        self.cal_action.triggered.connect(self.calibrate_requested)
        self.open_action.triggered.connect(self.open_requested)
        self.cont_action.triggered.connect(self.continue_anyway.emit)
        self.pause_action.triggered.connect(self._on_pause)
        self.hud_action.triggered.connect(self._on_hud)
        self.mascot_action.toggled.connect(self.mascot_toggled.emit)
        self.settings_action.triggered.connect(self.settings_requested)
        self.about_action.triggered.connect(self.about_requested)
        self.quit_action.triggered.connect(self.quit_requested)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._on_activated)

        self._paused = False
        self._hud_visible = True
        self._state_key = None

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # left click
            self.menu.popup(QCursor.pos())

    # ------------------------------------------------------------------
    def show_when_ready(self) -> None:
        """Call from the running event loop (e.g. QTimer.singleShot(0, …))."""
        from unshrimp import diag

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.icon.show()
            diag.log("tray: shown (system tray available)")
        else:
            diag.log("tray: unavailable — retrying in 3s")
            QTimer.singleShot(3000, self._retry_show)

    def _retry_show(self) -> None:
        from unshrimp import diag

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.icon.show()
            diag.log("tray: shown on retry")
        else:
            diag.log("tray: still unavailable — retrying in 3s")
            self.unavailable.emit()
            QTimer.singleShot(3000, self._retry_show)

    # ------------------------------------------------------------------
    def _on_pause(self):
        self._paused = not self._paused
        self.pause_toggled.emit(self._paused)

    def _on_hud(self):
        self._hud_visible = not self._hud_visible
        self.hud_toggled.emit(self._hud_visible)

    def sync_hud_action(self, visible: bool) -> None:
        self._hud_visible = visible
        with QSignalBlocker(self.hud_action):
            self.hud_action.setChecked(visible)

    def sync_compact_action(self, compact: bool) -> None:
        with QSignalBlocker(self.compact_action):
            self.compact_action.setChecked(compact)

    def show_continue(self, visible: bool) -> None:
        self.cont_action.setVisible(visible)

    def set_mascot_checked(self, on: bool) -> None:
        with QSignalBlocker(self.mascot_action):
            self.mascot_action.setChecked(on)

    def set_paused_ui(self, paused: bool) -> None:
        self._paused = paused
        self.pause_action.setText("&Resume tracking" if paused else "&Pause tracking")

    def set_break_text(self, text: str) -> None:
        self._break_text.setText(text)
        self._break_text.setVisible(bool(text))
        self._header_labels.invalidate()
        self._header_widget.layout().invalidate()
        self._header_widget.setFixedHeight(self._header_widget.layout().sizeHint().height())

    def set_controls(self, calibrating: bool, suspended: bool) -> None:
        self.cal_action.setText("View &calibration…" if calibrating else "&Calibrate…")
        self.cal_action.setEnabled(not suspended)
        self.pause_action.setEnabled(not suspended)

    # ------------------------------------------------------------------
    def set_state(self, key: str, detail: str) -> None:
        color = STATE_COLORS.get(key, STATE_COLORS["uncalibrated"])
        if key != self._state_key:
            self.icon.setIcon(shrimp_icon(color))
            self._header_shrimp.setPixmap(shrimp_pixmap_sized(22, color))
            self._state_key = key
        label = STATE_LABELS.get(key, "Finding your posture")
        self._header_text.setText(label)
        self.icon.setToolTip(f"Unshrimp · {label}")

    def toast(self, title: str, body: str, seconds: int = 6) -> None:
        self.icon.showMessage(title, body, QSystemTrayIcon.Information, seconds * 1000)
