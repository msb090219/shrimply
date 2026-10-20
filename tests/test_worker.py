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


def test_preview_only_captures_without_constructing_models_or_emitting_scores(monkeypatch):
    worker = worker_module.VisionWorker("models")
    worker.inference_enabled = False
    worker.preview_enabled = True
    cap = Mock()
    cap.read.return_value = (True, np.zeros((4, 4, 3), dtype=np.uint8))
    factory = Mock()
    monkeypatch.setattr(worker_module, "open_camera", lambda _: cap)
    monkeypatch.setattr(worker_module, "Landmarkers", factory)
    frames, previews = [], []
    worker.frame.connect(frames.append)
    worker.preview.connect(lambda payload: (previews.append(payload), worker.stop()))
    worker.run()
    factory.assert_not_called()
    assert not frames
    assert len(previews) == 1
    assert previews[0].ls is None and not previews[0].image.isNull()
    cap.release.assert_called_once()
