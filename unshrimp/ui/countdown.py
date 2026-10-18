"""Shrimp progress driven by usable calibration time, never by animation time."""
import math
import time

from PySide6.QtCore import Qt, QRectF, QTimer, QEasingCurve
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from . import theme
from .tray import shrimp_icon
from ..core.calibration import TALL_S, NORMAL_S, HUNCH_S, VERIFY_S


class ShrimpCountdown(QWidget):
    SLOT_COUNT = math.ceil(max(TALL_S, NORMAL_S, HUNCH_S, VERIFY_S))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setStyleSheet("font-size: 16px;")
        self.activity = None
        self.remaining = 0
        self.slots = self.SLOT_COUNT
        self.used_slots = 0
        self.reduce_motion = False
        self._fade_from = 0
        self._changed_at = time.monotonic()
        self._wave_started_at = self._changed_at
        self._preparing = False
        self._art = {color: shrimp_icon(color).pixmap(64, 64)
                     for color in (theme.INFO, theme.SHRIMP, theme.MUTED)}
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)

    def set_progress(self, result):
        if result.activity is None:
            self.clear()
            return
        previous = (self.activity, self.used_slots, self.remaining)
        self.activity = result.activity
        self.used_slots = min(self.slots, math.ceil(result.pose_duration_s))
        self.remaining = max(0, math.ceil(result.duration_s - result.elapsed_s))
        self._preparing = result.duration_s < result.pose_duration_s
        if previous != (self.activity, self.used_slots, self.remaining):
            self._fade_from = (previous[2] if previous[0] == self.activity == "capturing"
                               and previous[1] == self.used_slots else self.remaining)
            self._changed_at = time.monotonic()
        if previous[:2] != (self.activity, self.used_slots):
            self._wave_started_at = time.monotonic()
        self.show()
        self.setAccessibleName(f"Calibration {self.activity or 'progress'}")
        self.setAccessibleDescription(f"{self.remaining} seconds remaining")
        self._sync_timer()
        self.update()

    def pause(self):
        self.activity = "paused"
        self.timer.stop()
        self.setAccessibleName("Calibration progress paused")
        self.update()

    def clear(self):
        self.activity = None
        self.remaining = self.used_slots = self._fade_from = 0
        self._preparing = False
        self.timer.stop()
        self.setAccessibleName("Calibration progress")
        self.setAccessibleDescription("Waiting to collect samples")
        self.show()
        self.update()

    def apply_theme(self):
        self._art = {color: shrimp_icon(color).pixmap(64, 64)
                     for color in (theme.INFO, theme.SHRIMP, theme.MUTED)}
        self.update()

    def set_reduced_motion(self, enabled):
        self.reduce_motion = enabled
        self._sync_timer()
        self.update()

    def _sync_timer(self):
        animated = self.activity == "preparing" or (
            self.activity == "capturing" and self._fade_from > self.remaining
            and time.monotonic() - self._changed_at < .18)
        if animated and self.isVisible() and not self.reduce_motion:
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self):
        self._sync_timer()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        seconds = ("—" if self.activity is None else
                   "Checking…" if self.activity == "checking" else
                   "Paused" if self.activity == "paused" and not self.used_slots else f"{self.remaining}s")
        text_width = self.fontMetrics().horizontalAdvance("Checking…") + 12
        slot_width = min(30., max(1., (self.width() - text_width - 8) / self.slots))
        side = min(26., slot_width - 2)
        age = time.monotonic() - self._changed_at
        wave_age = time.monotonic() - self._wave_started_at
        peak = max(0, self.used_slots - 1) * (0.5 - 0.5 * math.cos(wave_age * 2 * math.pi / 1.6))
        color = (theme.INFO if self.activity == "preparing" else
                 theme.MUTED if self.activity == "paused" else theme.SHRIMP)
        fade = QEasingCurve(QEasingCurve.OutCubic).valueForProgress(min(1., age / .18))
        for index in range(self.slots):
            target = QRectF(index * slot_width, (self.height() - side) / 2, side, side)
            neutral = self._art[theme.MUTED]
            painter.setOpacity(.45)
            painter.drawPixmap(target, neutral, QRectF(neutral.rect()))
            if index >= self.used_slots:
                continue
            opacity = 1. if index < self.remaining or self._preparing else 0.
            if self.activity == "preparing" and not self.reduce_motion:
                opacity = .25 + .75 * max(0., 1 - abs(index - peak) / 2)
            elif (not self.reduce_motion and self.activity == "capturing"
                  and self.remaining <= index < self._fade_from):
                opacity = 1. - fade
            painter.setOpacity(opacity)
            painter.drawPixmap(target,
                               self._art[color], QRectF(self._art[color].rect()))
        painter.setOpacity(1.)
        painter.setPen(self.palette().text().color())
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(self.width() - text_width, 0, text_width, self.height()),
                         Qt.AlignRight | Qt.AlignVCenter, seconds)
