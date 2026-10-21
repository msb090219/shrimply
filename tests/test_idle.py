"""Tests for the system-idle policy (pure part)."""
from __future__ import annotations

from shrimply.core.idle import IDLE_STOP_S, should_idle_stop
from unittest.mock import Mock

from shrimply.core import idle


def test_macos_idle_uses_combined_session_activity_and_caches_library(monkeypatch):
    monkeypatch.setattr(idle.sys, "platform", "darwin")
    monkeypatch.setattr(idle, "_mac_idle", None)
    library = Mock()
    library.CGEventSourceSecondsSinceLastEventType.return_value = 305.5
    load = Mock(return_value=library)
    monkeypatch.setattr(idle.ctypes, "CDLL", load)
    assert idle.seconds_idle() == 305.5
    assert idle.seconds_idle() == 305.5
    load.assert_called_once()
    library.CGEventSourceSecondsSinceLastEventType.assert_called_with(0, 0xFFFFFFFF)


def test_macos_idle_unavailable_preserves_tracking(monkeypatch):
    monkeypatch.setattr(idle.sys, "platform", "darwin")
    monkeypatch.setattr(idle, "_mac_idle", None)
    monkeypatch.setattr(idle.ctypes, "CDLL", Mock(side_effect=OSError("Unavailable")))
    assert idle.seconds_idle() == 0.0


def test_stops_after_threshold():
    assert not should_idle_stop(IDLE_STOP_S - 1, calibrating=False, manually_paused=False)
    assert should_idle_stop(IDLE_STOP_S, calibrating=False, manually_paused=False)
    assert should_idle_stop(3600.0, calibrating=False, manually_paused=False)


def test_never_when_calibrating():
    assert not should_idle_stop(3600.0, calibrating=True, manually_paused=False)


def test_never_when_manually_paused():
    # manual pause already stopped the camera; idle logic must not double-manage
    assert not should_idle_stop(3600.0, calibrating=False, manually_paused=True)


def test_zero_idle_means_unavailable_never_stops():
    assert not should_idle_stop(0.0, calibrating=False, manually_paused=False)
