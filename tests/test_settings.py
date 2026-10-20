"""Rescanning must preserve device selection without restarting capture."""
import os
import copy
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
from PySide6.QtWidgets import QTabWidget

import config
from unshrimp.core.states import State
import unshrimp.ui.settings as settings


@pytest.fixture(scope="module")
def qt_app():
    previous = os.environ.get("QT_QPA_PLATFORM")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication([])
    yield app
    if previous is None:
        os.environ.pop("QT_QPA_PLATFORM", None)
    else:
        os.environ["QT_QPA_PLATFORM"] = previous


def test_rescan_does_not_emit_camera_change(qt_app, monkeypatch):
    cam = QComboBox()
    cam.addItems(["Camera 0", "Camera 2"])
    cam.setCurrentText("Camera 2")
    changed = Mock()
    cam.currentIndexChanged.connect(changed)
    monkeypatch.setattr(settings, "available_cameras", lambda skip: [0, 2, 3])
    button = QPushButton("Rescan")
    timer = Mock()
    timer.isActive.return_value = False
    dialog = SimpleNamespace(cam=cam, cfg={"camera_index": 2},
                             _live_cfg={"camera_index": 2}, _commit=lambda: True,
                             rescan_button=button, _rescan_timer=timer)
    settings.SettingsDialog._rescan(dialog)
    assert button.text() == "Scanning…"
    settings.SettingsDialog._finish_rescan(dialog)
    assert cam.currentText() == "Camera 2"
    assert button.text() == "Rescan"
    settings.SettingsDialog._rescan(dialog)
    settings.SettingsDialog._finish_rescan(dialog)
    assert button.text() == "Rescan"
    changed.assert_not_called()


def test_reduce_motion_preserves_saved_bobbing_preference(preferences):
    dialog, controller = preferences
    original = dialog.cfg["mascot_bob"]
    dialog.reduce_motion.setChecked(True)
    assert dialog.cfg["reduce_motion"] is True
    assert not dialog.mascot_bob.isEnabled()
    assert dialog.cfg["mascot_bob"] is original
    controller.apply_mascot_settings.assert_not_called()
    dialog.reduce_motion.setChecked(False)
    assert dialog.mascot_bob.isEnabled()


def test_mascot_entrance_saves_independently_and_restore_defaults(preferences):
    dialog, controller = preferences
    dialog.mascot_entrance.setCurrentIndex(dialog.mascot_entrance.findData("fade"))
    assert controller.cfg["mascot_entrance"] == "fade"
    assert controller.cfg["mascot_bob"] is True
    dialog.reduce_motion.setChecked(True)
    assert not dialog.mascot_entrance.isEnabled()
    assert controller.cfg["mascot_entrance"] == "fade"
    dialog.reduce_motion.setChecked(False)
    dialog.mascot_entrance.setCurrentIndex(dialog.mascot_entrance.findData("instant"))
    assert controller.cfg["mascot_entrance"] == "instant"
    dialog._restore_appearance()
    assert controller.cfg["mascot_entrance"] == "rise"


def test_text_cue_saves_updates_preview_and_restores_shrimp(preferences):
    dialog, controller = preferences
    dialog.mascot_style.setCurrentIndex(dialog.mascot_style.findData("text"))
    assert controller.cfg["mascot_style"] == "text"
    assert dialog.shrimp_preview.style == "text"
    dialog._restore_appearance()
    assert controller.cfg["mascot_style"] == "shrimp"
    assert dialog.shrimp_preview.style == "shrimp"


def test_mascot_response_delays_save_and_restore(preferences):
    dialog, controller = preferences
    dialog.mascot_bad_hold.setValue(0)
    dialog.mascot_recovery_hold.setValue(8)
    assert controller.cfg["mascot_bad_hold_s"] == 0
    assert controller.cfg["mascot_recovery_hold_s"] == 8
    dialog._restore_appearance()
    assert controller.cfg["mascot_bad_hold_s"] == 2
    assert controller.cfg["mascot_recovery_hold_s"] == 3


@pytest.fixture
def preferences(qt_app, monkeypatch):
    import unshrimp.autostart as autostart
    monkeypatch.setattr(autostart, "is_enabled", lambda: False)
    controller = Mock()
    controller.log.day_summaries.return_value = []
    controller.machine = SimpleNamespace(state=State.PAUSED)
    controller.worker.isRunning.return_value = False
    controller._suspended = controller._idle_stopped = controller._restart_pending = False
    controller._quitting = False
    controller._camera_preview = None
    controller._cal = controller.baseline = None
    controller.cfg = copy.deepcopy(config.DEFAULTS)
    def apply(changes, startup=None):
        for key, value in changes.items():
            if key == "hud":
                controller.cfg[key].update(value)
            else:
                controller.cfg[key] = copy.deepcopy(value)
    controller.apply_preferences.side_effect = apply
    dialog = settings.SettingsDialog(controller.cfg, controller)
    dialog.setAttribute(settings.Qt.WA_DontShowOnScreen)
    yield dialog, controller
    dialog._discard()
    dialog.deleteLater()
    qt_app.processEvents()


def test_settings_status_tracks_camera_recovery_and_saved_baseline(preferences, qt_app):
    from unshrimp.ui.status import calibration_status
    dialog, controller = preferences
    dialog.show()
    assert "Paused" in dialog.camera_status_label.text()
    assert not dialog.reset_button.isEnabled()
    assert dialog.status_timer.isActive()
    controller.machine.state = State.GOOD
    controller.worker.isRunning.return_value = True
    controller.worker.camera_state = "reconnecting"
    controller.worker.camera_error = "Camera busy."
    controller.baseline = SimpleNamespace(created_at=1700000000.)
    dialog.refresh_status()
    assert "Camera busy" in dialog.camera_status_label.text()
    assert not dialog.camera_retry.isHidden()
    dialog.camera_retry.click()
    controller.restart_camera.assert_called_once()
    assert dialog.camera_retry.text() == "Retrying…"
    assert dialog.baseline_status_label.text() == calibration_status(controller)
    assert dialog.reset_button.isEnabled()
    controller.worker.camera_state = "running"
    dialog.refresh_status()
    assert dialog.camera_retry.isHidden()
    assert dialog.camera_retry.text() == "Retry camera"
    dialog.hide()
    assert not dialog.status_timer.isActive()


def test_suggestion_editor_is_visible_inline(preferences, qt_app):
    dialog, controller = preferences
    dialog.select_page("Alerts and breaks")
    dialog.show()
    qt_app.processEvents()
    assert dialog.findChild(settings.QListWidget) is dialog.ex_list
    assert dialog.ex_list.isVisibleTo(dialog)
    controller.apply_breaks.assert_not_called()
    dialog.accept()
    qt_app.processEvents()


def test_settings_contains_only_configuration_and_can_open_a_specific_page(preferences):
    from unshrimp.ui.stats import StatsTab
    from unshrimp.ui.app import UnshrimpApp
    dialog, controller = preferences
    assert dialog.findChild(StatsTab) is None
    assert [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())] == [
        "Tracking", "Alerts and breaks", "Appearance", "General"]
    owner = SimpleNamespace(_open_settings=Mock(), _settings_dlg=dialog)
    UnshrimpApp._open_settings_page(owner, "Alerts and breaks")
    owner._open_settings.assert_called_once()
    assert dialog.tabs.currentIndex() == 1
    controller.apply_breaks.assert_not_called()
    controller.log.day_summaries.assert_not_called()


def test_settings_categories_and_aligned_horizontal_navigation(preferences):
    dialog, _ = preferences
    expected = {
        "Tracking": ["Camera", "Calibration", "Detection"],
        "Alerts and breaks": ["Posture alerts", "Break reminders", "Break suggestions", "Reminder preview"],
        "Appearance": ["Application theme", "Floating cue", "Posture meter"],
        "General": ["Startup", "About", "Data and support"],
    }
    assert dialog.tabs.tabBar().expanding()
    for index, (name, sections) in enumerate(expected.items()):
        page = dialog.tabs.widget(index).widget()
        assert dialog.tabs.tabText(index) == name
        assert page.layout().contentsMargins().left() == 0
        assert page.layout().contentsMargins().right() == 16
        assert [label.text() for label in page.findChildren(settings.QLabel, "sectionTitle")] == sections


def test_suggestion_editing_preserves_multiline_text_and_empty_list_state(preferences):
    dialog, controller = preferences
    dialog.cfg["exercises"] = []
    dialog._exercise_selected(-1)
    assert not dialog.ex_update.isEnabled()
    assert not dialog.ex_remove.isEnabled()
    dialog.ex_name.setText("Short walk")
    dialog.ex_how.setPlainText("Stand up comfortably.\nWalk around the room.")
    dialog._exercise_add()
    assert dialog.cfg["exercises"] == [{"name": "Short walk", "how": "Stand up comfortably.\nWalk around the room."}]
    assert dialog.ex_update.isEnabled()
    dialog.ex_name.setText("Walk and stretch")
    dialog._exercise_update()
    assert dialog.cfg["exercises"][0]["name"] == "Walk and stretch"
    assert len(dialog.cfg["exercises"]) == 1
    dialog._exercise_remove()
    assert dialog.cfg["exercises"] == []
    assert not dialog.ex_update.isEnabled()
    assert not dialog.ex_remove.isEnabled()
    assert not dialog.ex_name.text()
    assert not dialog.ex_how.toPlainText()
    controller.apply_breaks.assert_not_called()
    controller.restart_camera.assert_not_called()


def test_embedded_settings_reuses_main_window_without_probing_cameras(qt_app, monkeypatch):
    import unshrimp.autostart as autostart
    from unshrimp.ui import theme
    from unshrimp.ui.app import UnshrimpApp
    from unshrimp.ui.main_window import MainWindow

    probe = Mock(side_effect=AssertionError("Settings opening must not probe cameras"))
    monkeypatch.setattr(settings, "available_cameras", probe)
    monkeypatch.setattr(autostart, "is_enabled", lambda: False)
    controller = SimpleNamespace(cfg=copy.deepcopy(config.DEFAULTS), log=Mock(), hud=Mock(),
                                 _settings_dlg=None, _reset_baseline=Mock(), start_calibration=Mock(),
                                 worker=Mock(), machine=SimpleNamespace(state=State.PAUSED),
                                 _suspended=False, _idle_stopped=False, _restart_pending=False,
                                 _cal=None, baseline=None, open_camera_preview=Mock(), restart_camera=Mock(),
                                 _open_settings=Mock(), _open_settings_page=Mock())
    controller.apply_preferences = Mock()
    controller.log.day_summaries.return_value = []
    parent = controller.main_window = MainWindow(controller)
    parent.setAttribute(settings.Qt.WA_DontShowOnScreen)
    parent.resize(620, 600)
    try:
        UnshrimpApp._open_settings(controller)
        dialog = controller._settings_dlg
        qt_app.processEvents()
        assert dialog.isVisible()
        assert parent.isVisible()
        assert parent.pages.currentWidget() is dialog
        assert not dialog.isWindow()
        assert parent.settings_heading.text() == "Settings"
        assert parent.settings_heading.isVisible()
        assert parent.settings_button.isChecked()
        assert dialog.done_button.isHidden()
        assert parent.width() == 620
        tabs = dialog.findChild(QTabWidget)
        assert [tabs.tabText(i) for i in range(tabs.count())] == [
            "Tracking", "Alerts and breaks", "Appearance", "General"]
        assert all(tabs.widget(i).horizontalScrollBar().maximum() == 0
                   for i in range(tabs.count()))
        for width in (620, 960):
            parent.resize(width, 600)
            parent.pages.setCurrentWidget(parent.dashboard_page)
            qt_app.processEvents()
            dashboard_x = parent.dashboard_page.mapTo(
                parent.pages, QPoint(parent.dashboard_page.width(), 0)).x()
            parent.pages.setCurrentWidget(dialog)
            qt_app.processEvents()
            assert dialog.width() <= parent.pages.width()
            for index in range(tabs.count()):
                tabs.setCurrentIndex(index)
                qt_app.processEvents()
                scroll = tabs.widget(index)
                settings_x = scroll.mapTo(parent.pages, QPoint(scroll.width(), 0)).x()
                assert abs(settings_x - dashboard_x) <= 2
                card = scroll.widget().layout().itemAt(0).widget()
                assert card.mapTo(scroll.viewport(), QPoint(card.width(), 0)).x() <= scroll.viewport().width()
        tabs.setCurrentIndex(0)
        qt_app.processEvents()
        card = tabs.currentWidget().widget().layout().itemAt(0).widget()
        right = card.mapTo(tabs, QPoint(card.width(), 0)).x()
        image = tabs.grab().toImage()
        scale = image.devicePixelRatio()
        y = round(tabs.tabBar().geometry().bottom() * scale)
        assert image.pixelColor(round((right - 5) * scale), y) != image.pixelColor(round((right + 5) * scale), y)
        parent.resize(620, 600)
        previous_mode = theme.mode()
        try:
            theme.set_mode("light" if previous_mode == "dark" else "dark")
            assert all(theme.TEXT_MUTED in label.styleSheet()
                       for label in dialog._theme_muted_labels)
        finally:
            theme.set_mode(previous_mode)
        controller.log.day_summaries.assert_not_called()
        controller.apply_breaks = Mock()
        dialog.reminder_min.setValue(45)
        controller.apply_preferences.assert_called_once_with({"reminder_interval_min": 45}, startup=None)
        assert controller.cfg["reminder_interval_min"] == 40
        assert dialog.cfg["reminder_interval_min"] == 45
        controller.apply_breaks.assert_not_called()
        assert parent.isEnabled()
        probe.assert_not_called()
        parent.dashboard_button.click()
        controller.apply_preferences.assert_called_once_with({"reminder_interval_min": 45}, startup=None)
        assert controller._settings_dlg is None
        assert parent.pages.currentWidget() is parent.dashboard_page
        assert parent.dashboard_button.isChecked()
        parent.showMinimized()
        UnshrimpApp._open_settings(controller)
        assert parent.pages.currentWidget() is controller._settings_dlg
        assert not parent.isMinimized()
        parent.close()
        assert not parent.isVisible()
        assert controller._settings_dlg is None
    finally:
        parent.close()
        parent.deleteLater()


@pytest.mark.parametrize("measurement,expected", [
    ("legacy_samples", "older sample-based estimate"),
    ("time", "<1 min monitored"),
])
def test_stats_distinguish_timed_history_from_legacy(qt_app, measurement, expected):
    from unshrimp.ui.stats import StatsTab

    log = Mock()
    log.day_summaries.return_value = [{"ts": datetime.now().timestamp(), "pct_good": 50.,
                                     "minutes": .5, "measurement": measurement}]
    tab = StatsTab(log)
    tab.refresh()
    assert expected in tab.today_lbl.text()


def test_preferences_save_immediately_and_done_does_not_revert(preferences):
    dialog, controller = preferences
    original = copy.deepcopy(controller.cfg)
    dialog.hud_size.setCurrentIndex(2)
    dialog.mascot_op.setValue(40)
    dialog.reminder_min.setValue(55)
    assert controller.cfg != original
    assert dialog.hud_preview.bar.height() == 48
    assert dialog.shrimp_preview.opacity == .6
    assert controller.apply_preferences.call_count == 3
    dialog.done_button.click()
    assert controller.apply_preferences.call_count == 3
    assert controller.cfg["hud"]["size"] == "l"


def test_break_length_saves_and_updates_the_example(preferences):
    dialog, controller = preferences
    dialog.break_min.setValue(5)
    assert controller.cfg["reminder_break_min"] == 5
    assert "5-minute break" in dialog.reminder_sample.title.text()


def test_shrimp_positions_and_meter_transparency_save(preferences):
    dialog, controller = preferences
    for position in ("top_left", "top_right", "middle"):
        dialog.mascot_position.setCurrentIndex(dialog.mascot_position.findData(position))
        assert controller.cfg["mascot_position"] == position
    dialog.hud_op.setValue(40)
    assert controller.cfg["hud"]["opacity"] == .6
    assert dialog.hud_preview_opacity.opacity() == .6
    assert dialog.hud_op_label.text() == "40%"


def test_vertical_meter_setting_updates_roomy_previews_and_restores_default(preferences, qt_app):
    dialog, controller = preferences
    dialog.hud_orientation.setCurrentIndex(dialog.hud_orientation.findData("vertical"))
    qt_app.processEvents()
    assert controller.cfg["hud"]["orientation"] == "vertical"
    assert dialog.hud_preview.orientation == "vertical"
    assert dialog.hud_preview.height() >= dialog.hud_preview.shrimp.height() + 50
    assert dialog.reminder_meter_preview.orientation == "vertical"
    assert dialog.reminder_sample.width() >= 340
    dialog.defaults_button.click()
    assert controller.cfg["hud"]["orientation"] == "horizontal"
    assert dialog.hud_preview.orientation == "horizontal"


def test_camera_selection_applies_before_rescan_and_skips_selected_device(preferences, monkeypatch):
    dialog, controller = preferences
    dialog.cam.addItem("Camera 2")
    dialog.cam.setCurrentText("Camera 2")
    probe = Mock(return_value=[0, 1])
    monkeypatch.setattr(settings, "available_cameras", probe)
    dialog._rescan()
    assert dialog.rescan_button.text() == "Scanning…"
    dialog._rescan_timer.stop()
    dialog._finish_rescan()
    probe.assert_called_once_with(skip=2)
    assert dialog.cam.currentText() == "Camera 2"
    assert controller.cfg["camera_index"] == 2
    controller.restart_camera.assert_not_called()
    assert dialog.rescan_button.text() == "Rescan"


def test_save_commits_only_edited_fields_and_preserves_runtime_state(preferences):
    dialog, controller = preferences
    controller.cfg["baseline"] = {"new": "calibration"}
    controller.cfg["tracking_paused"] = True
    controller.cfg["hud"]["x"] = 321
    dialog.hud_size.setCurrentIndex(0)
    dialog.reminder_min.setValue(55)
    dialog.done_button.click()
    from unittest.mock import call
    assert controller.apply_preferences.call_args_list == [
        call({"hud": {"size": "s"}}, startup=None), call({"reminder_interval_min": 55}, startup=None)]
    assert controller.cfg["baseline"] == {"new": "calibration"}
    assert controller.cfg["tracking_paused"] is True
    assert controller.cfg["hud"]["x"] == 321
    assert dialog.result() == settings.QDialog.DialogCode.Accepted


def test_save_failure_restores_controls_and_reports_inline(preferences, monkeypatch):
    dialog, controller = preferences
    dialog.show()
    controller.apply_preferences.side_effect = OSError("Disk is full")
    report = Mock()
    monkeypatch.setattr(settings.QMessageBox, "critical", report)
    dialog.hud_size.setCurrentIndex(2)
    assert dialog.isVisible()
    assert dialog.cfg["hud"]["size"] == "m"
    assert dialog.hud_size.currentData() == "m"
    assert controller.cfg["hud"]["size"] == "m"
    assert "Disk is full" in dialog.save_status.text()
    report.assert_not_called()
    controller.apply_preferences.side_effect = None
    dialog.hud_size.setCurrentIndex(2)
    assert dialog.save_status.text() == "Changes saved"


@pytest.mark.parametrize("action", ["close", "reject", "accept"])
def test_close_preserves_saved_changes_without_prompt(preferences, monkeypatch, action):
    dialog, controller = preferences
    dialog.show()
    dialog.hud_size.setCurrentIndex(2)
    question = Mock(side_effect=AssertionError("No unsaved prompt"))
    monkeypatch.setattr(settings.QMessageBox, "question", question)
    getattr(dialog, action)()
    assert not dialog.isVisible()
    assert controller.cfg["hud"]["size"] == "l"
    question.assert_not_called()


def test_calibration_flushes_slider_and_stops_on_failed_save(preferences, monkeypatch):
    dialog, controller = preferences
    start = Mock()
    dialog.calibrate_requested.connect(start)
    dialog.sens.setSliderDown(True)
    dialog.sens.setValue(25)
    controller.apply_preferences.side_effect = OSError("No space")
    monkeypatch.setattr(settings.QMessageBox, "critical", Mock())
    dialog._calibrate()
    start.assert_not_called()
    assert dialog.sens.value() == round(config.DEFAULTS["sensitivity"] * 10)
    controller.apply_preferences.side_effect = None
    dialog._calibrate()
    start.assert_called_once()


def test_appearance_defaults_commit_once_and_do_not_reset_other_settings(preferences):
    dialog, controller = preferences
    dialog.mascot_size.setCurrentIndex(2)
    dialog.hud_compact.setChecked(True)
    controller.apply_preferences.reset_mock()
    dialog._restore_appearance()
    assert dialog.cfg["mascot_size"] == "m"
    assert dialog.cfg["mascot_opacity"] == .87
    assert dialog.cfg["hud"]["size"] == "m"
    assert not dialog.cfg["hud"]["compact"]
    controller.apply_preferences.assert_called_once()
    assert controller.apply_preferences.call_args.args[0]["hud"]["x"] is None
    assert "baseline" not in controller.apply_preferences.call_args.args[0]
    controller.restart_camera.assert_not_called()


def test_appearance_preview_timers_stop_when_hidden_or_reduced(preferences, qt_app):
    dialog, controller = preferences
    dialog.select_page("Appearance")
    dialog.show()
    qt_app.processEvents()
    assert dialog.shrimp_preview.timer.isActive()
    dialog.reduce_motion.setChecked(True)
    assert not dialog.shrimp_preview.timer.isActive()
    dialog.reduce_motion.setChecked(False)
    assert dialog.shrimp_preview.timer.isActive()
    dialog.select_page("Tracking")
    qt_app.processEvents()
    assert not dialog.shrimp_preview.timer.isActive()


def test_slider_drag_previews_without_writes_then_saves_on_release(preferences):
    dialog, controller = preferences
    dialog.mascot_op.setSliderDown(True)
    for value in (20, 30, 40):
        dialog.mascot_op.setValue(value)
    assert dialog.shrimp_preview.opacity == .6
    controller.apply_preferences.assert_not_called()
    dialog.mascot_op.setSliderDown(False)
    controller.apply_preferences.assert_called_once_with({"mascot_opacity": .6}, startup=None)
    dialog.mascot_op.setValue(41)
    assert controller.apply_preferences.call_count == 2


def test_disabled_controls_retain_choices_and_display_selection_is_always_visible(preferences):
    dialog, controller = preferences
    dialog.mascot_on.setChecked(False)
    assert not dialog.mascot_size.isEnabled()
    assert not dialog.mascot_screen.isHidden()
    assert dialog.mascot_screen.findData("*") >= 0
    dialog.mascot_on.setChecked(True)
    assert dialog.mascot_size.isEnabled()
    original = dialog.reminder_min.value()
    dialog.reminder.setChecked(False)
    assert not dialog.reminder_min.isEnabled()
    assert dialog.ex_list.isEnabled()
    dialog.reminder.setChecked(True)
    assert dialog.reminder_min.isEnabled()
    assert dialog.break_min.isEnabled()
    assert dialog.reminder_min.value() == original


def test_reminder_examples_and_tests_have_separate_effects(preferences, monkeypatch):
    dialog, controller = preferences
    from unshrimp.ui import app as app_module
    chime = Mock()
    monkeypatch.setattr(app_module, "_chime", chime)
    dialog.sound.setChecked(False)
    dialog.toasts.setChecked(False)
    controller.apply_preferences.reset_mock()
    dialog.select_page("Alerts and breaks")
    example = dialog.reminder_sample
    assert example.width() == dialog.reminder_meter_preview.bar.width()
    assert example.suggestion.text().startswith(dialog.cfg["exercises"][0]["name"])
    for signal in (example.take_requested, example.end_requested,
                   example.later_requested, example.skip_requested):
        signal.connect(Mock(side_effect=AssertionError("Examples must not emit live actions")))
    example.take_button.click()
    assert example._in_break
    assert not any("Example" in label.text() for label in example.findChildren(settings.QLabel))
    example.take_button.click()
    example.later_button.menu().actions()[1].trigger()
    assert "would remind" in dialog.preview_status.text()
    controller.tray.toast.assert_not_called()
    chime.assert_not_called()
    dialog._test_sound()
    chime.assert_called_once()
    dialog._test_notification()
    controller.tray.toast.assert_called_once()
    assert "requested" in dialog.test_status.text()
    assert not dialog.cfg["sound_on"] and not dialog.cfg["toasts_enabled"]
    controller.apply_preferences.assert_not_called()
    controller.restart_camera.assert_not_called()
    controller.log.day_summaries.assert_not_called()


def test_previews_align_left_and_reminder_matches_live_width(preferences, qt_app):
    dialog, _ = preferences
    for sample in (dialog.shrimp_preview, dialog.hud_preview):
        layout = sample.parentWidget().layout()
        assert layout.itemAt(layout.indexOf(sample)).alignment() == settings.Qt.AlignLeft

    dialog.select_page("Alerts and breaks")
    dialog.show()
    widths = []
    bar_widths = []
    for size in ("s", "m", "l"):
        dialog.hud_size.setCurrentIndex(dialog.hud_size.findData(size))
        qt_app.processEvents()
        assert dialog.reminder_sample.width() == dialog.reminder_meter_preview.bar.width()
        bar_widths.append(dialog.reminder_meter_preview.bar.width())
        buttons = dialog.reminder_sample.take_button, dialog.reminder_sample.later_button
        widths.append(buttons[0].width())
        assert abs(buttons[0].x() - (dialog.reminder_sample.width() - buttons[1].geometry().right() - 1)) <= 3
    assert widths == sorted(widths)
    assert widths[-1] > widths[0], f"button widths {widths}; bar widths {bar_widths}"

    previous_button_width = dialog.reminder_sample.take_button.width()
    dialog.reminder_sample.take_button.click()
    qt_app.processEvents()
    assert dialog.reminder_sample.take_button.width() > previous_button_width
    dialog.hud_visible.setChecked(False)
    qt_app.processEvents()
    assert dialog.reminder_meter_preview.isHidden()
    assert dialog.reminder_sample.width() == 340


def test_startup_failure_restores_os_state_control(preferences):
    dialog, controller = preferences
    if dialog.autostart is None:
        pytest.skip("Windows startup control")
    controller.apply_preferences.side_effect = OSError("Login permission denied")
    dialog.autostart.setChecked(True)
    assert not dialog.autostart.isChecked()
    assert "Login permission denied" in dialog.save_status.text()


def test_slider_focus_departure_flushes_and_numeric_enter_does_not_close(preferences, qt_app):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtTest import QTest
    dialog, controller = preferences
    dialog.show()
    dialog.sens.setSliderDown(True)
    dialog.sens.setValue(24)
    QApplication.sendEvent(dialog.sens, QFocusEvent(QEvent.FocusOut))
    controller.apply_preferences.assert_called_once_with({"sensitivity": 2.4}, startup=None)
    dialog.select_page("Alerts and breaks")
    dialog.grace.setFocus()
    QTest.keyClick(dialog.grace, settings.Qt.Key_Return)
    qt_app.processEvents()
    assert dialog.isVisible()


def test_failed_suggestion_edit_restores_saved_list(preferences):
    dialog, controller = preferences
    original = copy.deepcopy(dialog.cfg["exercises"])
    controller.apply_preferences.side_effect = OSError("No space")
    dialog.ex_name.setText("New walk")
    dialog._exercise_add()
    assert dialog.cfg["exercises"] == original
    assert dialog.ex_list.count() == len(original)
    assert controller.cfg["exercises"] == original
    assert "No space" in dialog.save_status.text()
