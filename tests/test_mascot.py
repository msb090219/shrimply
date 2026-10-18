"""Tests for the mascot mapping — pure math, no Qt app needed."""
from unshrimp.ui.mascot import mascot_params
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


def test_monotonic_through_drift_to_bad():
    prev = -1.0
    for dev in (1.0, 1.2, 1.5, 1.9, 2.5):
        op, _ = mascot_params(dev)
        assert op > prev
        prev = op


@pytest.mark.parametrize("key", ["s", "m", "l"])
def test_all_sizes_fit_at_maximum_rise_and_bob(key):
    from PySide6.QtWidgets import QApplication
    from unshrimp.ui.mascot import MascotWindow, _BOTTOM_MARGIN, _BOB_PX
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
    from unshrimp.ui import mascot
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
    try:
        group.screen_name = "*"
        group.position = "right"
        group.reduce_motion = True
        group.set_options(.7, "l", False)
        assert len(group.windows) == 2
        group.set_level(2.5)
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
    from unshrimp.ui.mascot import MascotWindow

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
