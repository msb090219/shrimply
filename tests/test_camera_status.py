from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from shrimply.core.states import State
from shrimply.ui.status import camera_status, calibration_status, camera_mode


@pytest.fixture
def app_status():
    worker = Mock(camera_state="starting", camera_error="Device is busy.")
    worker.isRunning.return_value = True
    return SimpleNamespace(worker=worker, machine=SimpleNamespace(state=State.GOOD),
                           _restart_pending=False, _suspended=False, _idle_stopped=False,
                           _cal=None, baseline=None)


@pytest.mark.parametrize("worker_state,expected", [
    ("starting", "starting"), ("running", "running"), ("reconnecting", "reconnecting"),
])
def test_camera_thread_is_not_reported_as_processing_before_frames(app_status, worker_state, expected):
    app_status.worker.camera_state = worker_state
    state, detail = camera_status(app_status)
    assert state == expected
    if state == "reconnecting":
        assert "Device is busy." in detail and "permissions" in detail


@pytest.mark.parametrize("policy,running,expected", [
    ("paused", True, "stopping"), ("paused", False, "paused"),
    ("sleeping", True, "stopping"), ("sleeping", False, "off"),
    ("idle", False, "off"), ("restart", True, "reconnecting"),
    ("normal", False, "off"),
])
def test_camera_policy_overrides_old_worker_status(app_status, policy, running, expected):
    app_status.worker.camera_state = "running"
    app_status.worker.isRunning.return_value = running
    app_status.machine.state = State.PAUSED if policy == "paused" else State.GOOD
    app_status._suspended = policy == "sleeping"
    app_status._idle_stopped = policy == "idle"
    app_status._restart_pending = policy == "restart"
    assert camera_status(app_status)[0] == expected


def test_calibration_status_distinguishes_missing_saved_and_replacement(app_status):
    assert "Not calibrated" in calibration_status(app_status)
    app_status._cal = object()
    assert "No baseline has been saved" in calibration_status(app_status)
    app_status.baseline = SimpleNamespace(created_at=1700000000.)
    assert "saved baseline is kept" in calibration_status(app_status)
    app_status._cal = None
    assert calibration_status(app_status).startswith("Saved ")


@pytest.mark.parametrize("paused,mirror,calibrating,sleeping,idle,expected", [
    (True, False, False, False, False, "off"),
    (True, True, False, False, False, "preview"),
    (False, False, False, False, False, "tracking"),
    (False, True, False, False, False, "tracking"),
    (True, False, True, False, False, "calibration"),
    (False, True, True, True, False, "off"),
    (False, True, False, False, True, "preview"),
    (False, False, False, False, True, "off"),
])
def test_shared_camera_policy(app_status, paused, mirror, calibrating, sleeping, idle, expected):
    app_status.machine.state = State.PAUSED if paused else State.GOOD
    app_status._camera_preview = SimpleNamespace(isVisible=lambda: mirror)
    app_status._cal = object() if calibrating else None
    app_status._suspended = sleeping
    app_status._idle_stopped = idle
    assert camera_mode(app_status) == expected
    if expected == "preview":
        app_status.worker.camera_state = "running"
        state, detail = camera_status(app_status)
        assert state == "preview" and "no posture history" in detail
