"""Controller regressions without opening cameras or writing user settings."""
import copy
import sqlite3
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, call
from PySide6.QtCore import QRect, QObject, Signal

import pytest

import config
import shrimply.ui.app as app_module
from shrimply.core.baseline import Baseline, SignalCal
from shrimply.core.breaks import BreakReminder
from shrimply.core.calibration import CalibrationSession, StepResult
from shrimply.core.smoother import Smoother
from shrimply.core.history import HistoryAccumulator
from shrimply.core.states import PostureStateMachine, State
from shrimply.vision.metrics import FrameSignals


@pytest.fixture
def controller(monkeypatch):
    machine = PostureStateMachine()
    machine.mark_calibrated()
    worker = Mock()
    worker.isRunning.return_value = False
    app = SimpleNamespace(
        machine=machine, worker=worker, models_dir="models", cfg=copy.deepcopy(config.DEFAULTS),
        baseline=Baseline(signals={"head_pitch": SignalCal(5., 8., 1)}),
        _quitting=False, _shutdown_done=False, _idle_stopped=False, _suspended=False,
        _restart_pending=False, _cal=None, _good_streak=0, _settings_dlg=None, _about_dlg=None, _cal_was_paused=False,
        _camera_preview=None,
        _on_calibration_preview=Mock(),
        smoother=Smoother(), history=HistoryAccumulator(), _history_save_failed=False,
        hud=Mock(), tray=Mock(), mascot=Mock(),
        preview_win=Mock(), _render=Mock(), _accumulate=Mock(),
        main_window=Mock(),
        _handle_event=Mock(), _toast=Mock(), _place_preview=Mock(),
        _sync_uncalibrated_ui=Mock(), _accept_baseline=Mock(),
        reminder_timer=Mock(), idle_timer=Mock(), log=Mock(),
        breaks=BreakReminder(True, 2400), break_prompt=Mock(), _ex_i=0,
        _position_break_prompt=Mock(),
        _refresh_tray=Mock(),
        _flush_bucket=Mock(), session_id=1,
    )
    app.main_window.screen.return_value = None
    app.main_window.isMinimized.return_value = False
    for name in ("_on_frame", "_adapt", "_restart_worker", "_on_worker_finished",
                 "_on_cam_error", "_on_cam_recovered", "_cal_step", "_apply_cal_result",
                 "_on_continue_anyway", "start_calibration", "_on_pause_toggled", "shutdown",
                 "_on_system_suspend", "_on_system_resume", "_idle_check", "_open_settings", "_cancel_calibration",
                 "_reminder_fire", "_take_break", "_end_break", "_snooze_break", "_skip_break", "apply_breaks",
                 "_start_after_calibration", "_open_main_window", "_preview_changed"):
        setattr(app, name, MethodType(getattr(app_module.ShrimplyApp, name), app))
    app._end_history_segment = MethodType(app_module.ShrimplyApp._end_history_segment, app)
    app._try_flush_bucket = MethodType(app_module.ShrimplyApp._try_flush_bucket, app)
    monkeypatch.setattr(config, "save", Mock())
    return app


def good_frame():
    return FrameSignals(ok=True, head_pitch=5., head_yaw=0., head_roll=0.,
                        head_sink=.72, lean_in=.52)


def test_compact_indicator_choice_is_applied_synced_and_saved(controller):
    app_module.ShrimplyApp._on_compact_toggled(controller, True)
    controller.hud.set_compact.assert_called_once_with(True)
    controller.tray.sync_compact_action.assert_called_once_with(True)
    assert controller.cfg["hud"]["compact"] is True
    config.save.assert_called_once_with(controller.cfg)


def test_mascot_response_controls_reach_live_overlay(controller):
    controller.cfg.update(mascot_bad_hold_s=0, mascot_recovery_hold_s=8, bad=1.8)
    app_module.ShrimplyApp.apply_motion_settings(controller)
    assert controller.mascot.bad_hold_s == 0
    assert controller.mascot.recovery_hold_s == 8
    assert controller.mascot.set_options.call_args.args[-2:] == (1.8, "shrimp")
    controller.cfg["mascot_style"] = "text"
    app_module.ShrimplyApp.apply_motion_settings(controller)
    assert controller.mascot.set_options.call_args.args[-1] == "text"


def test_preference_patch_preserves_newer_baseline_pause_and_hud_position(controller):
    controller.cfg["baseline"] = {"new": "baseline"}
    controller.cfg["tracking_paused"] = True
    controller.cfg["hud"]["x"] = 400
    controller.apply_thresholds = Mock()
    controller.apply_mascot_settings = Mock()
    app_module.ShrimplyApp.apply_preferences(controller, {"hud": {"size": "l"}, "grace_s": 60})
    saved = config.save.call_args.args[0]
    assert saved["baseline"] == {"new": "baseline"}
    assert saved["tracking_paused"] is True
    assert saved["hud"]["x"] == 400
    assert saved["hud"]["size"] == "l"
    controller.hud.set_size.assert_called_once_with("l")
    controller.apply_thresholds.assert_called_once_with(save=False)
    controller.worker.start.assert_not_called()


def test_failed_preference_write_does_not_mutate_runtime_and_rolls_back_login(controller, monkeypatch):
    import shrimply.autostart as autostart
    monkeypatch.setattr(autostart, "is_enabled", lambda: False)
    login = Mock()
    monkeypatch.setattr(autostart, "set_enabled", login)
    before = copy.deepcopy(controller.cfg)
    config.save.side_effect = OSError("Disk full")
    with pytest.raises(OSError, match="Disk full"):
        app_module.ShrimplyApp.apply_preferences(controller, {"camera_index": 2}, startup=True)
    assert controller.cfg == before
    assert login.call_args_list == [call(True), call(False)]
    controller.worker.start.assert_not_called()


def test_quit_cancelled_by_unsaved_settings_keeps_worker_running(controller):
    controller._settings_dlg = Mock()
    controller._settings_dlg._finish_pending.return_value = False
    controller.shutdown = Mock(return_value=True)
    app_module.ShrimplyApp._on_quit(controller)
    controller.shutdown.assert_not_called()
    assert not controller._quitting


@pytest.mark.parametrize("frame,expected", [
    (QRect(900, 100, 479, 40), (545, 100)),
    (QRect(-100, 100, 479, 40), (0, 100)),
    (QRect(100, 750, 479, 40), (100, 728)),
])
def test_saved_hud_position_keeps_wider_row_controls_inside_screen(controller, monkeypatch, frame, expected):
    from PySide6.QtGui import QGuiApplication
    screen = SimpleNamespace(availableGeometry=lambda: QRect(0, 0, 1024, 768))
    monkeypatch.setattr(QGuiApplication, "screens", lambda: [screen])
    controller.hud.frameGeometry.return_value = frame
    controller.hud.width.return_value = 479
    controller.hud.height.return_value = 40
    app_module.ShrimplyApp._rescue_offscreen_hud(controller)
    controller.hud.move.assert_called_once_with(*expected)


@pytest.mark.parametrize("background,setup,paused", [
    (False, False, False), (True, False, False), (True, True, False),
    (True, False, True), (False, False, True),
])
def test_startup_visibility_and_saved_pause(controller, monkeypatch, background, setup, paused):
    monkeypatch.setattr(app_module.QTimer, "singleShot", lambda *_: None)
    controller._show_welcome = Mock()
    controller._open_main_window = Mock()
    controller.cfg["tracking_paused"] = paused
    if setup:
        controller.baseline = None
    app_module.ShrimplyApp.start(controller, background=background)
    assert controller._show_welcome.call_count == int(setup)
    assert controller._open_main_window.call_count == int(not background or setup)
    assert controller.worker.start.call_count == int(not paused)
    assert (controller.machine.state is State.PAUSED) is paused
    controller.reminder_timer.start.assert_called_once()
    controller.idle_timer.start.assert_called_once()


def test_missing_tray_with_hidden_meter_opens_controls(controller):
    controller._open_main_window = Mock()
    controller.hud.isVisible.return_value = False
    controller.main_window.isVisible.return_value = False
    app_module.ShrimplyApp._ensure_controls_visible(controller)
    controller._open_main_window.assert_called_once()

    controller._open_main_window.reset_mock()
    controller.main_window.isVisible.return_value = True
    app_module.ShrimplyApp._ensure_controls_visible(controller)
    controller._open_main_window.assert_not_called()


@pytest.mark.parametrize("paused", [False, True])
def test_manual_pause_preference_is_saved(controller, paused):
    controller._restart_worker = Mock()
    controller._on_pause_toggled(paused)
    assert controller.cfg["tracking_paused"] is paused
    config.save.assert_called_once_with(controller.cfg)


def test_reopen_restores_minimized_main_window(controller):
    controller.main_window = Mock()
    controller.main_window.isMinimized.return_value = True
    app_module.ShrimplyApp._open_main_window(controller)
    controller.main_window.showNormal.assert_called_once()
    controller.main_window.raise_.assert_called_once()
    controller.main_window.activateWindow.assert_called_once()


def test_background_launch_does_not_repeat_dismissed_welcome(controller, monkeypatch):
    monkeypatch.setattr(app_module.QTimer, "singleShot", lambda *_: None)
    controller.baseline = None
    controller.cfg["welcome_seen"] = True
    controller._show_welcome = Mock()
    controller._open_main_window = Mock()
    app_module.ShrimplyApp.start(controller, background=True)
    controller._show_welcome.assert_not_called()
    controller._open_main_window.assert_not_called()


@pytest.mark.parametrize("mode,expected", [
    ("normal", "good"), ("paused", "paused"), ("sleep", "sleeping"),
    ("idle", "idle"), ("calibration", "calibrating"),
    ("uncalibrated", "uncalibrated"), ("missing", "starting"),
    ("camera", "camera_error"), ("break", "break"),
])
def test_tray_snapshot_reflects_tracking_availability(controller, mode, expected):
    controller._display_deviation = .2
    if mode == "paused":
        controller.machine.pause()
    elif mode == "sleep":
        controller._suspended = True
    elif mode == "idle":
        controller._idle_stopped = True
    elif mode == "calibration":
        controller._cal = CalibrationSession()
    elif mode == "uncalibrated":
        controller.baseline = None
    elif mode == "missing":
        controller._display_deviation = None
    elif mode == "camera":
        controller.machine.camera_failed()
    elif mode == "break":
        controller.breaks.take_break(0.)
    app_module.ShrimplyApp._refresh_tray(controller)
    controller.tray.set_state.assert_called_once_with(expected, "")


def test_tray_break_summary_distinguishes_sitting_time_and_countdown(controller, monkeypatch):
    monkeypatch.setattr(app_module.time, "monotonic", lambda: 30.)
    controller._display_deviation = .2
    refresh = lambda: app_module.ShrimplyApp._refresh_tray(controller)
    refresh()
    controller.tray.set_break_text.assert_called_with("Next break · 40 min of sitting")
    controller.breaks.snooze()
    refresh()
    controller.tray.set_break_text.assert_called_with("Snoozed · 5 min of sitting")
    controller.breaks.take_break(0.)
    refresh()
    controller.tray.set_break_text.assert_called_with("Break · 1:30 remaining")
    controller.breaks.configure(False, 2400)
    refresh()
    controller.tray.set_break_text.assert_called_with("")


def test_break_reminder_counts_raw_presence_and_suggests_once(controller, monkeypatch):
    clock = [0.]
    monkeypatch.setattr(app_module.time, "monotonic", lambda: clock[0])
    controller.breaks = BreakReminder(True, 3)
    controller.break_prompt.isVisible.return_value = False
    for second in range(4):
        clock[0] = float(second)
        controller._on_frame(good_frame())
    assert controller.breaks.pending
    controller.break_prompt.set_suggestion.assert_called_once()
    controller.break_prompt.show.assert_called()
    controller.hud.set_break_prompt_visible.assert_called_with(True)
    clock[0] = 4.
    controller._on_frame(FrameSignals(ok=False))
    controller.break_prompt.hide.assert_called()
    controller.hud.set_break_prompt_visible.assert_called_with(False)
    assert controller.breaks.elapsed == 3
    clock[0] = 20.
    controller._on_frame(good_frame())
    assert controller.breaks.elapsed == 3
    controller.break_prompt.set_suggestion.assert_called_once()


@pytest.mark.parametrize("mode", ["paused", "sleep", "idle", "calibration", "camera", "restart", "stale"])
def test_due_break_prompt_hides_during_unavailable_tracking(controller, monkeypatch, mode):
    monkeypatch.setattr(app_module.time, "monotonic", lambda: 5.)
    controller.breaks = BreakReminder(True, 1)
    controller.breaks.observe(True, 4.)
    controller.breaks.observe(True, 5.)
    if mode == "paused":
        controller.machine.pause()
    elif mode == "sleep":
        controller._suspended = True
    elif mode == "idle":
        controller._idle_stopped = True
    elif mode == "calibration":
        controller._cal = CalibrationSession()
    elif mode == "camera":
        controller.machine.camera_failed()
    elif mode == "restart":
        controller._restart_pending = True
    else:
        monkeypatch.setattr(app_module.time, "monotonic", lambda: 10.)
    controller._reminder_fire()
    controller.break_prompt.show.assert_not_called()
    controller.break_prompt.hide.assert_called_once()
    assert controller.breaks.pending  # parked, not dismissed or sent repeatedly


def test_break_actions_and_disable_apply_without_changing_camera_state(controller):
    controller.breaks.pending = True
    controller._snooze_break(10)
    assert controller.breaks.remaining == 600
    controller._skip_break()
    assert controller.breaks.remaining == 2400
    controller._take_break()
    assert controller.breaks.in_break
    controller._end_break()
    assert controller.breaks.remaining == 2400
    controller.cfg["reminder_enabled"] = False
    controller.apply_breaks()
    assert not controller.breaks.enabled
    controller.worker.stop.assert_not_called()


def test_break_length_preference_changes_next_countdown(controller, monkeypatch):
    monkeypatch.setattr(app_module.time, "monotonic", lambda: 0.)
    app_module.ShrimplyApp.apply_preferences(controller, {"reminder_break_min": 5})
    assert controller.breaks.break_s == 300
    controller.break_prompt.set_break_minutes.assert_called_with(5)
    controller._take_break()
    assert controller.breaks.break_remaining(0.) == 300


def test_active_break_is_visible_while_away_and_expires_without_frames(controller, monkeypatch):
    clock = [0.]
    monkeypatch.setattr(app_module.time, "monotonic", lambda: clock[0])
    controller._take_break()
    controller.machine.state = State.AWAY
    clock[0] = 30.
    controller._reminder_fire()
    controller.break_prompt.set_break_state.assert_called_with(90.)
    clock[0] = 120.
    controller._reminder_fire()
    assert not controller.breaks.in_break
    controller.break_prompt.hide.assert_called()
    assert controller.breaks.remaining == 2400


def test_break_suppresses_posture_alerts_and_mascot(controller):
    from shrimply.core.states import EVENT_ALERT, EVENT_RENAG, EVENT_RECOVERED
    controller.breaks.take_break(0.)
    for event in (EVENT_ALERT, EVENT_RENAG, EVENT_RECOVERED):
        app_module.ShrimplyApp._handle_event(controller, event)
    controller._toast.assert_not_called()
    controller.hud.show_feedback.assert_not_called()
    controller._adapt(State.BAD, 2.)
    controller.mascot.force_hide.assert_called()
    controller.mascot.set_level.assert_not_called()


def test_sustained_posture_alert_shows_brief_meter_cue(controller):
    from shrimply.core.states import EVENT_ALERT, EVENT_RENAG
    app_module.ShrimplyApp._handle_event(controller, EVENT_ALERT)
    controller.hud.show_feedback.assert_called_once_with("Adjust posture")
    app_module.ShrimplyApp._handle_event(controller, EVENT_RENAG)
    controller.hud.show_feedback.assert_called_once()


@pytest.mark.parametrize("anchor,visible,bar_width", [
    (QRect(1100, 750, 230, 40), True, 230),
    (QRect(-50, 0, 270, 40), True, 270),
    (QRect(500, 400, 320, 80), True, 320),
    (QRect(500, 400, 311, 40), False, 311),
])
def test_break_prompt_matches_meter_and_stays_on_screen(controller, anchor, visible, bar_width):
    bounds = QRect(0, 0, 1280, 800)
    controller.break_prompt.isVisible.return_value = True
    controller.break_prompt.width.return_value = 340
    controller.break_prompt.height.return_value = 126
    controller.break_prompt.setFixedWidth.side_effect = lambda width: setattr(
        controller.break_prompt.width, "return_value", width)
    controller.hud.frameGeometry.return_value = anchor
    controller.hud.isVisible.return_value = visible
    controller.hud.bar.width.return_value = bar_width
    controller.hud.bar.height.return_value = 40
    controller.hud.screen.return_value.availableGeometry.return_value = bounds
    app_module.ShrimplyApp._position_break_prompt(controller)
    x, y = controller.break_prompt.move.call_args.args
    expected_width = bar_width if visible else 340
    assert controller.break_prompt.width() == expected_width
    assert bounds.contains(QRect(x, y, expected_width, 126))
    if visible and anchor.top() == 400:
        assert y == 448
    if visible and anchor.top() == 750:
        assert y == anchor.top() - 126 - 8


def test_vertical_meter_keeps_break_prompt_readable(controller):
    controller.break_prompt.isVisible.return_value = True
    controller.break_prompt.width.return_value = 340
    controller.break_prompt.height.return_value = 126
    controller.break_prompt.setFixedWidth.side_effect = lambda width: setattr(
        controller.break_prompt.width, "return_value", width)
    controller.hud.orientation = "vertical"
    controller.hud.isVisible.return_value = True
    controller.hud.bar.width.return_value = 78
    controller.hud.bar.height.return_value = 218
    controller.hud.frameGeometry.return_value = QRect(500, 200, 78, 218)
    controller.hud.screen.return_value.availableGeometry.return_value = QRect(0, 0, 1280, 800)
    app_module.ShrimplyApp._position_break_prompt(controller)
    assert controller.break_prompt.width() == 340


@pytest.mark.parametrize("paused,idle", [(False, False), (True, False), (False, True)])
def test_sleep_wake_restarts_capture_only_when_policy_allows(controller, monkeypatch, paused, idle):
    if paused:
        controller.machine.pause()
    controller._idle_stopped = idle
    old = controller.worker
    old.isRunning.return_value = True
    new = Mock()
    factory = Mock(return_value=new)
    monkeypatch.setattr(app_module, "VisionWorker", factory)
    controller._on_system_suspend()
    assert controller._suspended
    old.stop.assert_called()
    controller._on_frame(good_frame())
    controller._accumulate.assert_not_called()
    controller._restart_worker()
    factory.assert_not_called()
    controller._on_system_resume()
    assert not controller._suspended
    factory.assert_not_called()  # never overlap with the old worker
    assert controller._restart_pending is (not paused and not idle)
    old.isRunning.return_value = False
    controller._on_worker_finished()
    assert factory.call_count == (0 if paused or idle else 1)
    if paused:
        assert controller.machine.state is State.PAUSED
    if not paused and not idle:
        new.start.assert_called_once()


def test_resume_after_quit_does_not_restart_worker(controller):
    controller._quitting = True
    controller._restart_worker = Mock()
    controller._on_system_resume()
    controller._restart_worker.assert_not_called()


def test_settings_opens_inside_main_and_reuses_page_until_done(controller, monkeypatch):
    import shrimply.ui.settings as settings

    dialog = Mock()
    factory = Mock(return_value=dialog)
    monkeypatch.setattr(settings, "SettingsDialog", factory)
    controller._reset_baseline = Mock()
    controller._open_settings()
    controller._open_settings()
    factory.assert_called_once_with(controller.cfg, controller, parent=controller.main_window.pages)
    assert controller.main_window.show_settings.call_count == 2
    dialog.setWindowFlags.assert_called_once_with(app_module.Qt.Widget)
    dialog.exec.assert_not_called()
    clear_reference = dialog.finished.connect.call_args_list[0].args[0]
    dialog.tabs.tabText.return_value = "Appearance"
    clear_reference(0)
    assert controller._settings_dlg is None
    assert controller._settings_page == "Appearance"
    controller.main_window.show_dashboard.assert_called_once_with(dialog)
    assert dialog.finished.connect.call_args_list[1].args[0] == dialog.deleteLater
    controller._open_settings()
    dialog.select_page.assert_called_with("Appearance")


def test_real_rate_policy_recovers_after_leaving_and_returning(controller, monkeypatch):
    app = controller
    clock = [0.]
    monkeypatch.setattr(app_module.time, "monotonic", lambda: clock[0])
    for now in (0., .5, 1.):
        clock[0] = now
        app._on_frame(good_frame())
    clock[0] = 20.
    app._on_frame(FrameSignals(ok=False))
    assert app.machine.state is State.AWAY
    assert app.worker.inference_interval == 2.
    for _ in range(5):
        clock[0] += app.worker.inference_interval
        app._on_frame(good_frame())
        if app.machine.state is State.GOOD:
            break
    assert app.machine.state is State.GOOD
    assert clock[0] <= 23.


@pytest.mark.parametrize("paused,idle", [(True, False), (False, True)])
def test_camera_selection_does_not_open_capture_while_stopped(controller, monkeypatch, paused, idle):
    if paused:
        controller.machine.pause()
    controller._idle_stopped = idle
    factory = Mock()
    monkeypatch.setattr(app_module, "VisionWorker", factory)
    controller._restart_worker()
    factory.assert_not_called()
    controller.worker.start.assert_not_called()


def test_replacement_waits_for_finished_and_preserves_preview(controller, monkeypatch):
    old = controller.worker
    old.isRunning.return_value = True
    new = Mock()
    factory = Mock(return_value=new)
    monkeypatch.setattr(app_module, "VisionWorker", factory)
    controller._cal = CalibrationSession()
    controller._restart_worker()
    factory.assert_not_called()
    assert controller._restart_pending
    old.isRunning.return_value = False
    controller._on_worker_finished()
    factory.assert_called_once()
    new.start.assert_called_once()
    assert new.preview_enabled is True
    old.wait.assert_not_called()


def test_camera_preview_reuses_window_without_resuming_paused_capture(controller, monkeypatch):
    controller.machine.pause()
    preview = Mock()
    factory = Mock(return_value=preview)
    monkeypatch.setattr(app_module, "CameraPreviewWindow", factory)
    for _ in range(2):
        app_module.ShrimplyApp.open_camera_preview(controller)
    factory.assert_called_once_with(controller)
    assert preview.show.call_count == 2
    controller.worker.start.assert_not_called()
    controller.worker.preview.connect.assert_called_once_with(preview.update_frame)


def test_camera_preview_is_reconnected_to_replacement_worker(controller, monkeypatch):
    controller._camera_preview = Mock()
    controller._camera_preview.isVisible.return_value = True
    new = Mock()
    monkeypatch.setattr(app_module, "VisionWorker", Mock(return_value=new))
    controller._restart_worker()
    assert new.preview_enabled is True
    new.preview.connect.assert_any_call(controller._camera_preview.update_frame)


def test_paused_preview_uses_capture_only_then_releases_on_close(controller, monkeypatch):
    controller.machine.pause()
    controller.cfg["tracking_paused"] = True
    preview = Mock()
    preview.isVisible.return_value = True
    controller._camera_preview = preview
    new = Mock()
    new.isRunning.return_value = False
    monkeypatch.setattr(app_module, "VisionWorker", Mock(return_value=new))
    controller._preview_changed()
    assert new.inference_enabled is False
    assert new.preview_enabled is True
    new.start.assert_called_once()
    assert controller.machine.state is State.PAUSED
    assert controller.cfg["tracking_paused"] is True
    controller._on_frame(good_frame())
    controller._accumulate.assert_not_called()
    preview.isVisible.return_value = False
    controller._preview_changed()
    assert new.preview_enabled is False
    new.stop.assert_called_once()
    assert new.start.call_count == 1


def test_pausing_with_preview_open_waits_for_worker_then_uses_capture_only(controller, monkeypatch):
    old = controller.worker
    old.isRunning.return_value = True
    controller._camera_preview = Mock()
    controller._camera_preview.isVisible.return_value = True
    new = Mock()
    factory = Mock(return_value=new)
    monkeypatch.setattr(app_module, "VisionWorker", factory)
    controller._on_pause_toggled(True)
    factory.assert_not_called()
    assert controller._restart_pending
    old.isRunning.return_value = False
    controller._on_worker_finished()
    assert new.inference_enabled is False
    assert controller.machine.state is State.PAUSED
    new.start.assert_called_once()


def test_sleep_wake_restores_preview_without_resuming_tracking(controller, monkeypatch):
    controller.machine.pause()
    controller._camera_preview = Mock()
    controller._camera_preview.isVisible.return_value = True
    old = controller.worker
    old.isRunning.return_value = True
    new = Mock()
    factory = Mock(return_value=new)
    monkeypatch.setattr(app_module, "VisionWorker", factory)
    controller._on_system_suspend()
    controller._preview_changed()
    factory.assert_not_called()
    controller._on_system_resume()
    assert controller._restart_pending
    old.isRunning.return_value = False
    controller._on_worker_finished()
    assert new.inference_enabled is False
    assert controller.machine.state is State.PAUSED


def test_calibration_while_paused_receives_samples_without_ordinary_scoring(controller):
    controller.machine.pause()
    controller._cal = CalibrationSession()
    controller._cal_step = Mock()
    controller._on_frame(good_frame())
    controller._cal_step.assert_called_once()
    controller._accumulate.assert_not_called()
    assert controller.breaks.remaining == 2400


def test_calibration_resets_alert_clocks_without_saving_a_manual_pause(controller, monkeypatch):
    controller.machine.update(2., 0.)
    assert controller.machine.state is State.BAD
    controller.worker.isRunning.return_value = True
    controller.start_calibration()
    assert controller.machine.state is State.PAUSED
    assert controller.cfg["tracking_paused"] is False
    config.save.assert_not_called()
    monkeypatch.setattr(app_module.time, "monotonic", lambda: 100.)
    controller._cancel_calibration()
    state, events = controller.machine.update(2., 101.)
    assert state is State.BAD and not events


def test_preview_error_does_not_unpause_or_emit_posture_alerts(controller):
    controller.machine.pause()
    controller._camera_preview = Mock()
    controller._camera_preview.isVisible.return_value = True
    controller._on_cam_error()
    assert controller.machine.state is State.PAUSED
    controller._handle_event.assert_not_called()


def test_stale_worker_signals_cannot_enter_a_new_calibration():
    class Worker(QObject):
        frame = Signal(object)
        preview = Signal(object)
        error = Signal()

    class Receiver(QObject):
        _on_frame = app_module.ShrimplyApp._on_frame
        _on_calibration_preview = app_module.ShrimplyApp._on_calibration_preview
        _on_cam_error = app_module.ShrimplyApp._on_cam_error

    receiver = Receiver()
    old, current = Worker(), Worker()
    receiver.worker = current
    receiver._quitting = receiver._suspended = receiver._restart_pending = False
    receiver._cal = object()
    receiver._cal_step = Mock()
    receiver.preview_win = Mock()
    old.frame.connect(receiver._on_frame)
    old.preview.connect(receiver._on_calibration_preview)
    old.error.connect(receiver._on_cam_error)
    current.frame.connect(receiver._on_frame)
    current.preview.connect(receiver._on_calibration_preview)
    old.frame.emit(good_frame())
    old.preview.emit(object())
    old.error.emit()
    receiver._cal_step.assert_not_called()
    receiver.preview_win.update_frame.assert_not_called()
    receiver.preview_win.camera_unavailable.assert_not_called()
    current.frame.emit(good_frame())
    current.preview.emit(object())
    receiver._cal_step.assert_called_once()
    receiver.preview_win.update_frame.assert_called_once()


def test_closing_preview_cancels_a_pending_camera_reopen(controller, monkeypatch):
    controller.machine.pause()
    controller._camera_preview = Mock()
    controller._camera_preview.isVisible.return_value = True
    controller.worker.isRunning.return_value = True
    factory = Mock()
    monkeypatch.setattr(app_module, "VisionWorker", factory)
    controller._preview_changed()
    assert controller._restart_pending
    controller._camera_preview.isVisible.return_value = False
    controller._preview_changed()
    assert not controller._restart_pending
    controller.worker.isRunning.return_value = False
    controller._on_worker_finished()
    factory.assert_not_called()


def test_opening_preview_during_tracking_keeps_scoring_continuity(controller):
    controller._camera_preview = Mock()
    controller._camera_preview.isVisible.return_value = True
    controller._restart_worker = Mock()
    controller._display_deviation = .4
    controller._preview_changed()
    controller._restart_worker.assert_not_called()
    controller._render.assert_not_called()
    assert controller._display_deviation == .4
    controller.worker.wake.assert_called_once()


def test_resetting_calibration_preserves_pause(controller):
    controller.machine.pause()
    app_module.ShrimplyApp._reset_baseline(controller)
    assert controller.baseline is None
    assert controller.machine.state is State.PAUSED
    controller.worker.start.assert_not_called()


def test_failed_reset_keeps_previous_calibration(controller, monkeypatch):
    original = controller.baseline
    controller.cfg["baseline"] = original.to_dict()
    monkeypatch.setattr(config, "save", Mock(side_effect=OSError("disk full")))
    warning = Mock()
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", warning)

    app_module.ShrimplyApp._reset_baseline(controller)

    assert controller.baseline is original
    assert controller.cfg["baseline"] == original.to_dict()
    assert controller.machine.state is State.GOOD
    warning.assert_called_once()


def test_pause_cancels_pending_restart(controller, monkeypatch):
    controller.worker.isRunning.return_value = True
    controller._restart_worker()
    assert controller._restart_pending
    controller._on_pause_toggled(True)
    factory = Mock()
    monkeypatch.setattr(app_module, "VisionWorker", factory)
    controller._on_worker_finished()
    factory.assert_not_called()
    assert not controller._restart_pending


def test_calibration_from_pause_keeps_tracking_paused_and_opens_preview(controller, monkeypatch):
    controller.machine.pause()
    new = Mock()
    monkeypatch.setattr(app_module, "VisionWorker", Mock(return_value=new))
    controller.start_calibration()
    assert controller.machine.state is State.PAUSED
    assert new.preview_enabled
    new.start.assert_called_once()


def test_skipping_setup_displays_tall_instruction(controller):
    controller._cal = CalibrationSession()
    controller._on_continue_anyway()
    assert controller._cal.phase == "tall"
    controller.preview_win.set_instruction.assert_called_with(*app_module._CAL_INSTRUCTIONS["enter_tall"])


@pytest.mark.parametrize("result,caption", [
    (StepResult("tall", "TALL 2/10s"), "Hold still · 2/10s"),
    (StepResult("normal", "Get ready · 3s", "No samples collected yet."), "Get ready · 3s"),
    (StepResult("normal", "Collection paused", "Keep your face visible."),
     "Collection paused · Keep your face visible."),
    (StepResult("setup", "3/5 · gaze", "Raise the camera."),
     "Checking your camera… · Raise the camera."),
])
def test_calibration_caption_prioritizes_countdown_and_actionable_problems(controller, result, caption):
    controller._cal = CalibrationSession()
    controller._apply_cal_result(result)
    controller.preview_win.set_caption.assert_called_once_with(caption)


def test_shutdown_defers_storage_close_until_worker_stops(controller):
    controller.worker.isRunning.return_value = True
    assert controller.shutdown() is False
    controller.log.close.assert_not_called()
    controller.worker.isRunning.return_value = False
    assert controller.shutdown() is True
    assert controller.shutdown() is True
    controller.log.close.assert_called_once()
    controller._flush_bucket.assert_called_once()


def test_quit_finishes_when_final_writes_fail(controller):
    controller.log.end_session.side_effect = sqlite3.OperationalError("database locked")
    controller.log.close.side_effect = sqlite3.OperationalError("database locked")
    config.save.side_effect = OSError("disk full")

    assert controller.shutdown() is True
    assert controller._shutdown_done
    controller.hud.hide.assert_called_once()


def test_resuming_opens_the_device_selected_while_paused(controller, monkeypatch):
    controller.machine.pause()
    controller.cfg["camera_index"] = 2
    new = Mock()
    factory = Mock(return_value=new)
    monkeypatch.setattr(app_module, "VisionWorker", factory)
    controller._restart_worker()
    factory.assert_not_called()
    controller._on_pause_toggled(False)
    factory.assert_called_once_with("models", 2, controller.cfg["fps"])
    new.start.assert_called_once()


def test_camera_failure_hides_stale_feedback(controller):
    controller._good_streak = 10
    controller._on_cam_error()
    controller.mascot.force_hide.assert_called_once()
    assert controller._good_streak == 0
    assert controller.machine.state is State.CAMERA_ERROR


def test_stopping_message_clears_only_when_paused_worker_finishes(controller):
    controller.worker.isRunning.return_value = True
    controller._on_pause_toggled(True)
    controller.hud.set_status.assert_called_with("paused", "stopping camera")
    controller._on_worker_finished()
    controller._render.assert_called_with(State.PAUSED, None)


def test_calibration_failure_explicitly_reports_previous_baseline_retained(controller, monkeypatch):
    controller._cal = CalibrationSession()
    controller._apply_cal_result(StepResult("failed", hint="Poses were too similar"))
    assert controller._cal is None
    assert controller.worker.preview_enabled is False
    controller.preview_win.show_result.assert_called_once()
    success, message = controller.preview_win.show_result.call_args.args
    assert not success
    assert "previous calibration is still active" in message
    assert "Poses were too similar" in message


def test_successful_calibration_waits_for_explicit_start(controller):
    controller._cal = CalibrationSession()
    controller._accept_baseline = MethodType(app_module.ShrimplyApp._accept_baseline, controller)
    built = Baseline(signals={"head_pitch": SignalCal(4., 9., 1)})
    controller._apply_cal_result(StepResult("done", events=["calibrated"], baseline=built))
    assert controller.baseline is built
    assert controller._cal is None
    assert controller.machine.state is State.PAUSED
    assert controller.cfg["tracking_paused"]
    assert controller.cfg["baseline"] == built.to_dict()
    controller.worker.stop.assert_called_once()
    assert not controller.worker.preview_enabled
    assert controller.preview_win.show_result.call_args.args[0] is True
    controller._restart_worker = Mock()
    controller._start_after_calibration()
    assert controller.machine.state is not State.PAUSED
    assert not controller.cfg["tracking_paused"]
    controller._restart_worker.assert_called_once()
    controller.preview_win.hide.assert_called_once()
    controller.main_window.show.assert_called_once()


def test_failed_calibration_write_keeps_previous_baseline_and_finishes_flow(controller):
    old = controller.baseline
    controller.cfg["baseline"] = old.to_dict()
    controller._cal = CalibrationSession()
    controller._accept_baseline = MethodType(app_module.ShrimplyApp._accept_baseline, controller)
    config.save.side_effect = OSError("disk full")
    candidate = Baseline(signals={"head_pitch": SignalCal(4., 9., 1)})

    controller._apply_cal_result(StepResult("done", events=["calibrated"], baseline=candidate))

    assert controller.baseline is old
    assert controller.cfg["baseline"] == old.to_dict()
    assert controller._cal is None
    assert controller.worker.preview_enabled is False
    assert controller.preview_win.show_result.call_args.args[0] is False
    assert "not saved" in controller.preview_win.show_result.call_args.args[1]


@pytest.mark.parametrize("mode", ["missing_baseline", "calibrating"])
def test_start_after_calibration_requires_saved_result(controller, mode):
    if mode == "missing_baseline":
        controller.baseline = None
    else:
        controller._cal = CalibrationSession()
    controller._on_pause_toggled = Mock()
    controller._start_after_calibration()
    controller._on_pause_toggled.assert_not_called()
    controller.preview_win.hide.assert_not_called()
    controller.main_window.show.assert_not_called()


def test_dismissing_first_run_keeps_camera_off(controller, monkeypatch):
    from shrimply.ui import welcome

    dialog = Mock()
    dialog.exec.return_value = False
    monkeypatch.setattr(welcome, "WelcomeDialog", Mock(return_value=dialog))
    controller.baseline = None
    app_module.ShrimplyApp._show_welcome(controller)
    assert controller.machine.state is State.PAUSED
    assert controller.cfg["tracking_paused"]
    controller.worker.start.assert_not_called()


def test_startup_keeps_calibration_in_front(controller, monkeypatch):
    monkeypatch.setattr(app_module.QTimer, "singleShot", lambda *_: None)
    controller.baseline = None
    controller._show_welcome = lambda: setattr(controller, "_cal", CalibrationSession())
    app_module.ShrimplyApp.start(controller)
    controller.main_window.show.assert_not_called()


@pytest.mark.parametrize("paused", [False, True])
def test_cancel_calibration_keeps_saved_baseline_and_restores_pause(controller, paused):
    original = controller.baseline
    controller._cal = CalibrationSession()
    controller._cal_was_paused = paused
    controller._cancel_calibration()
    assert controller.baseline is original
    assert controller._cal is None
    assert not controller.worker.preview_enabled
    controller.preview_win.stop_preview.assert_called_once()
    controller.preview_win.hide.assert_called_once()
    assert (controller.machine.state is State.PAUSED) is paused


def test_duplicate_calibration_request_keeps_session_and_setup_override_is_scoped(controller):
    session = CalibrationSession()
    controller._cal = session
    controller.start_calibration()
    assert controller._cal is session
    controller.preview_win.raise_.assert_called_once()
    session.phase = "verify"
    controller._on_continue_anyway()
    assert session.phase == "verify"


def test_calibration_diagnostics_contain_only_numeric_signals(controller, monkeypatch):
    from shrimply import diag

    sample = Mock()
    monkeypatch.setattr(diag, "sample", sample)
    controller._cal = CalibrationSession()
    controller._cal_step(good_frame())
    assert sample.call_args.args == ("calibration",)
    fields = sample.call_args.kwargs
    assert fields["phase"] == "setup"
    assert fields["head_pitch"] == 5.
    assert all(value is None or isinstance(value, (str, bool, float, int)) for value in fields.values())


def test_history_tracks_rate_changes_and_flushes_once(controller, monkeypatch, tmp_path):
    from shrimply.storage.db import PostureLog

    clock = [0.]
    base = PostureLog._day_start(app_module.time.time()) + 12 * 3600
    monkeypatch.setattr(app_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(app_module.time, "time", lambda: base + clock[0])
    controller.log = PostureLog(tmp_path / "log.db")
    for name in ("_accumulate", "_flush_bucket"):
        setattr(controller, name, MethodType(getattr(app_module.ShrimplyApp, name), controller))
    for second in range(30):
        clock[0] = float(second)
        controller._accumulate(State.GOOD, .2)
    clock[0] = 30.
    controller._accumulate(State.BAD, 2.)
    for tick in range(1, 121):
        clock[0] = 30 + tick / 4
        controller._accumulate(State.BAD, 2.)
    controller._flush_bucket()
    controller._flush_bucket()
    day = controller.log.today()
    assert day["seconds"] == pytest.approx(60.)
    assert day["pct_good"] == pytest.approx(50.)
    controller.log.close()


def test_failed_history_write_retains_pending_time(controller):
    controller.history.minutes[6000] = {"good": 1., "drifting": 0., "bad": 0.}
    controller.log.record_duration.side_effect = OSError("disk unavailable")
    with pytest.raises(OSError):
        app_module.ShrimplyApp._flush_bucket(controller)
    assert controller.history.minutes[6000]["good"] == 1.


def test_sqlite_failure_does_not_block_pause_and_retains_pending_time(controller):
    controller._flush_bucket = MethodType(app_module.ShrimplyApp._flush_bucket, controller)
    controller.history.minutes[6000] = {"good": 40., "drifting": 0., "bad": 0.}
    controller.log.record_duration.side_effect = sqlite3.OperationalError("database locked")

    controller._on_pause_toggled(True)

    assert controller.machine.state is State.PAUSED
    assert controller.history.minutes[6000]["good"] == 40.


def test_pausing_flushes_pending_history_without_waiting_for_next_frame(controller):
    controller._flush_bucket = MethodType(app_module.ShrimplyApp._flush_bucket, controller)
    controller.history.minutes[6000] = {"good": 40., "drifting": 0., "bad": 0.}

    controller._on_pause_toggled(True)

    controller.log.record_duration.assert_called_once_with(6000, 40., 0., 0.)
    assert controller.history.minutes == {}


def test_unscorable_frame_breaks_history_continuity(controller, monkeypatch):
    clock = [0.]
    monkeypatch.setattr(app_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(app_module.time, "time", lambda: 6000 + clock[0])
    controller._accumulate = MethodType(app_module.ShrimplyApp._accumulate, controller)
    controller._accumulate(State.GOOD, .2)
    clock[0] = 1.
    controller._on_frame(FrameSignals(ok=False))
    clock[0] = 2.
    controller._accumulate(State.GOOD, .2)
    clock[0] = 3.
    controller._accumulate(State.GOOD, .2)
    assert controller.history.minutes[6000]["good"] == 1.
