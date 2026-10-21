"""Tests for the mascot mapping — pure math, no Qt app needed."""
from shrimply.ui.mascot import mascot_params
import pytest


def test_hidden_when_good_or_none():
    assert mascot_params(None) == (0.0, 0.0)
    assert mascot_params(0.0) == (0.0, 0.0)
    assert mascot_params(0.99) == (0.0, 0.0)


def test_faint_at_drift_threshold():
    opacity, lift = mascot_params(1.0)
    assert opacity == 0.15
    assert lift == 0.0


def test_saturates_at_deep_bad():
    opacity, lift = mascot_params(2.5)
    assert opacity == 0.87
    assert lift == 110.0
    assert mascot_params(9.0) == mascot_params(2.5)  # clamped


def test_mascot_is_visible_at_configured_bad_threshold():
    assert mascot_params(1.5)[0] == .87
    assert mascot_params(2.0, bad_threshold=2.0)[0] == .87
    assert mascot_params(1.5, bad_threshold=2.0)[0] < .87


def test_opacity_grows_to_bad_threshold():
    prev = -1.0
    for dev in (1.0, 1.2, 1.5):
        op, _ = mascot_params(dev)
        assert op > prev
        prev = op


@pytest.mark.parametrize("reduced,bob", [(False, False), (True, True)])
def test_settled_static_mascot_stops_and_unchanged_readings_do_not_restart(reduced, bob):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.mascot import MascotWindow
    app = QApplication.instance() or QApplication([])
    widget = MascotWindow()
    widget.setAttribute(Qt.WA_DontShowOnScreen)
    try:
        widget.reduce_motion = reduced
        widget.set_options(.87, "m", bob)
        widget.set_level(2.)
        for _ in range(100):
            widget._tick()
        assert not widget._timer.isActive()
        widget.set_level(2.)
        assert not widget._timer.isActive()
        assert widget._bob_offset == 0
        widget.set_level(2.4)
        # Reduced motion has no lift; both readings already saturate opacity.
        assert widget._timer.isActive() is not reduced
        widget.set_level(None)
        for _ in range(100):
            widget._tick()
        assert not widget.isVisible()
        assert not widget._timer.isActive()
    finally:
        widget.force_hide()
        widget.deleteLater()
        app.processEvents()


def test_mac_bob_repaints_only_when_raster_state_changes(monkeypatch):
    from unittest.mock import Mock
    from PySide6.QtWidgets import QApplication
    from shrimply.ui import mascot
    app = QApplication.instance() or QApplication([])
    widget = mascot.MascotWindow()
    try:
        widget.set_options(.87, "m", True)
        widget._target = (.5, 10.)
        widget._cur, widget._cur_lift, widget._t0 = .5, 10., 0.
        clock = [0.]
        monkeypatch.setattr(mascot.sys, "platform", "darwin")
        monkeypatch.setattr(mascot.time, "monotonic", lambda: clock[0])
        update = Mock()
        monkeypatch.setattr(widget, "update", update)
        widget._tick()
        clock[0] = .01
        widget._tick()
        assert update.call_count == 1
        clock[0] = .25
        widget._tick()
        assert update.call_count == 2
    finally:
        widget.force_hide()
        widget.deleteLater()
        app.processEvents()
def test_large_shrimp_waits_for_sustained_bad_and_stays_through_brief_recovery():
    from unittest.mock import Mock
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.mascot import MascotGroup, _RECOVERY_HOLD_S

    application = QApplication.instance() or QApplication([])
    group = MascotGroup()
    group.bad_hold_s = 6
    window = Mock()
    group.windows[object()] = window
    try:
        group.set_level(2.0, bad=True, now=0.0)
        for second in range(1, 6):
            group.set_level(2.0, bad=True, now=float(second))
        group.set_level(2.0, bad=True, now=group.bad_hold_s - .1)
        assert group._level is None
        group.set_level(2.0, bad=True, now=group.bad_hold_s)
        assert group._level == 2.0
        group.set_level(.8, bad=False, now=7.0)
        assert group._level == 2.0
        group.set_level(2.0, bad=True, now=8.0)
        group.set_level(1.2, bad=False, now=8.5)
        assert group._level == 1.2
        group.set_level(.8, bad=False, now=9.0)
        group.set_level(.8, bad=False, now=9.0 + _RECOVERY_HOLD_S - .1)
        assert group._level == 1.2
        group.set_level(.8, bad=False, now=9.0 + _RECOVERY_HOLD_S)
        assert group._level is None
        group.set_level(2.0, bad=True, now=13.0)
        assert group._level is None
        group.force_hide()
        group.set_level(2.0, bad=True, now=20.0)
        assert group._level is None
        group.set_level(None, bad=False, now=21.0)
        group.set_level(2.0, bad=True, now=22.0)
        assert group._level is None
        group.set_level(2.0, bad=True, now=23.0)
        group.set_level(2.0, bad=True, now=24.0)
        group.set_level(.8, bad=False, now=25.0)
        group.set_level(2.0, bad=True, now=25.2)
        group.set_level(2.0, bad=True, now=26.2)
        group.set_level(2.0, bad=True, now=27.2)
        group.set_level(2.0, bad=True, now=27.9)
        assert group._level is None
        group.set_level(2.0, bad=True, now=28.0)
        assert group._level == 2.0
        group.set_level(None, bad=False, now=28.1)
        assert group._level is None
        assert not group._active
    finally:
        group.force_hide()
        group.deleteLater()
        application.processEvents()


def test_zero_delay_appears_at_bad_and_fades_at_first_good_sample():
    from unittest.mock import Mock
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.mascot import MascotGroup

    application = QApplication.instance() or QApplication([])
    group = MascotGroup()
    group.windows[object()] = Mock()
    group.bad_hold_s = group.recovery_hold_s = 0
    try:
        group.set_level(1.5, bad=True, now=0.0)
        assert group._level == 1.5
        group.set_level(.8, bad=False, now=.5)
        assert group._level is None
    finally:
        group.force_hide()
        group.deleteLater()
        application.processEvents()


@pytest.mark.parametrize("entrance,expected_lift,instant", [
    ("rise", True, False), ("fade", False, False), ("instant", False, True),
])
def test_entrance_options_keep_movement_independent_of_bobbing(entrance, expected_lift, instant):
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.mascot import MascotWindow

    application = QApplication.instance() or QApplication([])
    window = MascotWindow()
    try:
        window.set_options(.87, "m", False, entrance)
        window.set_level(2.5)
        window._tick()
        assert (window._cur_lift > 0) is expected_lift
        assert (window._cur == window._target[0]) is instant
        if instant:
            window.set_level(None)
            window._tick()
            assert 0 < window._cur < window._max_opacity
        window.reduce_motion = True
        window.set_level(2.5)
        window._tick()
        assert window._cur_lift == 0
    finally:
        window.force_hide()
        window.deleteLater()
        application.processEvents()


def test_text_cue_uses_compact_window_and_shared_posture_response():
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.mascot import MascotWindow

    application = QApplication.instance() or QApplication([])
    window = MascotWindow()
    try:
        window.set_options(.87, "m", False, "fade", 1.5, "text")
        assert window.width() == 220
        assert window._style == "text"
        window.set_level(1.5)
        assert window._target[0] > 0
        assert window._target[1] == 0
        window._cur = .8
        image = QImage(window.size(), QImage.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        window.render(painter, QPoint())
        painter.end()
        assert image.pixelColor(window.width() // 2, window.height() - 50).alpha() > 0
        window.set_level(None)
        assert window._target == (0.0, 0.0)
        window.set_options(.87, "m", False, "fade", 1.5, "shrimp")
        assert window.width() > 220
    finally:
        window.force_hide()
        window.deleteLater()
        application.processEvents()


def test_text_sizes_have_wider_range_and_fit_selected_screen():
    from types import SimpleNamespace
    from PySide6.QtCore import QRect
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.mascot import MascotWindow

    application = QApplication.instance() or QApplication([])
    window = MascotWindow()
    try:
        widths = []
        for size in ("s", "m", "l"):
            window.set_options(.87, size, False, style="text")
            widths.append(window.width())
        assert widths == [154, 220, 440]
        window.target_screen = SimpleNamespace(availableGeometry=lambda: QRect(0, 0, 320, 240))
        window.set_options(.87, "l", False, style="text")
        assert window.width() <= 320 - 48
        assert window.height() <= 240 - 30
    finally:
        window.force_hide()
        window.deleteLater()
        application.processEvents()


def test_text_preview_keeps_sizes_distinct_in_narrow_panel():
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.appearance import ShrimpPreview

    application = QApplication.instance() or QApplication([])
    preview = ShrimpPreview()
    preview.setFixedWidth(240)
    widths = []
    for size in ("s", "m", "l"):
        preview.configure({"mascot_style": "text", "mascot_size": size,
                           "mascot_position": "middle", "mascot_bob": False})
        image = QImage(preview.size(), QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        preview.render(painter, QPoint())
        painter.end()
        background = preview.palette().base().color()
        pixels = [x for x in range(image.width())
                  if image.pixelColor(x, image.height() // 2) != background]
        widths.append(pixels[-1] - pixels[0] + 1)
    assert widths[0] < widths[1] < widths[2] <= 216


@pytest.mark.parametrize("key", ["s", "m", "l"])
def test_all_sizes_fit_at_maximum_rise_and_bob(key):
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.mascot import MascotWindow, _BOTTOM_MARGIN, _BOB_PX
    application = QApplication.instance() or QApplication([])
    widget = MascotWindow()
    try:
        widget.set_options(.87, key, True)
        assert widget._art is not None
        assert widget._art.width() + 24 <= widget.width()
        assert widget._art.height() + 110 + _BOB_PX + _BOTTOM_MARGIN <= widget.height()
    finally:
        widget.force_hide()
        widget.deleteLater()
        application.processEvents()


def test_display_group_hotplug_fallback_suppression_and_fit(monkeypatch):
    from PySide6.QtCore import QRect
    from PySide6.QtWidgets import QApplication
    from unittest.mock import Mock
    from shrimply.ui import mascot
    application = QApplication.instance() or QApplication([])

    class Screen:
        def __init__(self, name, geometry):
            self._name, self.geometry = name, geometry
            self.availableGeometryChanged = Mock()
        def name(self):
            return self._name
        def availableGeometry(self):
            return self.geometry

    first = Screen("main", QRect(0, 0, 1920, 1040))
    second = Screen("small", QRect(-960, 0, 960, 500))
    screens = [first, second]
    monkeypatch.setattr(mascot.QGuiApplication, "screens", staticmethod(lambda: screens))
    monkeypatch.setattr(mascot.QGuiApplication, "primaryScreen", lambda: first)
    group = mascot.MascotGroup()
    group.bad_hold_s = 6
    try:
        group.screen_name = "*"
        group.position = "right"
        group.reduce_motion = True
        group.set_options(.7, "l", False)
        assert len(group.windows) == 2
        group.set_level(2.5, bad=True, now=0.0)
        assert not group.isVisible()
        for tick in range(1, 6):
            group.set_level(2.5, bad=True, now=float(tick))
        group.set_level(2.5, bad=True, now=group.bad_hold_s)
        for screen, window in group.windows.items():
            assert window.isVisible()
            assert window.reduce_motion
            assert window.windowFlags() & mascot.Qt.WindowTransparentForInput
            assert screen.availableGeometry().contains(window.geometry())
            assert window._art.height() + 110 + mascot._BOB_PX + mascot._BOTTOM_MARGIN <= window.height()
        group.force_hide()
        assert not group.isVisible()
        group._screen_removed(second)
        assert list(group.windows) == [first]
        group._screen_added(second)
        assert len(group.windows) == 2
        assert not group.isVisible()
        group.screen_name = "missing"
        group.set_options(.7, "s", True)
        assert list(group.windows) == [first]
    finally:
        group.force_hide()
        for window in group.windows.values():
            window.deleteLater()
        group.deleteLater()
        application.processEvents()


@pytest.mark.parametrize("position,horizontal,vertical", [
    ("top_left", "left", "top"),
    ("top_right", "right", "top"),
    ("middle", "center", "center"),
    ("center", "center", "bottom"),
])
def test_mascot_anchor_positions(position, horizontal, vertical):
    from PySide6.QtCore import QRect
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.mascot import MascotWindow

    class Screen:
        def availableGeometry(self):
            return QRect(0, 0, 1920, 1080)

    application = QApplication.instance() or QApplication([])
    window = MascotWindow()
    try:
        window.target_screen = Screen()
        window.set_options(.87, "m", False)
        window.position = position
        window._anchor()
        if horizontal == "left":
            assert window.x() == 24
        elif horizontal == "right":
            assert window.x() == 1920 - window.width() - 24
        else:
            assert abs(window.geometry().center().x() - 959) <= 1
        if vertical == "top":
            assert window.y() == 24
        elif vertical == "bottom":
            assert window.y() == 1079 - window.height() - 30
        else:
            assert abs(window.geometry().center().y() - 539) <= 1
    finally:
        window.deleteLater()
        application.processEvents()
