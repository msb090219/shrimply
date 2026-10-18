import copy
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFocusEvent
from PySide6.QtCore import QEvent
from PySide6.QtTest import QTest

import config
from unshrimp.core.states import State
from unshrimp.core.breaks import BreakReminder
from unshrimp.ui.main_window import MainWindow


@pytest.fixture
def window():
    application = QApplication.instance() or QApplication([])
    log = Mock()
    log.day_summaries.return_value = []
    controller = SimpleNamespace(
        cfg=copy.deepcopy(config.DEFAULTS), machine=SimpleNamespace(state=State.GOOD),
        worker=Mock(), baseline=None, _suspended=False, _idle_stopped=False,
        _cal=None, _display_deviation=.2, log=log, _restart_pending=False,
        breaks=BreakReminder(True, 2400), _take_break=Mock(), _snooze_break=Mock(),
        _skip_break=Mock(), _end_break=Mock(),
        _open_settings=Mock(), _open_settings_page=Mock(), _on_pause_toggled=Mock(), start_calibration=Mock(),
        open_camera_preview=Mock(), restart_camera=Mock())
    controller.worker.isRunning.return_value = True
    view = MainWindow(controller)
    view.setAttribute(Qt.WA_DontShowOnScreen)
    yield view, controller, application
    view.hide()
    view.deleteLater()
    application.processEvents()


@pytest.mark.parametrize("state,label", [
    (State.GOOD, "Sitting comfortably"), (State.DRIFTING, "Posture drifting"),
    (State.BAD, "Time to adjust"), (State.AWAY, "Away from the desk"),
    (State.PAUSED, "Tracking paused"), (State.CAMERA_ERROR, "Camera unavailable"),
    (State.UNCALIBRATED, "Set up your posture baseline"),
])
def test_main_window_reports_real_state(window, state, label):
    view, controller, _ = window
    controller.machine.state = state
    view.refresh()
    assert view.status.text() == label
    controller.worker.start.assert_not_called()


def test_missing_score_does_not_claim_good_posture(window):
    view, controller, _ = window
    controller._display_deviation = None
    view.refresh()
    assert view.status.text() == "Finding your posture"


def test_daily_line_changes_only_with_local_date(window, monkeypatch):
    import unshrimp.ui.main_window as module

    view, _, _ = window
    assert view.dashboard_heading.text() == "Dashboard"
    assert view.daily_line.parent() is view.dashboard_page.widget()
    assert len(module.DAILY_LINES) == 20
    monkeypatch.setattr(module, "date", SimpleNamespace(today=lambda: date(2026, 10, 18)))
    view.refresh()
    first = view.daily_line.text()
    assert first == module.DAILY_LINES[date(2026, 10, 18).toordinal() % 20]
    view.refresh()
    assert view.daily_line.text() == first
    monkeypatch.setattr(module, "date", SimpleNamespace(today=lambda: date(2026, 10, 19)))
    view.refresh()
    assert view.daily_line.text() != first


def test_today_shortcuts_open_the_relevant_preference_page(window):
    view, controller, _ = window
    view.tracking_settings.click()
    controller._open_settings_page.assert_called_with("Tracking")
    view.reminder_settings.click()
    controller._open_settings_page.assert_called_with("Alerts and breaks")
    controller.worker.start.assert_not_called()


def test_main_camera_preview_retry_and_status_follow_worker_frames(window):
    view, controller, _ = window
    controller.worker.camera_state = "starting"
    view.refresh()
    assert "Starting" in view.camera.text()
    view.camera_preview.click()
    controller.open_camera_preview.assert_called_once()
    controller.worker.camera_state = "reconnecting"
    controller.worker.camera_error = "Device disconnected."
    view.refresh()
    assert "Reconnecting" in view.camera.text()
    assert "Device disconnected" in view.camera_detail.text()
    assert not view.camera_retry.isHidden()
    view.camera_retry.click()
    controller.restart_camera.assert_called_once()
    controller.worker.camera_state = "running"
    view.refresh()
    assert "Running" in view.camera.text()
    assert view.camera_retry.isHidden()
    assert view.camera_detail.isHidden()


def test_settings_cog_keeps_a_name_shortcut_and_existing_action(window):
    view, controller, _ = window
    button = view.settings_button
    assert button.text() == ""
    assert not button.icon().isNull()
    assert button.accessibleName() == "Settings"
    assert button.shortcut().toString() == "Alt+S"
    assert view.tracking_settings.shortcut().toString() != "Alt+S"
    assert button.focusPolicy() == Qt.StrongFocus
    button.click()
    controller._open_settings.assert_called_once()


def test_settings_cog_border_is_for_keyboard_focus_only(window):
    view, _, _ = window
    button = view.settings_button
    button.focusInEvent(QFocusEvent(QEvent.FocusIn, Qt.MouseFocusReason))
    assert not button.property("keyboardFocus")
    button.focusInEvent(QFocusEvent(QEvent.FocusIn, Qt.TabFocusReason))
    assert button.property("keyboardFocus")
    button.focusOutEvent(QFocusEvent(QEvent.FocusOut))
    assert not button.property("keyboardFocus")


def test_reopening_progress_refreshes_the_same_history_view(window):
    view, controller, _ = window
    view.show()
    view.hide()
    controller.log.day_summaries.return_value = [
        {"ts": datetime.combine(date.today(), datetime.min.time()).timestamp(),
         "pct_good": 80., "minutes": 12., "seconds": 720., "measurement": "time"}]
    view.show()
    assert "80%" in view.progress.today_lbl.text()
    assert "12 min monitored" in view.progress.today_lbl.text()
    controller.worker.stop.assert_not_called()


def test_main_window_close_keeps_tracking_and_reopen_restores_refresh(window):
    view, controller, application = window
    view.show()
    application.processEvents()
    assert view.timer.isActive()
    view.close()
    assert not view.isVisible()
    assert not view.timer.isActive()
    controller.worker.stop.assert_not_called()
    view.show()
    assert view.isVisible()
    assert view.timer.isActive()


def test_pause_controls_route_to_existing_policy(window):
    view, controller, _ = window
    assert not view.pause.icon().isNull()
    pause_icon = view.pause.icon().cacheKey()
    view.pause.click()
    controller._on_pause_toggled.assert_called_with(True)
    controller.machine.state = State.PAUSED
    view.refresh()
    assert view.pause.icon().cacheKey() != pause_icon
    view.pause.click()
    controller._on_pause_toggled.assert_called_with(False)


def test_progress_refresh_icon_is_named_and_refreshes_history(window):
    view, controller, _ = window
    button = view.progress.refresh_button
    assert button.text() == "Refresh"
    assert not button.icon().isNull()
    assert button.accessibleName() == "Refresh progress"
    assert button.shortcut().toString() == "Alt+R"
    button.click()
    assert button.text() == "Refreshing…"
    assert button.isEnabled()
    view.progress._refresh_timer.stop()
    view.progress._finish_manual_refresh()
    controller.log.day_summaries.assert_called_once_with(84)
    assert button.text() == "Refresh"


def test_progress_calendar_distinguishes_empty_day_from_zero_in_range(window):
    view, controller, _ = window
    today = date.today()
    controller.log.day_summaries.return_value = [{
        "ts": datetime(today.year, today.month, today.day).timestamp(),
        "pct_good": 0., "minutes": 2., "seconds": 120.,
        "good_s": 0., "drifting_s": 0., "bad_s": 120.,
        "measurement": "time",
    }]
    view.progress.refresh()
    assert "0% in calibrated range" in view.progress.day_detail.text()
    assert "2 min monitored" in view.progress.week_lbl.text()
    yesterday = today - timedelta(days=1)
    view.progress._cells[yesterday].click()
    assert "No observations" in view.progress.day_detail.text()


def test_progress_today_does_not_reuse_yesterdays_result(window):
    view, controller, _ = window
    yesterday = date.today() - timedelta(days=1)
    controller.log.day_summaries.return_value = [{
        "ts": datetime.combine(yesterday, datetime.min.time()).timestamp(),
        "pct_good": 90., "seconds": 600., "measurement": "time",
    }]
    view.progress.refresh()
    assert view.progress.today_lbl.text() == "No monitored time today."
    view.progress._cells[yesterday].click()
    assert "90%" in view.progress.day_detail.text()


def test_progress_calendar_arrow_keys_select_days_and_keep_one_tab_stop(window):
    view, _, _ = window
    view.progress.refresh()
    today = date.today()
    previous_week = today - timedelta(days=7)
    button = view.progress._cells[today]
    assert button.focusPolicy() == Qt.StrongFocus
    QTest.keyClick(button, Qt.Key_Left)
    assert view.progress._selected == previous_week
    assert view.progress._cells[previous_week].focusPolicy() == Qt.StrongFocus
    assert button.focusPolicy() == Qt.ClickFocus
    assert view.progress.selected_date.text() == previous_week.strftime("%A, %d %B %Y")
    QTest.keyClick(view.progress._cells[previous_week], Qt.Key_Right)
    assert view.progress._selected == today


def test_progress_legacy_cell_has_visible_and_accessible_estimate_marker(window):
    view, controller, _ = window
    today = date.today()
    controller.log.day_summaries.return_value = [{
        "ts": datetime.combine(today, datetime.min.time()).timestamp(),
        "pct_good": 60., "measurement": "legacy_samples",
    }]
    view.progress.refresh()
    cell = view.progress._cells[today]
    assert cell.text() == "~"
    assert "older sample-based estimate" in cell.accessibleName()
    assert "60%" in view.progress.day_detail.text()


def test_due_break_controls_are_available_in_the_main_window(window):
    view, controller, _ = window
    controller.breaks.pending = True
    view.refresh()
    assert "A break is due" in view.reminders.text()
    assert not view.break_actions.isHidden()
    view.take_break.click()
    controller._take_break.assert_called_once()
    view.later_break.menu().actions()[0].trigger()
    controller._snooze_break.assert_called_once_with(5)
    view.later_break.menu().actions()[2].trigger()
    controller._skip_break.assert_called_once()
    controller.breaks.configure(False, 2400)
    view.refresh()
    assert view.break_actions.isHidden()
    assert "are off" in view.reminders.text()


def test_active_break_has_countdown_and_end_action(window, monkeypatch):
    view, controller, _ = window
    monkeypatch.setattr("unshrimp.ui.main_window.time.monotonic", lambda: 30.)
    controller.breaks.take_break(0.)
    view.refresh()
    assert "1:30 remaining" in view.reminders.text()
    assert "End break" in view.take_break.text()
    assert view.later_break.isHidden()
    view.take_break.click()
    controller._end_break.assert_called_once()


def test_break_card_switches_actions_and_restores_the_next_suggestion(window):
    from unshrimp.ui.break_prompt import BreakPrompt
    prompt = BreakPrompt()
    prompt.setAttribute(Qt.WA_DontShowOnScreen)
    take, end = Mock(), Mock()
    prompt.take_requested.connect(take)
    prompt.end_requested.connect(end)
    try:
        prompt.set_suggestion("A short walk")
        prompt.take_button.click()
        take.assert_called_once()
        prompt.set_break_state(90)
        assert "1:30" in prompt.title.text()
        assert prompt.later_button.isHidden()
        prompt.take_button.click()
        end.assert_called_once()
        prompt.set_break_state(None)
        assert prompt.suggestion.text() == "A short walk"
        assert not prompt.later_button.isHidden()
    finally:
        prompt.hide()
        prompt.deleteLater()


def test_break_card_shows_duration_and_later_menu_actions(window):
    from unshrimp.ui.break_prompt import BreakPrompt
    prompt = BreakPrompt(break_minutes=5)
    prompt.setAttribute(Qt.WA_DontShowOnScreen)
    later, skip = Mock(), Mock()
    prompt.later_requested.connect(later)
    prompt.skip_requested.connect(skip)
    try:
        assert "5-minute break" in prompt.title.text()
        prompt.later_button.menu().actions()[1].trigger()
        later.assert_called_once_with(10)
        prompt.later_button.menu().actions()[2].trigger()
        skip.assert_called_once()
    finally:
        prompt.hide()
        prompt.deleteLater()


def test_progress_shares_dashboard_and_calibration_is_single_flow(window):
    view, controller, _ = window
    view.show()
    assert view.progress.parent() is view.dashboard_page.widget()
    controller.log.day_summaries.assert_called_once_with(84)
    assert "No observations in the last 12 weeks" in view.progress.today_lbl.text()
    controller._cal = object()
    view.refresh()
    assert not view.calibrate.isEnabled()
    assert view.status.text() == "Calibration in progress"


def test_controller_wires_tray_to_main_window_without_opening_camera(window, monkeypatch):
    import unshrimp.ui.app as module

    _, _, application = window
    cfg = copy.deepcopy(config.DEFAULTS)
    cfg["hud"]["visible"] = False
    monkeypatch.setattr(config, "load", lambda: cfg)
    monkeypatch.setattr(config, "save", Mock())
    worker = Mock()
    worker.isRunning.return_value = False
    monkeypatch.setattr(module, "VisionWorker", Mock(return_value=worker))
    log = Mock()
    log.day_summaries.return_value = []
    monkeypatch.setattr(module, "PostureLog", Mock(return_value=log))
    controller = module.UnshrimpApp("models")
    controller.main_window.setAttribute(Qt.WA_DontShowOnScreen)
    try:
        worker.start.assert_not_called()
        controller.tray.open_action.trigger()
        application.processEvents()
        assert controller.main_window.isVisible()
        controller.main_window.close()
        worker.stop.assert_not_called()
        assert controller.hud._menu is controller.tray.menu
        controller.tray.open_action.trigger()
        application.processEvents()
        assert controller.main_window.isVisible()
        controller.hud.pause_button.click()
        assert controller.machine.state is State.PAUSED
    finally:
        controller.shutdown()
        controller.main_window.hide()
        controller.hud.hide()
        controller.tray.icon.hide()
        controller.main_window.deleteLater()
        controller.hud.deleteLater()
        controller.preview_win.deleteLater()
        controller.mascot.deleteLater()
        controller.break_prompt.hide()
        controller.break_prompt.deleteLater()
