import json
from unittest.mock import Mock

import numpy as np
import pytest

from tools import vision_demo
from shrimply.vision.metrics import FrameSignals


@pytest.mark.parametrize("reliable", [True, False])
def test_numeric_report_records_quality_without_images(tmp_path, monkeypatch, reliable):
    report = tmp_path / "confidence.json"
    monkeypatch.setattr(vision_demo.sys, "argv", ["vision_demo", "--report", str(report)])
    cap, landmarks = Mock(), Mock()
    landmarks.signals.return_value = FrameSignals(
        ok=reliable, face_found=True, pose_found=True,
        head_pitch=0., head_yaw=0., head_roll=0., head_sink=.8, lean_in=.4,
        pose_visibility=.99 if reliable else .1, pose_presence=.99,
        rejection_reason=None if reliable else "pose_confidence")
    monkeypatch.setattr(vision_demo, "open_camera", lambda _: cap)
    monkeypatch.setattr(vision_demo, "Landmarkers", lambda _: landmarks)
    monkeypatch.setattr(vision_demo, "paced_frames", lambda *_: iter([(1, np.zeros((4, 4, 3), dtype=np.uint8))]))
    assert vision_demo.main() == (0 if reliable else 2)
    data = json.loads(report.read_text())
    assert data["samples"][0]["ok"] is reliable
    assert data["samples"][0]["visibility"] == (.99 if reliable else .1)
    assert data["samples"][0]["rejection_reason"] == (None if reliable else "pose_confidence")
    assert all(value is None or isinstance(value, (float, bool, str)) for value in data["samples"][0].values())
    cap.release.assert_called_once()
    landmarks.close.assert_called_once()


def test_preview_waits_for_space_and_cleans_up_on_escape(tmp_path, monkeypatch):
    report = tmp_path / "preview.json"
    monkeypatch.setattr(vision_demo.sys, "argv", ["vision_demo", "--preview", "--report", str(report)])
    cap, landmarks = Mock(), Mock()
    landmarks.signals.return_value = FrameSignals(ok=False, face_found=False)
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    monkeypatch.setattr(vision_demo, "open_camera", lambda _: cap)
    monkeypatch.setattr(vision_demo, "Landmarkers", lambda _: landmarks)
    monkeypatch.setattr(vision_demo, "paced_frames", lambda *_: iter([(1, frame), (2, frame), (3, frame)]))
    keys = iter([-1, 32, 27])
    monkeypatch.setattr(vision_demo.cv2, "waitKey", lambda _: next(keys))
    monkeypatch.setattr(vision_demo.cv2, "imshow", Mock())
    monkeypatch.setattr(vision_demo.cv2, "getWindowProperty", lambda *_: 1)
    cleanup = Mock()
    monkeypatch.setattr(vision_demo.cv2, "destroyAllWindows", cleanup)
    assert vision_demo.main() == 2
    assert json.loads(report.read_text())["counts"]["total"] == 1
    landmarks.signals.assert_called_once()
    cap.release.assert_called_once()
    landmarks.close.assert_called_once()
    cleanup.assert_called_once()
