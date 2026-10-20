"""Camera-free appearance samples; no controller or saved settings writes."""
import math
import time

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from . import assets
from .mascot import TEXT_SIZES, paint_text_cue
from .shrimp import paint_shrimp
from .theme import SHRIMP


class ShrimpPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(150)
        self.setMinimumWidth(240)
        self.setAccessibleName("Floating cue sample preview")
        self.enabled = True
        self.style = "shrimp"
        self.scale = 1.
        self.opacity = .87
        self.position = "center"
        self.bob = True
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.update)

    def configure(self, cfg):
        self.enabled = cfg.get("mascot_enabled", True)
        self.style = cfg.get("mascot_style", "shrimp")
        sizes = TEXT_SIZES if self.style == "text" else {"s": .75, "m": 1., "l": 1.3}
        self.scale = sizes.get(cfg.get("mascot_size"), 1.)
        self.opacity = cfg.get("mascot_opacity", .87)
        self.position = cfg.get("mascot_position", "center")
        self.bob = cfg.get("mascot_bob", True) and not cfg.get("reduce_motion", False)
        self.setAccessibleDescription("Sample only; no camera. " +
                                      ("Floating cue hidden." if not self.enabled else
                                       f"{self.style} cue, {cfg.get('mascot_size', 'm')} size, "
                                       f"{round(self.opacity * 100)}% opacity."))
        self._sync_timer()
        self.update()

    def _sync_timer(self):
        if self.isVisible() and self.enabled and self.bob:
            self.timer.start()
        else:
            self.timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base())
        if not self.enabled:
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignCenter, "Floating cue is hidden")
            return
        if self.style == "text":
            scale = min(self.scale * .65, (self.width() - 24) / 220,
                        (self.height() - 20) / 44)
            cue_width = round(220 * scale)
            cue_height = round(44 * scale)
            x = (12 if self.position in ("left", "top_left") else self.width() - cue_width - 12
                 if self.position in ("right", "top_right") else (self.width() - cue_width) // 2)
            bob = 3 * math.sin(time.monotonic() * 2 * math.pi / 3) if self.bob else 0
            y = (10 if self.position.startswith("top_") else
                 self.height() - cue_height - 10 if self.position in ("left", "center", "right") else
                 (self.height() - cue_height) / 2) + bob
            painter.setOpacity(self.opacity * .87)
            paint_text_cue(painter, QRectF(x, y, cue_width, cue_height), scale)
            return
        width = min(round(145 * self.scale), self.width() - 24)
        art = assets.shrimp_mascot(width, round(width * .62))
        art_width = art.width() if art is not None else width
        art_height = art.height() if art is not None else round(width * .62)
        x = (12 if self.position in ("left", "top_left") else self.width() - art_width - 12
             if self.position in ("right", "top_right") else (self.width() - art_width) // 2)
        bob = 3 * math.sin(time.monotonic() * 2 * math.pi / 3) if self.bob else 0
        painter.setOpacity(self.opacity * .87)
        y = round((10 if self.position.startswith("top_") else
                   self.height() - art_height - 10 if self.position in ("left", "center", "right") else
                   (self.height() - art_height) / 2) + bob)
        if art is not None:
            painter.drawPixmap(x, y, art)
        else:
            paint_shrimp(painter, QRectF(x, y, art_width, art_height), SHRIMP)
