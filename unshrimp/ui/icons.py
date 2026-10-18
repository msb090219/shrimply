"""Small original line icons, rendered at multiple sizes for desktop scaling."""
import math

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QToolButton


class IconButton(QToolButton):
    """Keep a keyboard focus ring without leaving a border after mouse clicks."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("keyboardFocus", False)

    def _focus_ring(self, visible):
        self.setProperty("keyboardFocus", visible)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def focusInEvent(self, event):
        self._focus_ring(event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason,
                                           Qt.ShortcutFocusReason, Qt.OtherFocusReason))
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._focus_ring(False)
        super().focusOutEvent(event)


def _render_icon(color, draw):
    icon = QIcon()
    for size in (18, 24, 36, 48, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(size / 24, size / 24)
        pen = QPen(color, 1.8)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        draw(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def settings_icon(color):
    path = QPainterPath()
    for tooth in range(8):
        for offset, radius in ((-16, 8), (-12, 10), (12, 10), (16, 8)):
            angle = math.radians(tooth * 45 + offset)
            x, y = 12 + radius * math.cos(angle), 12 + radius * math.sin(angle)
            if tooth == 0 and offset == -16:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
    path.closeSubpath()
    def draw(painter):
        painter.drawPath(path)
        painter.drawEllipse(8.5, 8.5, 7., 7.)
    return _render_icon(color, draw)


def tracking_icon(color, paused):
    def draw(painter):
        if paused:
            path = QPainterPath()
            path.moveTo(8, 5)
            path.lineTo(19, 12)
            path.lineTo(8, 19)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            painter.drawLine(8, 5, 8, 19)
            painter.drawLine(16, 5, 16, 19)
    return _render_icon(color, draw)


def refresh_icon(color):
    def draw(painter):
        painter.drawArc(QRectF(4, 4, 16, 16), 45 * 16, 285 * 16)
        path = QPainterPath()
        path.moveTo(19.5, 20.5)
        path.lineTo(19, 16)
        path.lineTo(14.5, 18)
        painter.drawPath(path)
    return _render_icon(color, draw)
