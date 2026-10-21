import copy
import sys
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel, QWidget
from PySide6.QtGui import QAction, QFocusEvent, QKeySequence
from PySide6.QtCore import QEvent
from PySide6.QtTest import QTest

import config
from shrimply.core.states import State
from shrimply.core.breaks import BreakReminder
from shrimply.ui.main_window import MainWindow


@pytest.fixture
def window():
    application = QApplication.instance() or QApplication([])
    log = Mock()
    log.day_summaries.return_value = []
    controller = SimpleNamespace(
        cfg=copy.deepcopy(config.DEFAULTS), machine=SimpleNamespace(state=State.GOOD),
        worker=Mock(), baseline=object(), _suspended=False, _idle_stopped=False,
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


@pytest.mark.parametrize("state", [State.GOOD, State.DRIFTING, State.BAD, State.AWAY, State.PAUSED])
def test_normal_dashboard_stays_focused_on_progress(window, state):
    view, controller, _ = window
    controller.machine.state = state
    view.refresh()
    assert view.notice_card.isHidden()
    controller.worker.start.assert_not_called()


def test_missing_score_does_not_claim_good_posture(window):
    view, controller, _ = window
    controller._display_deviation = None
    view.refresh()
    assert view.notice_card.isHidden()


def test_daily_line_changes_only_with_local_date(window, monkeypatch):
    import shrimply.ui.main_window as module

    view, _, _ = window
    assert view.dashboard_heading.text() == "Dashboard"
    assert view.daily_line.parent() is view.dashboard_page.widget()
    assert len(module.DAILY_LINES) == 20
    monkeypatch.setattr(module, "date", SimpleNamespace(today=lambda: date(2026, 10, 18)))
    view.refresh()
    first = view.daily_line.text()
    assert first == f"“{module.DAILY_LINES[date(2026, 10, 18).toordinal() % 20]}”"
    assert view.daily_line.font().bold()
    assert view.dashboard_heading.font().pointSize() > view.daily_line.font().pointSize()
    view.refresh()
    assert view.daily_line.text() == first
    monkeypatch.setattr(module, "date", SimpleNamespace(today=lambda: date(2026, 10, 19)))
    view.refresh()
    assert view.daily_line.text() != first


def test_camera_setup_shortcut_opens_the_relevant_preference_page(window):
    view, controller, _ = window
    controller.machine.state = State.CAMERA_ERROR
    view.refresh()
    view.tracking_settings.click()
    controller._open_settings_page.assert_called_with("Tracking")
    controller.worker.start.assert_not_called()


def test_camera_failure_shows_one_recovery_card_and_clears_on_recovery(window):
    view, controller, _ = window
    controller.machine.state = State.CAMERA_ERROR
    controller.worker.camera_state = "reconnecting"
    controller.worker.camera_error = "Device disconnected."
    view.refresh()
    assert not view.notice_card.isHidden()
    assert view.notice_heading.text() == "Camera unavailable"
    assert "Device disconnected" in view.notice_detail.text()
    assert not view.camera_retry.isHidden()
    assert view.calibrate.isHidden()
    view.camera_retry.click()
    controller.restart_camera.assert_called_once()
    controller.machine.state = State.GOOD
    controller.worker.camera_state = "running"
    view.refresh()
    assert view.notice_card.isHidden()


def test_missing_calibration_shows_setup_action_even_while_paused(window):
    view, controller, _ = window
    controller.baseline = None
    controller.machine.state = State.PAUSED
    view.refresh()
    assert not view.notice_card.isHidden()
    assert view.notice_heading.text() == "Set up posture tracking"
    assert not view.calibrate.isHidden()
    assert view.camera_retry.isHidden()
    view.calibrate.click()
    controller.start_calibration.assert_called_once()


def test_camera_failure_takes_priority_over_missing_calibration(window):
    view, controller, _ = window
    controller.baseline = None
    controller.machine.state = State.CAMERA_ERROR
    controller.worker.camera_state = "reconnecting"
    controller.worker.camera_error = "Device disconnected."
    view.refresh()
    assert view.notice_heading.text() == "Camera unavailable"
    assert view.calibrate.isHidden()
    controller.machine.state = State.UNCALIBRATED
    view.refresh()
    assert view.notice_heading.text() == "Set up posture tracking"
    assert view.camera_retry.isHidden()
    controller._suspended = True
    view.refresh()
    assert view.notice_card.isHidden()


def test_sidebar_settings_keeps_a_name_shortcut_and_existing_action(window):
    view, controller, _ = window
    button = view.settings_button
    assert button.text().strip() == "Settings"
    assert not button.icon().isNull()
    assert button.accessibleName() == "Settings"
    assert button.shortcut().toString() == ("" if sys.platform == "darwin" else "Alt+S")
    assert view.tracking_settings.shortcut().toString() != "Alt+S"
    assert button.focusPolicy() == Qt.StrongFocus
    button.click()
    controller._open_settings.assert_called_once()


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS application menu")
def test_mac_application_menu_uses_standard_roles_and_commands(window):
    view, controller, _ = window
    controller._show_about = Mock()
    controller._on_quit = Mock()
    actions = {a.menuRole(): a for a in view.findChildren(QAction)
               if a.menuRole() in (QAction.PreferencesRole, QAction.QuitRole, QAction.AboutRole)}
    assert actions[QAction.PreferencesRole].shortcut() == QKeySequence(QKeySequence.Preferences)
    assert actions[QAction.QuitRole].shortcut() == QKeySequence(QKeySequence.Quit)
    actions[QAction.PreferencesRole].trigger()
    controller._open_settings.assert_called_once()
    actions[QAction.AboutRole].trigger()
    controller._show_about.assert_called_once()
    actions[QAction.QuitRole].trigger()
    controller._on_quit.assert_called_once()
    close = next(a for a in view.findChildren(QAction) if a.text() == "Close Window")
    assert close.shortcut() == QKeySequence(QKeySequence.Close)
    close.trigger()
    assert not view.isVisible()
    controller.worker.stop.assert_not_called()


def test_settings_cog_border_is_for_keyboard_focus_only(window):
    view, _, _ = window
    button = view.settings_button
    button.focusInEvent(QFocusEvent(QEvent.FocusIn, Qt.MouseFocusReason))
    assert not button.property("keyboardFocus")
    button.focusInEvent(QFocusEvent(QEvent.FocusIn, Qt.TabFocusReason))
    assert button.property("keyboardFocus")
    button.focusOutEvent(QFocusEvent(QEvent.FocusOut))
    assert not button.property("keyboardFocus")


def test_sidebar_collapses_and_routes_between_pages(window):
    view, controller, application = window
    assert view.sidebar.width() == 168
    assert not any(label.text() == "Shrimply" for label in view.sidebar.findChildren(QLabel))
    assert view.dashboard_button.text().startswith("\u2002")
    assert view.settings_button.text().startswith("\u2002")
    assert view.dashboard_button.isChecked()
    assert not view.settings_button.isChecked()
    assert view.dashboard_button.font().pointSize() == 11
    assert view.dashboard_button.font().weight() == view.settings_button.font().weight()
    assert view.dashboard_button.iconSize() == view.settings_button.iconSize()
    assert view.dashboard_button.iconSize().width() == 20
    assert view.dashboard_button.height() == view.settings_button.height() == 44
    expanded_icon = view.sidebar_toggle.icon().pixmap(24, 24).toImage()
    view.toggle_sidebar()
    assert view.sidebar.width() == 56
    assert view.sidebar_toggle.accessibleName() == "Expand menu"
    collapsed_icon = view.sidebar_toggle.icon().pixmap(24, 24).toImage()
    assert collapsed_icon == expanded_icon
    point = QPoint(round(15 * collapsed_icon.devicePixelRatio()),
                   round(12 * collapsed_icon.devicePixelRatio()))
    assert collapsed_icon.pixelColor(point).alpha() == 0
    assert view.dashboard_button.toolButtonStyle() == Qt.ToolButtonIconOnly
    assert view.dashboard_button.accessibleName() == "Dashboard"
    view.toggle_sidebar()
    assert view.sidebar.width() == 168
    assert view.dashboard_button.toolButtonStyle() == Qt.ToolButtonTextBesideIcon
    assert not view.dashboard_button.icon().isNull()
    view.resize(620, 600)
    view.show()
    application.processEvents()
    assert view.sidebar_toggle.x() == 8
    assert view.dashboard_page.horizontalScrollBar().maximum() == 0
    view.toggle_sidebar()
    application.processEvents()
    assert view.sidebar_toggle.x() == 8
    assert view.dashboard_page.horizontalScrollBar().maximum() == 0
    view.hide()
    view.show()
    assert view.sidebar.width() == 56
    assert view.sidebar_toggle.accessibleName() == "Expand menu"
    view.settings_button.click()
    controller._open_settings.assert_called_once()


def test_dashboard_navigation_keeps_settings_selected_on_save_failure(window):
    view, controller, _ = window
    page = QWidget()
    page.tabs = QWidget()
    view.show_settings(page)
    controller._settings_dlg = Mock()
    controller._settings_dlg.accept.side_effect = lambda: None
    view.dashboard_button.click()
    assert view.pages.currentWidget() is page
    assert view.settings_button.isChecked()
    view.pages.setCurrentWidget(view.dashboard_page)


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


def test_dashboard_leads_with_quote_and_progress(window):
    view, controller, application = window
    layout = view.dashboard_page.widget().layout()
    assert layout.indexOf(view.dashboard_heading) < layout.indexOf(view.daily_line)
    assert layout.indexOf(view.daily_line) < layout.indexOf(view.progress)
    assert view.settings_heading.isHidden()
    view.resize(620, 480)
    view.show()
    application.processEvents()
    scroll = view.dashboard_page.verticalScrollBar()
    scroll.setValue(scroll.maximum())
    assert view.dashboard_heading.mapTo(view.dashboard_page.viewport(), QPoint(0, 0)).y() < 0
    assert view.notice_card.isHidden()
    assert not any(card.accessibleName() in ("Now", "Tracking", "Break reminders")
                   for card in view.findChildren(QGroupBox))
    controller.log.day_summaries.return_value = [{
        "ts": datetime.combine(date.today(), datetime.min.time()).timestamp(),
        "pct_good": 50., "seconds": 120., "good_s": 60.,
        "drifting_s": 30., "bad_s": 30., "measurement": "time",
    }]
    view.progress.refresh()
    assert view.progress.mix.height() == 22
    assert [label.text() for label in view.progress.mix_values] == [
        "Comfortable\n1 min", "Drifting\n<1 min", "Adjust\n<1 min"]
    assert "Comfortable 1 min" in view.progress.mix.accessibleDescription()


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


def test_main_window_stays_open_if_settings_cannot_finish(window):
    view, controller, application = window
    page = QWidget()
    view.pages.addWidget(page)
    view.pages.setCurrentWidget(page)
    controller._settings_dlg = Mock()
    controller._settings_dlg._finish_pending.return_value = False
    view.show()
    application.processEvents()
    view.close()
    assert view.isVisible()
    controller._settings_dlg._finish_pending.assert_called_once()
    view.pages.setCurrentWidget(view.dashboard_page)


def test_progress_refresh_icon_is_named_and_refreshes_history(window):
    view, controller, _ = window
    button = view.progress.refresh_button
    assert button.text() == "Refresh"
    assert not button.icon().isNull()
    assert button.accessibleName() == "Refresh progress"
    expected = QKeySequence(QKeySequence.Refresh) if sys.platform == "darwin" else QKeySequence("Alt+R")
    assert button.shortcut() == expected
    button.click()
    assert button.text() == "Refreshing…"
    assert button.isEnabled()
    view.progress._refresh_timer.stop()
    view.progress._finish_manual_refresh()
    controller.log.day_summaries.assert_called_once_with(182)
    assert button.text() == "Refresh"


def test_progress_calendar_distinguishes_empty_day_from_zero_in_range(window):
    view, controller, application = window
    today = date.today()
    controller.log.day_summaries.return_value = [{
        "ts": datetime(today.year, today.month, today.day).timestamp(),
        "pct_good": 0., "minutes": 2., "seconds": 120.,
        "good_s": 0., "drifting_s": 0., "bad_s": 120.,
        "measurement": "time",
    }]
    view.progress.refresh()
    assert "0% in calibrated range" in view.progress.day_detail.text()
    view.resize(620, 600)
    view.show()
    application.processEvents()
    card = view.progress.calendar_card
    date_y = view.progress.selected_date.mapTo(card, QPoint(0, 0)).y()
    detail_y = view.progress.day_detail.mapTo(card, QPoint(0, 0)).y()
    refresh_y = view.progress.refresh_button.mapTo(card, QPoint(0, 0)).y()
    assert date_y < detail_y
    assert abs(detail_y - refresh_y) <= view.progress.refresh_button.height()
    assert view.dashboard_page.horizontalScrollBar().maximum() == 0
    assert "2 min monitored" in view.progress.week_lbl.text()
    yesterday = today - timedelta(days=1)
    view.progress._cells[yesterday].click()
    assert "No observations" in view.progress.day_detail.text()


def test_progress_six_month_grid_and_timed_summary_exclude_legacy_estimates(window):
    view, controller, application = window
    view.resize(1000, 700)
    view.show()
    application.processEvents()
    today = date.today()
    yesterday = today - timedelta(days=1)
    view.progress.refresh()
    before_grid = min(view.progress._cells) - timedelta(days=1)
    controller.log.day_summaries.return_value = [
        {"ts": datetime.combine(today, datetime.min.time()).timestamp(),
         "pct_good": 50., "seconds": 120., "good_s": 60., "measurement": "time"},
        {"ts": datetime.combine(yesterday, datetime.min.time()).timestamp(),
         "pct_good": 90., "measurement": "legacy_samples"},
        {"ts": datetime.combine(before_grid, datetime.min.time()).timestamp(),
         "pct_good": 100., "seconds": 3600., "good_s": 3600., "measurement": "time"},
    ]
    view.progress.refresh()
    assert len(view.progress._cells) == 182
    assert view.progress.tracked_days.text() == "2"
    assert view.progress.monitored_time.text() == "2 min"
    assert view.progress.in_range.text() == "50%"
    assert min(view.progress._cells) < today - timedelta(days=160)


def test_progress_calendar_fits_minimum_dashboard_width(window):
    view, _, application = window
    view.resize(620, 600)
    view.show()
    application.processEvents()
    assert view.dashboard_page.horizontalScrollBar().maximum() == 0
    card = view.progress.calendar_card
    refresh = view.progress.refresh_button
    assert card.width() - refresh.mapTo(card, QPoint(refresh.width(), 0)).x() <= 20
    assert len(view.progress._cells) < 182
    assert card.accessibleName() == f"Last {view.progress._weeks_shown} weeks"
    last = view.progress._cells[max(view.progress._cells)]
    assert last.mapTo(card, QPoint(last.width(), 0)).x() <= card.width() - 14
    assert last.width() == last.height() == 20
    yesterday = date.today() - timedelta(days=1)
    view.progress._cells[yesterday].click()
    view.resize(1200, 700)
    application.processEvents()
    view.progress.refresh()
    assert len(view.progress._cells) == 182
    assert view.progress._cells[max(view.progress._cells)].width() == 20
    assert view.progress._selected == yesterday


def test_context_card_fits_minimum_width(window):
    view, controller, application = window
    view.resize(620, 600)
    view.show()
    controller.machine.state = State.CAMERA_ERROR
    controller.worker.camera_state = "reconnecting"
    controller.worker.camera_error = "Device disconnected."
    view.refresh()
    application.processEvents()
    assert view.dashboard_page.horizontalScrollBar().maximum() == 0
    assert not view.camera_retry.isHidden()
    controller.baseline = None
    controller.machine.state = State.UNCALIBRATED
    controller.worker.camera_state = "running"
    view.refresh()
    application.processEvents()
    assert view.dashboard_page.horizontalScrollBar().maximum() == 0
    assert not view.calibrate.isHidden()


def test_break_states_keep_dashboard_focused_on_progress(window):
    view, controller, _ = window
    controller.breaks.pending = True
    view.refresh()
    assert view.notice_card.isHidden()
    controller.breaks.take_break(0.)
    view.refresh()
    assert view.notice_card.isHidden()


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


def test_progress_empty_and_legacy_cells_are_neutral_without_marks(window):
    view, controller, _ = window
    today = date.today()
    controller.log.day_summaries.return_value = [{
        "ts": datetime.combine(today, datetime.min.time()).timestamp(),
        "pct_good": 60., "measurement": "legacy_samples",
    }]
    view.progress.refresh()
    cell = view.progress._cells[today]
    empty = view.progress._cells[today - timedelta(days=1)]
    assert cell.text() == empty.text() == ""
    assert view.progress.palette().mid().color().name() in cell.styleSheet()
    assert view.progress.palette().midlight().color().name() in empty.styleSheet()
    assert "older sample-based estimate" in cell.accessibleName()
    assert "60%" in view.progress.day_detail.text()
    assert "older sample-based estimate" in view.progress.day_detail.text()
    assert not any("Darker coral" in label.text() for label in
                   view.progress.calendar_card.findChildren(QLabel))


def test_break_card_switches_actions_and_restores_the_next_suggestion(window):
    from shrimply.ui.break_prompt import BreakPrompt
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
    from shrimply.ui.break_prompt import BreakPrompt
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


def test_progress_shares_dashboard_and_calibration_hides_setup_card(window):
    view, controller, _ = window
    view.show()
    assert view.progress.parent() is view.dashboard_page.widget()
    controller.log.day_summaries.assert_called_once_with(182)
    assert f"No observations in the {view.progress.calendar_heading.text().lower()}" in view.progress.today_lbl.text()
    controller.baseline = None
    controller._cal = object()
    view.refresh()
    assert view.notice_card.isHidden()


def test_controller_wires_tray_to_main_window_without_opening_camera(window, monkeypatch):
    import shrimply.ui.app as module

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
    controller = module.ShrimplyApp("models")
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
