"""The mascot — a very large translucent shrimp that rises as you slouch.

Performance model (v1.1.2): the OS window is **stationary** — positioned
once, bottom-center, sized to fit the shrimp at maximum rise and bob.
All animation (fade, rise, bob) happens *inside* the window via
paint-only updates at 30 fps. Moving translucent layered windows is what
made the original bob feel laggy; repainting a stationary one is cheap.

Shown after sustained bad posture, faint while recovering through drifting,
near-opaque (gently bobbing) when hunched. Click-through, never takes focus, never appears
during calibration/pause/away.
"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import QRectF, Qt, QTimer, QObject
from PySide6.QtGui import QColor, QPainter, QGuiApplication
from PySide6.QtWidgets import QWidget

from . import assets
from .shrimp import paint_shrimp
from .theme import SHRIMP

_W = 460
_H = 420  # room for the shrimp + max lift + bob, bottom-anchored
_BOTTOM_MARGIN = 30
_BOB_PX = 7
_BOB_PERIOD_S = 3.0
_EASE = 0.09  # per 33ms tick — a gradual entrance and exit
_BAD_HOLD_S = 2.0
_BAD_GAP_S = 1.5
_RECOVERY_HOLD_S = 3.0
_BAD_THRESHOLD = 1.5

_SIZES = {"s": 0.75, "m": 1.0, "l": 1.3}
TEXT_SIZES = {"s": 0.7, "m": 1.0, "l": 2.0}


def paint_text_cue(painter: QPainter, rect: QRectF, scale: float = 1.0) -> None:
    """The same compact cue is used by the live overlay and Settings preview."""
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(32, 34, 38, 235))
    painter.drawRoundedRect(rect, 11 * scale, 11 * scale)
    font = painter.font()
    font.setPixelSize(max(11, round(14 * scale)))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(rect, Qt.AlignCenter, "Don't get shrimped.")


def mascot_params(dev: float | None, bad_threshold: float = _BAD_THRESHOLD) -> tuple[float, float]:
    """Pure mapping: deviation → (opacity 0..1, lift_px 0..110).

    Hidden below dev 1.0; near-opaque at the Bad threshold. Rise can
    continue with deeper slouching.
    """
    if dev is None or dev < 1.0:
        return (0.0, 0.0)
    opacity = min((dev - 1.0) / max(bad_threshold - 1.0, .01), 1.0)
    lift = min((dev - 1.0) / 1.5, 1.0)
    return (round(0.15 + 0.72 * opacity, 3), round(110.0 * lift, 1))


class MascotWindow(QWidget):
    """Owns paint + animation only; the app feeds it deviations and options."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput  # click-through
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # never steal focus
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.setFixedSize(_W, _H)

        # options (set via set_options from Settings)
        self._max_opacity = 0.87
        self._scale = 1.0
        self._bob_on = True
        self._entrance = "rise"
        self._style = "shrimp"
        self._bad_threshold = _BAD_THRESHOLD
        self.reduce_motion = False
        self.position = "center"
        self.screen_name = ""
        self.target_screen = None
        self._art = None  # pre-scaled mascot art — the paint loop only blits

        self._cur = 0.0  # eased opacity
        self._cur_lift = 0.0  # eased rise, px
        self._target = (0.0, 0.0)
        self._t0 = time.monotonic()

        self._timer = QTimer(self)
        self._timer.setInterval(33)  # 30 fps paint-only animation
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------
    def set_options(self, max_opacity: float, size_key: str, bob: bool,
                    entrance: str = "rise", bad_threshold: float = _BAD_THRESHOLD,
                    style: str = "shrimp") -> None:
        self._max_opacity = max(0.2, min(1.0, max_opacity))
        self._scale = _SIZES.get(size_key, 1.0)
        self._bob_on = bob
        self._entrance = entrance if entrance in ("rise", "fade", "instant") else "rise"
        self._style = style if style in ("shrimp", "text") else "shrimp"
        self._bad_threshold = bad_threshold
        if self._style == "text":
            self._scale = TEXT_SIZES.get(size_key, 1.0)
            if self.target_screen is not None:
                area = self.target_screen.availableGeometry()
                self._scale = min(self._scale,
                                  max(1, area.width() - 48) / 220,
                                  max(1, area.height() - 110 - _BOB_PX
                                      - 2 * _BOTTOM_MARGIN - 12) / 44)
            self._art = None
            self.setFixedSize(round(220 * self._scale),
                              round(44 * self._scale) + 110 + _BOB_PX + _BOTTOM_MARGIN + 12)
            if self.isVisible():
                self._anchor()
                self.update()
            return
        # precompute the art at draw size — the 30fps paint loop must never
        # load from disk or rescale
        w = int(_W * 0.92 * self._scale)
        screen = self.target_screen
        if screen is not None:
            area = screen.availableGeometry()
            w = min(w, max(1, area.width() - 48),
                    max(1, int((area.height() - 110 - _BOB_PX - 2 * _BOTTOM_MARGIN - 12) / .62)))
        self._art = assets.shrimp_mascot(w, int(w * 0.62))
        self.setFixedSize(w + 24, int(w * .62) + 110 + _BOB_PX + _BOTTOM_MARGIN + 12)
        if self.isVisible():
            self._anchor()
            self.update()

    def set_level(self, dev: float | None) -> None:
        """Feed the current deviation (None = fade out / hide)."""
        op, lift = mascot_params(dev, self._bad_threshold)
        self._target = (op * self._max_opacity if op else 0.0,
                        lift if self._entrance == "rise" and not self.reduce_motion else 0.0)
        if self._target[0] > 0 and not self.isVisible():
            self._anchor()
            self.show()
            self.raise_()
        if (self._target[0] > 0 or self._cur > 0.01) and not self._timer.isActive():
            self._timer.start()

    def force_hide(self) -> None:
        self._target = (0.0, 0.0)
        self._cur = 0.0
        self._cur_lift = 0.0
        self._timer.stop()
        self.hide()

    # ------------------------------------------------------------------
    def _anchor(self) -> None:
        """Place the window once at the selected point of the current screen."""
        screen = self.target_screen or next((s for s in QGuiApplication.screens() if s.name() == self.screen_name),
                      QGuiApplication.primaryScreen())
        if screen is None:
            return
        g = screen.availableGeometry()
        x = (g.left() + 24 if self.position in ("left", "top_left") else
             g.right() - self.width() - 23 if self.position in ("right", "top_right") else
             g.center().x() - self.width() // 2)
        y = (g.top() + 24 if self.position.startswith("top_") else
             g.center().y() - self.height() // 2 if self.position == "middle" else
             g.bottom() - self.height() - _BOTTOM_MARGIN)
        self.move(max(g.left(), min(x, g.right() - self.width() + 1)),
                  max(g.top(), min(y, g.bottom() - self.height() + 1)))

    def _tick(self) -> None:
        t_op, t_lift = self._target
        self._cur = (t_op if self._entrance == "instant" and t_op > 0
                     else self._cur + (t_op - self._cur) * _EASE)
        self._cur_lift = (self._cur_lift + (t_lift - self._cur_lift) * _EASE
                          if self._entrance == "rise" and not self.reduce_motion else 0.0)
        if t_op == 0.0 and self._cur < 0.02:
            self._timer.stop()
            self.hide()
            return
        if (self.reduce_motion or not self._bob_on) and abs(t_op - self._cur) < .01 and abs(t_lift - self._cur_lift) < 1:
            self._cur = t_op
            self._timer.stop()
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, _):
        if self._cur <= 0.01:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(self._cur)

        if self._style == "text":
            bob = (_BOB_PX * (0.5 + 0.5 * math.sin(
                2 * math.pi * (time.monotonic() - self._t0) / _BOB_PERIOD_S
            )) if self._bob_on else 0.0)
            rect = QRectF(0, self.height() - _BOTTOM_MARGIN - round(44 * self._scale)
                          - self._cur_lift - bob,
                          self.width(), round(44 * self._scale))
            paint_text_cue(p, rect, self._scale)
            return

        art = self._art if self._art is not None else assets.shrimp_mascot(
            int(_W * 0.92 * self._scale), int(_W * 0.92 * self._scale * 0.62)
        )
        bob = (
            _BOB_PX * (0.5 + 0.5 * math.sin(
                2 * math.pi * (time.monotonic() - self._t0) / _BOB_PERIOD_S
            ))
            if self._bob_on
            else 0.0
        )

        if art is not None:
            aw, ah = art.width(), art.height()
            x = (self.width() - aw) // 2
            y = self.height() - _BOTTOM_MARGIN - ah - self._cur_lift - bob
            # ground shadow
            p.setOpacity(self._cur * 0.22)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 90))
            p.drawEllipse(QRectF(self.width() * 0.28, self.height() - _BOTTOM_MARGIN - 16, self.width() * 0.44, 14))
            p.setOpacity(self._cur)
            p.drawPixmap(x, int(y), art)
        else:
            sw = self.width() - 24
            sh = sw * 0.62
            rect = QRectF(
                (self.width() - sw) / 2,
                self.height() - _BOTTOM_MARGIN - sh - self._cur_lift - bob,
                sw,
                sh,
            )
            p.setOpacity(self._cur * 0.22)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 90))
            p.drawEllipse(QRectF(self.width() * 0.28, self.height() - _BOTTOM_MARGIN - 16, self.width() * 0.44, 14))
            p.setOpacity(self._cur)
            paint_shrimp(p, rect, QColor(SHRIMP))


class MascotGroup(QObject):
    """Share one posture value across the overlays for the selected displays."""
    def __init__(self):
        super().__init__(QGuiApplication.instance())
        self.reduce_motion = False
        self.position = "center"
        self.screen_name = ""
        self.windows = {}
        self._options = (.87, "m", True, "rise", _BAD_THRESHOLD, "shrimp")
        self._level = None
        self._bad_since = None
        self._last_bad = None
        self._recover_since = None
        self._active = False
        self.bad_hold_s = _BAD_HOLD_S
        self.recovery_hold_s = _RECOVERY_HOLD_S
        self._t0 = time.monotonic()
        app = QGuiApplication.instance()
        app.screenAdded.connect(self._screen_added)
        app.screenRemoved.connect(self._screen_removed)
        for screen in app.screens():
            screen.availableGeometryChanged.connect(self._sync)

    def _screen_added(self, screen):
        screen.availableGeometryChanged.connect(self._sync)
        self._sync()

    def _screen_removed(self, screen):
        self._sync(excluded=screen)

    def set_options(self, max_opacity, size_key, bob, entrance="rise", bad_threshold=_BAD_THRESHOLD,
                    style="shrimp"):
        self._options = (max_opacity, size_key, bob, entrance, bad_threshold, style)
        self._sync()

    def _sync(self, *_, excluded=None):
        screens = [screen for screen in QGuiApplication.screens() if screen is not excluded]
        primary = QGuiApplication.primaryScreen()
        if primary not in screens:
            primary = screens[0] if screens else None
        selected = screens if self.screen_name == "*" else [next(
            (screen for screen in screens if screen.name() == self.screen_name),
            primary)]
        selected = [screen for screen in selected if screen is not None]
        for screen in list(self.windows):
            if screen not in selected:
                window = self.windows.pop(screen)
                window.force_hide()
                window.deleteLater()
        for screen in selected:
            if screen not in self.windows:
                self.windows[screen] = MascotWindow()
                self.windows[screen]._t0 = self._t0
            window = self.windows[screen]
            window.target_screen = screen
            window.position = self.position
            window.reduce_motion = self.reduce_motion
            window.set_options(*self._options)
            window._anchor()
            window.set_level(self._level)

    def set_level(self, dev, *, bad: bool, now=None):
        now = time.monotonic() if now is None else now
        if dev is None:
            self.force_hide()
            return
        if self._active:
            if bad:
                self._recover_since = None
            elif dev < 1.0:
                if self._recover_since is None:
                    self._recover_since = now
                if now - self._recover_since >= self.recovery_hold_s:
                    self._active = False
                    self._bad_since = None
                    self._last_bad = None
            else:
                self._recover_since = None
        else:
            if bad:
                if self._last_bad is None or now - self._last_bad > _BAD_GAP_S:
                    self._bad_since = now
                self._last_bad = now
                if now - self._bad_since >= self.bad_hold_s:
                    self._active = True
                    self._recover_since = None
            elif self._last_bad is not None and now - self._last_bad > _BAD_GAP_S:
                self._bad_since = None
                self._last_bad = None
        self._level = (dev if dev >= 1.0 else self._level) if self._active else None
        for window in self.windows.values():
            window.set_level(self._level)

    def force_hide(self):
        self._level = None
        self._bad_since = None
        self._last_bad = None
        self._recover_since = None
        self._active = False
        for window in self.windows.values():
            window.force_hide()

    def isVisible(self):
        return any(window.isVisible() for window in self.windows.values())
