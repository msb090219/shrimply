"""Compact posture companion with stable proportions and ordinary Qt controls."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, Signal, QRectF, QTimer, QPropertyAnimation
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen, QPixmap, QIcon, QPolygon
from PySide6.QtWidgets import QWidget, QLabel, QBoxLayout, QFrame, QGraphicsOpacityEffect

from . import theme
from .tray import shrimp_icon
from .icons import IconButton
from .macos_windows import join_fullscreen_spaces


class ShrimpMeter(QWidget):
    """Fixed green-to-red segments, with neutral shrimp for unused readings."""

    COLORS = (theme.GOOD, "#45bf50", "#6cba42", "#95b534", "#b9af26",
              "#dda617", theme.DRIFT, "#f4801e", "#f26331", theme.BAD)

    def __init__(self):
        super().__init__()
        self.setFixedSize(160, 28)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lit_count = 0
        self.orientation = "horizontal"
        self.cell = 16
        self.cross_size = 28
        self._art = {}
        self.setAccessibleName("Posture deviation meter")

    def set_reading(self, level):
        # The last segment turns red at the same threshold as Adjust posture.
        self.lit_count = (0 if level is None else
                          1 + int(min(1., max(0., level / 1.5)) * (len(self.COLORS) - 1)))
        self.setAccessibleDescription(f"{self.lit_count} of {len(self.COLORS)} shrimp lit; more means greater posture deviation.")
        self.update()

    def set_size(self, cell, height):
        self.cell, self.cross_size = cell, height
        if self.orientation == "vertical":
            self.setFixedSize(height, cell * len(self.COLORS))
        else:
            self.setFixedSize(cell * len(self.COLORS), height)
        self.update()

    def set_orientation(self, orientation):
        self.orientation = orientation if orientation == "vertical" else "horizontal"
        self.set_size(self.cell, self.cross_size)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        for index, color in enumerate(self.COLORS):
            selected = index < self.lit_count
            color = color if selected else theme.MUTED
            if color not in self._art:
                self._art[color] = shrimp_icon(color).pixmap(64, 64)
            art = self._art[color]
            painter.setOpacity(1. if selected else .45)
            if self.orientation == "vertical":
                cell = self.height() / len(self.COLORS)
                target = QRectF((self.width() - cell) / 2, self.height() - (index + 1) * cell, cell, cell - 1)
            else:
                cell = self.width() / len(self.COLORS)
                target = QRectF(index * cell, (self.height() - cell) / 2, cell - 1, cell)
            painter.drawPixmap(target, art, QRectF(art.rect()))


class FeedbackLabel(QLabel):
    """A small translucent backing follows the text over light or dark desktops."""
    def paintEvent(self, event):
        if self.text():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            fill, outline = theme.caption_colors()
            width = min(self.fontMetrics().horizontalAdvance(self.text()) + 20, self.width() - 2)
            rect = QRectF((self.width() - width) / 2, 1, width, self.height() - 2)
            painter.setPen(QPen(outline, 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 6, 6)
            painter.end()
        super().paintEvent(event)


class Hud(QWidget):
    doubleClicked = Signal()
    pause_requested = Signal()
    moved = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.setWindowTitle("Shrimply posture indicator")
        self.setCursor(Qt.OpenHandCursor)
        self.setAccessibleName("Shrimply posture indicator")
        self.level = None
        self.mode = "uncalibrated"
        self.text = "Calibration required"
        self._drag_off = None
        self._menu = None
        self._icons = {}
        self.compact = False
        self._break_prompt_visible = False
        self._caption_active = False
        self._caption_text = ""
        self.size_key = "m"
        self.orientation = "horizontal"
        self._height = theme.HUD_HEIGHT
        self.setStyleSheet(f"""
            QToolButton {{ border: 1px solid transparent; border-radius: 4px; padding: 0; }}
            QToolButton:hover {{ background: palette(midlight); }}
            QToolButton[keyboardFocus="true"] {{ border-color: {theme.SHRIMP}; }}
        """)
        root = QBoxLayout(QBoxLayout.TopToBottom, self)
        root.setContentsMargins(0, 0, 0, 3)
        root.setSpacing(4)
        self.bar = QWidget()
        self.bar.setFixedHeight(self._height)
        root.addWidget(self.bar)
        layout = QBoxLayout(QBoxLayout.LeftToRight, self.bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)
        self.shrimp = ShrimpMeter()
        layout.addWidget(self.shrimp, 0, Qt.AlignCenter)
        layout.addSpacing(6)
        self.label = FeedbackLabel()
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.label.setStyleSheet("font-size: 12px; color: palette(text); background: transparent;")
        self.label.setAlignment(Qt.AlignCenter)
        self._label_opacity = QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self._label_opacity)
        self._caption_timer = QTimer(self)
        self._caption_timer.setSingleShot(True)
        self._caption_timer.timeout.connect(self._fade_caption)
        self._caption_fade = QPropertyAnimation(self._label_opacity, b"opacity", self)
        self._caption_fade.setDuration(250)
        self._caption_fade.finished.connect(self._finish_caption)
        root.addWidget(self.label, 0, Qt.AlignHCenter)
        controls = QWidget()
        controls_layout = QBoxLayout(QBoxLayout.LeftToRight, controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)
        self.divider = QFrame()
        self.divider.setFixedSize(1, 18)
        self.divider.setStyleSheet("background: palette(mid);")
        controls_layout.addWidget(self.divider)
        self.pause_button = self._button("Pause tracking", "pause")
        self.pause_button.clicked.connect(self.pause_requested.emit)
        self.menu_button = self._button("More controls", "menu")
        self.menu_button.clicked.connect(self._show_menu)
        for button in (self.pause_button, self.menu_button):
            controls_layout.addWidget(button)
        layout.addWidget(controls, 0, Qt.AlignCenter)
        self.setFixedWidth(layout.sizeHint().width())
        self._refresh()

    def _button(self, name, icon):
        button = IconButton()
        button.setFixedSize(theme.COMPACT_CONTROL_HEIGHT, theme.COMPACT_CONTROL_HEIGHT)
        button.setCursor(Qt.PointingHandCursor)
        button.setIcon(self._icon(icon))
        button.setIconSize(QSize(18, 18))
        button.setToolTip(name)
        button.setAccessibleName(name)
        button.setFocusPolicy(Qt.StrongFocus)
        return button

    def _icon(self, kind):
        color = self.palette().text().color()
        ratio = self.devicePixelRatioF()
        key = (kind, color.name(), ratio)
        if key not in self._icons:
            pixmap = QPixmap(round(16 * ratio), round(16 * ratio))
            pixmap.setDevicePixelRatio(ratio)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(color, 1.5))
            if kind == "pause":
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(4, 3, 3, 10, .5, .5)
                painter.drawRoundedRect(10, 3, 3, 10, .5, .5)
            else:
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                if kind == "play":
                    painter.drawPolygon(QPolygon([QPoint(5, 3), QPoint(12, 8), QPoint(5, 13)]))
                elif kind == "menu":
                    for x in (3, 8, 13):
                        painter.drawEllipse(QPoint(x, 8), 1, 1)
            painter.end()
            self._icons[key] = QIcon(pixmap)
        return self._icons[key]

    def set_context_menu(self, menu):
        self._menu = menu

    def _show_menu(self):
        if self._menu is not None:
            self._menu.popup(self.menu_button.mapToGlobal(QPoint(0, self.menu_button.height())))

    def contextMenuEvent(self, event):
        if self._menu is not None:
            self._menu.popup(event.globalPos())

    def set_live(self, level: float | None, text: str):
        self.mode, self.level = "live", level
        self.text = ("Finding posture" if level is None else
                     "Adjust posture" if level >= 1.5 else
                     "Posture drifting" if level >= 1.0 else "Sitting comfortably")
        if level is None or level < 1.5:
            self._finish_caption()
        self._refresh()

    def set_status(self, mode: str, text: str):
        if mode != "live":
            self._finish_caption()
        self.mode, self.level = mode, None
        self.text = {
            "uncalibrated": "Calibration required", "away": "Away from the desk",
            "paused": "Stopping camera" if text == "stopping camera" else "Tracking paused",
            "cam_error": "Camera unavailable", "calibrating": f"Calibration · {text}",
        }.get(mode, text)
        self._refresh()

    def show_feedback(self, text: str):
        if self.mode != "live" or self.compact or self._break_prompt_visible:
            return
        self._caption_fade.stop()
        self._label_opacity.setOpacity(1)
        self._caption_text = text
        self._caption_active = True
        self._caption_timer.start(3000)
        self._refresh()

    def _fade_caption(self):
        self._caption_fade.setStartValue(1)
        self._caption_fade.setEndValue(0)
        self._caption_fade.start()

    def _finish_caption(self):
        self._caption_timer.stop()
        self._caption_fade.stop()
        if self._caption_active:
            self._caption_active = False
            self._label_opacity.setOpacity(1)
            self._refresh()

    def set_break_prompt_visible(self, visible: bool):
        if visible:
            self._finish_caption()
        if self._break_prompt_visible != visible:
            self._break_prompt_visible = visible
            self._refresh()

    def set_compact(self, compact):
        if compact:
            self._finish_caption()
        self.compact = compact
        self._refresh()

    def set_size(self, key):
        self.size_key = key if key in ("s", "m", "l") else "m"
        cell, height, control, font, margin = {
            "s": (14, 36, 28, 11, 8), "m": (16, 40, 28, 12, 12),
            "l": (20, 48, 32, 14, 14),
        }[self.size_key]
        self._height = height
        self.shrimp.set_size(cell, control)
        self.bar.setFixedHeight(height)
        self.label.setStyleSheet(f"font-size: {font}px; color: palette(text); background: transparent;")
        if self.orientation == "vertical":
            self.bar.layout().setContentsMargins(8, 8, 8, 8)
            self.bar.layout().itemAt(1).changeSize(0, 8)
        else:
            self.bar.layout().setContentsMargins(margin, (height - control) // 2,
                                                margin, (height - control) // 2)
            self.bar.layout().itemAt(1).changeSize(margin - 6, 0)
        for button in (self.pause_button, self.menu_button):
            button.setFixedSize(control, control)
            button.setIconSize(QSize(22, 22) if self.size_key == "l" else QSize(18, 18))
        self._refresh()

    def set_orientation(self, orientation):
        orientation = "vertical" if orientation == "vertical" else "horizontal"
        if orientation == "vertical" and self.isWindow() and not self.label.isWindow():
            self.layout().removeWidget(self.label)
            self.label.setParent(self, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint |
                                 Qt.WindowTransparentForInput)
            self.label.setAttribute(Qt.WA_TranslucentBackground)
            self.label.setAttribute(Qt.WA_ShowWithoutActivating)
            self.label.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
            self.label.setWindowOpacity(self.windowOpacity())
        elif orientation == "horizontal" and self.label.isWindow():
            self.label.hide()
            self.label.setParent(self, Qt.Widget)
            self.layout().addWidget(self.label, 0, Qt.AlignHCenter)
        self.orientation = orientation
        self.shrimp.set_orientation(orientation)
        self.bar.layout().itemAt(2).widget().layout().setDirection(
            QBoxLayout.TopToBottom if orientation == "vertical" else QBoxLayout.LeftToRight)
        self.bar.layout().setDirection(QBoxLayout.TopToBottom if orientation == "vertical" else QBoxLayout.LeftToRight)
        self.layout().setDirection(QBoxLayout.LeftToRight if orientation == "vertical" and not self.label.isWindow()
                                   else QBoxLayout.TopToBottom)
        if not self.label.isWindow():
            self.layout().setAlignment(self.label, Qt.AlignVCenter if orientation == "vertical" else Qt.AlignHCenter)
        self.divider.setVisible(orientation == "horizontal")
        self.set_size(self.size_key)

    def setWindowOpacity(self, opacity):
        super().setWindowOpacity(opacity)
        if self.label.isWindow():
            self.label.setWindowOpacity(opacity)

    def _refresh(self):
        label_text = (self._caption_text if self.mode == "live" and self._caption_active else
                      "Calibrating" if self.mode == "calibrating" else self.text)
        self.label.ensurePolished()
        metrics = QFontMetrics(self.label.font())
        self.bar.layout().itemAt(2).widget().layout().invalidate()
        self.bar.layout().itemAt(2).widget().updateGeometry()
        self.bar.layout().invalidate()
        hint = self.bar.layout().sizeHint()
        width = hint.width()
        bar_height = hint.height() if self.orientation == "vertical" else self._height
        self.bar.setFixedSize(width, bar_height)
        self.label.setFixedSize(160 if self.orientation == "vertical" else width - 8, metrics.height() + 10)
        self.label.setText(label_text if metrics.horizontalAdvance(label_text) <= self.label.width() - 24 else
                           metrics.elidedText(label_text, Qt.ElideRight, self.label.width() - 24))
        needs_explanation = (self.mode in ("cam_error", "uncalibrated", "calibrating",
                                                "paused", "preview", "idle")
                             or (self.mode == "live" and self.level is None))
        caption_visible = (not self._break_prompt_visible and
                           (needs_explanation or (self._caption_active and not self.compact)))
        caption_was_visible = self.label.isVisible()
        self.label.setVisible(caption_visible and (self.isVisible() or not self.label.isWindow()))
        if self.label.isWindow() and self.label.isVisible() and not caption_was_visible:
            join_fullscreen_spaces(self.label)
        floating_caption = self.orientation == "vertical" and self.label.isWindow()
        self.layout().setContentsMargins(0, 0, 0, 3 if caption_visible and not floating_caption else 0)
        self.layout().invalidate()
        if self.orientation == "vertical":
            self.setFixedSize(width if floating_caption or not caption_visible else width + 4 + self.label.width(),
                              bar_height)
        else:
            self.setFixedSize(width, bar_height if not caption_visible else
                              bar_height + 4 + self.label.height() + 3)
        screen = self.screen()
        if screen is not None and self.isWindow():
            area = screen.availableGeometry()
            self.move(max(area.left(), min(self.x(), area.right() - self.width() + 1)),
                      max(area.top(), min(self.y(), area.bottom() - self.height() + 1)))
        self._position_caption()
        self.setToolTip(self.text)
        self.setAccessibleDescription(self.text)
        self.shrimp.set_reading(self.level if self.mode == "live" else None)
        paused = self.mode in ("paused", "preview")
        name = "Resume tracking" if paused else "Pause tracking"
        if self.mode == "calibrating":
            name = "Cancel calibration and pause tracking"
        self.pause_button.setToolTip(name)
        self.pause_button.setAccessibleName(name)
        self.pause_button.setIcon(self._icon("play" if paused else "pause"))
        self.update()

    def apply_theme(self):
        self._icons.clear()
        self.menu_button.setIcon(self._icon("menu"))
        self.shrimp._art.clear()
        font = {"s": 11, "m": 12, "l": 14}[self.size_key]
        self.label.setStyleSheet(f"font-size: {font}px; color: palette(text); background: transparent;")
        self._refresh()
        self.shrimp.update()

    def moveEvent(self, event):
        self._position_caption()
        self.moved.emit()

    def showEvent(self, event):
        super().showEvent(event)
        join_fullscreen_spaces(self)
        if self.label.isWindow():
            self._refresh()

    def hideEvent(self, event):
        if self.label.isWindow():
            self.label.hide()
        super().hideEvent(event)

    def _position_caption(self):
        if not self.label.isWindow() or self.label.isHidden():
            return
        area = self.screen().availableGeometry()
        bar = self.bar.mapToGlobal(QPoint())
        x = bar.x() + (self.bar.width() - self.label.width()) // 2
        y = bar.y() + self.bar.height() + 4
        if y + self.label.height() > area.bottom() + 1:
            y = bar.y() - self.label.height() - 4
        self.label.move(max(area.left(), min(x, area.right() - self.label.width() + 1)),
                        max(area.top(), y))

    def resizeEvent(self, event):
        self.moved.emit()
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_off = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_off is not None:
            self.move(event.globalPosition().toPoint() - self._drag_off)

    def mouseReleaseEvent(self, event):
        self._drag_off = None
        self.setCursor(Qt.OpenHandCursor)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(self.palette().mid().color(), 1))
        background = QColor(self.palette().window().color())
        background.setAlpha(255)
        painter.setBrush(background)
        painter.drawRoundedRect(QRectF(1, 1, self.bar.width() - 2, self.bar.height() - 2), theme.R_HUD, theme.R_HUD)
