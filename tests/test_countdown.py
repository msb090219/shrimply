import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from unshrimp.core.calibration import StepResult
from unshrimp.ui.countdown import ShrimpCountdown


@pytest.fixture
def countdown():
    app = QApplication.instance() or QApplication([])
    widget = ShrimpCountdown()
    widget.setAttribute(Qt.WA_DontShowOnScreen)
    widget.resize(448, 38)
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def progress(activity, elapsed, duration=8., pose=8.):
    return StepResult("normal", activity=activity, elapsed_s=elapsed,
                      duration_s=duration, pose_duration_s=pose)


def test_preparation_motion_never_advances_observed_time_and_stops_on_loss(countdown, monkeypatch):
    clock = [0.]
    monkeypatch.setattr("unshrimp.ui.countdown.time.monotonic", lambda: clock[0])
    countdown.set_progress(progress("preparing", 0., 3.))
    assert countdown.timer.isActive()
    clock[0] = 1.
    countdown.set_progress(progress("preparing", 1., 3.))
    assert countdown._wave_started_at == 0.
    clock[0] = 100.
    countdown._tick()
    assert countdown.remaining == 2
    countdown.set_progress(progress("paused", 1., 3.))
    assert countdown.remaining == 2 and countdown.slots == 12 and countdown.used_slots == 8
    assert not countdown.timer.isActive()


def test_capture_fades_without_reflow_and_reduced_motion_keeps_progress(countdown):
    countdown.set_progress(progress("capturing", 0.))
    size = countdown.size()
    countdown.set_progress(progress("capturing", 1.))
    assert countdown.remaining == 7 and countdown.slots == 12 and countdown.used_slots == 8
    assert countdown.timer.isActive()
    countdown.set_reduced_motion(True)
    assert not countdown.timer.isActive()
    assert countdown.remaining == 7 and countdown.size() == size
    assert countdown.accessibleDescription() == "7 seconds remaining"
    assert not countdown.grab().isNull()
    countdown.clear()
    assert countdown.isVisible() and not countdown.timer.isActive()
    assert countdown.used_slots == 0 and countdown.slots == 12


def test_hiding_and_camera_loss_stop_cosmetic_timers(countdown):
    countdown.set_progress(progress("preparing", 0., 3.))
    countdown.hide()
    assert not countdown.timer.isActive()
    countdown.show()
    assert countdown.timer.isActive()
    countdown.pause()
    assert not countdown.timer.isActive()
    assert countdown.remaining == 3


def test_quality_extension_does_not_show_negative_seconds(countdown):
    countdown.set_progress(progress("checking", 12., 10., 10.))
    assert countdown.remaining == 0
    assert not countdown.timer.isActive()
    assert not countdown.grab().isNull()


def test_slots_and_spacing_stay_fixed_across_setup_preparation_and_all_poses(countdown):
    countdown.clear()
    size = countdown.size()
    assert countdown.isVisible() and countdown.used_slots == 0
    for duration in (6., 8., 10., 12.):
        countdown.set_progress(progress("preparing", 0., 3., duration))
        assert countdown.slots == 12 and countdown.used_slots == duration
        countdown.set_progress(progress("capturing", 0., duration, duration))
        assert countdown.slots == 12 and countdown.remaining == duration
        countdown.set_progress(progress("capturing", duration, duration, duration))
        assert countdown.remaining == 0 and countdown.slots == 12
        assert countdown.size() == size
    countdown.set_progress(StepResult("setup"))
    assert countdown.slots == 12 and countdown.used_slots == 0
    assert countdown.isVisible()
