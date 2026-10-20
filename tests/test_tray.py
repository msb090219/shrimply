from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from shrimply.ui.tray import Tray


@pytest.fixture
def tray():
    app = QApplication.instance() or QApplication([])
    tray = Tray()
    yield tray
    tray.menu.hide()
    tray.menu.deleteLater()
    tray.deleteLater()
    app.processEvents()


def test_visibility_sync_does_not_emit_user_changes(tray):
    mascot, hud = Mock(), Mock()
    tray.mascot_toggled.connect(mascot)
    tray.hud_toggled.connect(hud)
    tray.set_mascot_checked(False)
    tray.sync_hud_action(False)
    assert not tray.mascot_action.isChecked()
    assert not tray.hud_action.isChecked()
    mascot.assert_not_called()
    hud.assert_not_called()
    tray.mascot_action.trigger()
    tray.hud_action.trigger()
    mascot.assert_called_once_with(True)
    hud.assert_called_once_with(True)


def test_unavailable_tray_keeps_retrying_and_signals_fallback(tray, monkeypatch):
    from shrimply.ui import tray as tray_module

    available = iter((False, False, True))
    monkeypatch.setattr(tray_module.QSystemTrayIcon, "isSystemTrayAvailable",
                        staticmethod(lambda: next(available)))
    scheduled = []
    monkeypatch.setattr(tray_module.QTimer, "singleShot",
                        staticmethod(lambda delay, callback: scheduled.append((delay, callback))))
    tray.icon.show = Mock()
    fallback = Mock()
    tray.unavailable.connect(fallback)

    tray.show_when_ready()
    assert len(scheduled) == 1
    scheduled.pop()[1]()
    fallback.assert_called_once()
    assert len(scheduled) == 1
    scheduled.pop()[1]()
    tray.icon.show.assert_called_once()
    assert scheduled == []


def test_calibration_override_is_in_menu_and_primary_controls_route(tray):
    assert tray.cont_action in tray.menu.actions()
    assert not tray.cont_action.isVisible()
    skip, pause = Mock(), Mock()
    tray.continue_anyway.connect(skip)
    tray.pause_toggled.connect(pause)
    tray.show_continue(True)
    tray.cont_action.trigger()
    skip.assert_called_once()
    tray.set_paused_ui(True)
    assert tray.pause_action.text() == "&Resume tracking"
    tray.pause_action.trigger()
    pause.assert_called_once_with(False)
    tray.set_controls(True, False)
    assert tray.cal_action.text() == "View &calibration…"
    tray.set_controls(False, True)
    assert not tray.cal_action.isEnabled()
    assert not tray.pause_action.isEnabled()


def test_header_explains_state_without_raw_numbers_and_reuses_icon(tray):
    tray.set_state("bad", "1.8")
    icon_key = tray.icon.icon().cacheKey()
    assert tray._header_text.text() == "Time to adjust"
    assert "1.8" not in tray.icon.toolTip()
    tray.set_state("bad", "2.2")
    assert tray.icon.icon().cacheKey() == icon_key
    tray.set_break_text("Break · 1:30 remaining")
    assert not tray._break_text.isHidden()
    expanded = tray._header_widget.height()
    tray.set_break_text("")
    assert tray._break_text.isHidden()
    assert tray._header_widget.height() < expanded


def test_compact_action_sync_is_silent_and_user_toggle_emits(tray):
    changed = Mock()
    tray.compact_toggled.connect(changed)
    tray.sync_compact_action(True)
    changed.assert_not_called()
    assert tray.compact_action in tray.menu.actions()
    assert tray.compact_action.isChecked()
    tray.compact_action.trigger()
    changed.assert_called_once_with(False)
