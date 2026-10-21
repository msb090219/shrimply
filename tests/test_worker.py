"""Exercise the actual worker loop with fake capture and inference."""
from unittest.mock import Mock

import numpy as np
import pytest

import shrimply.vision.worker as worker_module
from shrimply.vision.metrics import FrameSignals


@pytest.mark.parametrize("stage", ["capture", "inference"])
def test_processing_failures_report_error_and_release_resources(monkeypatch, stage):
    worker = worker_module.VisionWorker("models")
    cap = Mock()
    cap.read.return_value = (True, np.zeros((4, 4, 3), dtype=np.uint8))
    lm = Mock()
    if stage == "capture":
        cap.read.side_effect = RuntimeError("driver failed")
    else:
        lm.signals_with_overlay.side_effect = ValueError("inference failed")
    monkeypatch.setattr(worker_module, "open_camera", lambda _: cap)
    monkeypatch.setattr(worker_module, "Landmarkers", lambda _: lm)
    monkeypatch.setattr(worker._wake, "wait", lambda _: worker.stop())
    errors = []
    worker.cam_error.connect(lambda: errors.append((worker.camera_state, worker.camera_error)))
    worker.run()
    assert len(errors) == 1 and errors[0][0] == "reconnecting"
    assert errors[0][1] == ("driver failed" if stage == "capture" else "inference failed")
    assert worker.camera_state == "stopped"
    cap.release.assert_called_once()
    lm.close.assert_called_once()


def test_worker_recovers_after_failure_only_when_inference_succeeds(monkeypatch):
    worker = worker_module.VisionWorker("models")
    first, second = Mock(), Mock()
    first.read.side_effect = RuntimeError("temporary failure")
    second.read.return_value = (True, np.zeros((4, 4, 3), dtype=np.uint8))
    lm = Mock()
    lm.signals_with_overlay.return_value = (FrameSignals(ok=False), None)
    monkeypatch.setattr(worker_module, "open_camera", Mock(side_effect=[first, second]))
    monkeypatch.setattr(worker_module, "Landmarkers", lambda _: lm)
    monkeypatch.setattr(worker._wake, "wait", lambda _: None)
    events = []
    states = []
    worker.cam_error.connect(lambda: events.append("error"))
    worker.cam_recovered.connect(lambda: events.append("recovered"))
    worker.frame.connect(lambda _: (states.append((worker.camera_state, worker.camera_error)), worker.stop()))
    worker.run()
    assert events == ["error", "recovered"]
    assert states == [("running", "")]
    first.release.assert_called_once()
    second.release.assert_called_once()
    assert lm.close.call_count == 2


def test_stop_interrupts_pacing_and_retry_waits():
    worker = worker_module.VisionWorker("models")
    worker.stop()
    assert worker._wake.wait(30.) is True


def test_no_first_frame_retries_quickly_without_loading_models(monkeypatch):
    worker = worker_module.VisionWorker("models")
    monkeypatch.setattr(worker_module, "open_camera", Mock(side_effect=worker_module.CameraNotReady("No first frame")))
    models = Mock()
    monkeypatch.setattr(worker_module, "Landmarkers", models)
    waits = []
    errors = []
    worker.cam_error.connect(lambda: errors.append(worker.camera_error))
    def wait(delay):
        waits.append(delay)
        worker.stop()
    monkeypatch.setattr(worker._wake, "wait", wait)
    worker.run()
    models.assert_not_called()
    assert waits == [.5]
    assert errors == []


def test_persistent_no_first_frame_is_reported_after_one_quick_startup_retry(monkeypatch):
    worker = worker_module.VisionWorker("models")
    monkeypatch.setattr(worker_module, "open_camera", Mock(side_effect=worker_module.CameraNotReady("No first frame")))
    waits, errors = [], []
    def wait(delay):
        waits.append(delay)
        if len(waits) == 2:
            worker.stop()
    monkeypatch.setattr(worker._wake, "wait", wait)
    worker.cam_error.connect(lambda: errors.append(worker.camera_error))
    worker.run()
    assert waits == [.5, .5]
    assert errors == ["No first frame"]


def test_stop_during_camera_open_does_not_load_models_before_releasing_capture(monkeypatch):
    worker = worker_module.VisionWorker("models")
    cap, models = Mock(), Mock()
    def open_camera(_):
        worker.stop()
        return cap
    monkeypatch.setattr(worker_module, "open_camera", open_camera)
    monkeypatch.setattr(worker_module, "Landmarkers", models)
    worker.run()
    models.assert_not_called()
    cap.read.assert_not_called()
    cap.release.assert_called_once()
    assert worker.camera_state == "stopped"


def test_repeated_failed_reads_report_outage_duration_and_release_capture(monkeypatch):
    worker = worker_module.VisionWorker("models")
    cap, models = Mock(), Mock()
    clock = [0.]
    def read():
        clock[0] += 1.
        return False, None
    cap.read.side_effect = read
    monkeypatch.setattr(worker_module.time, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(worker_module, "open_camera", lambda _: cap)
    monkeypatch.setattr(worker_module, "Landmarkers", lambda _: models)
    monkeypatch.setattr(worker._wake, "wait", lambda _: worker.stop())
    errors = []
    worker.cam_error.connect(lambda: errors.append(worker.camera_error))
    worker.run()
    assert errors == ["camera stopped producing frames: 5 failed reads over 5.00s"]
    cap.release.assert_called_once()
    models.close.assert_called_once()


def test_preview_only_captures_without_constructing_models_or_emitting_scores(monkeypatch):
    worker = worker_module.VisionWorker("models")
    worker.inference_enabled = False
    worker.preview_enabled = True
    cap = Mock()
    cap.read.return_value = (True, np.zeros((4, 4, 3), dtype=np.uint8))
    factory = Mock()
    open_camera = Mock(return_value=cap)
    monkeypatch.setattr(worker_module, "open_camera", open_camera)
    monkeypatch.setattr(worker_module, "Landmarkers", factory)
    frames, previews = [], []
    worker.frame.connect(frames.append)
    worker.preview.connect(lambda payload: (previews.append(payload), worker.stop()))
    worker.run()
    factory.assert_not_called()
    open_camera.assert_called_once_with(0, warmup=False)
    assert not frames
    assert len(previews) == 1
    assert previews[0].ls is None and not previews[0].image.isNull()
    cap.release.assert_called_once()


def test_preview_is_mirrored_and_owns_pixels_after_source_changes():
    worker = worker_module.VisionWorker("models")
    previews = []
    worker.preview.connect(previews.append)
    rgb = np.zeros((2, 3, 3), dtype=np.uint8)
    rgb[0, 0] = (123, 45, 67)
    worker._emit_preview(rgb, None)
    rgb[:] = 0
    assert previews[0].image.pixelColor(2, 0).getRgb() == (123, 45, 67, 255)
    assert previews[0].image.pixelColor(0, 0).getRgb() == (0, 0, 0, 255)


def test_preview_pacing_includes_time_spent_capturing(monkeypatch):
    worker = worker_module.VisionWorker("models")
    worker.inference_enabled = False
    worker.preview_enabled = True
    clock = [0.]
    cap = Mock()
    def read():
        clock[0] += .04
        return True, np.zeros((2, 3, 3), dtype=np.uint8)
    cap.read.side_effect = read
    waits = []
    def wait(delay):
        waits.append(delay)
        worker.stop()
    monkeypatch.setattr(worker_module.time, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(worker_module, "open_camera", lambda *_, **__: cap)
    monkeypatch.setattr(worker._wake, "wait", wait)
    worker.run()
    assert waits == pytest.approx([1 / worker_module._PREVIEW_FPS - .04])
