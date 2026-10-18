from types import SimpleNamespace
from unittest.mock import Mock
import json

import numpy as np
import pytest

from tools import compare_pose_modes as tool


def test_modes_receive_identical_image_and_keep_independent_raw_results():
    video, image = Mock(), Mock()
    points = [SimpleNamespace(x=.4, y=.5, visibility=.99, presence=.98) for _ in range(33)]
    points[11].x = -.05
    points[7].visibility = float("nan")
    video.detect_for_video.return_value = SimpleNamespace(pose_landmarks=[points])
    image.detect.return_value = SimpleNamespace(pose_landmarks=[])
    result = tool.compare_frame(np.zeros((8, 8, 3), dtype=np.uint8), 123, video, image)
    assert video.detect_for_video.call_args.args[0] is image.detect.call_args.args[0]
    assert video.detect_for_video.call_args.args[1] == 123
    assert result["video"]["points"]["left_shoulder"]["x"] == -.05
    assert result["video"]["points"]["left_ear"]["visibility"] is None
    assert result["image"] == {"found": False, "points": {}}
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("cancel", [False, True])
def test_continuous_stages_and_cleanup(tmp_path, monkeypatch, cancel):
    report = tmp_path / "comparison.json"
    monkeypatch.setattr(tool.sys, "argv", ["compare", "--seconds", "1", "--report", str(report)])
    cap, video, image = Mock(), Mock(), Mock()
    monkeypatch.setattr(tool, "open_camera", lambda _: cap)
    factory = Mock(side_effect=[video, image])
    monkeypatch.setattr(tool.Vision.PoseLandmarker, "create_from_options", factory)
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    monkeypatch.setattr(tool, "paced_frames", lambda *_: iter((i, frame) for i in range(4)))
    clock = iter([0., 0., 1., 1., 2., 2., 3.])
    monkeypatch.setattr(tool.time, "perf_counter", lambda: next(clock))
    comparison = Mock(return_value={"video": {"found": False, "points": {}},
                                    "image": {"found": False, "points": {}}})
    monkeypatch.setattr(tool, "compare_frame", comparison)
    monkeypatch.setattr(tool.cv2, "imshow", Mock())
    monkeypatch.setattr(tool.cv2, "waitKey", lambda _: 27 if cancel else 32)
    monkeypatch.setattr(tool.cv2, "getWindowProperty", lambda *_: 1)
    destroy = Mock()
    monkeypatch.setattr(tool.cv2, "destroyAllWindows", destroy)
    assert tool.main() == (2 if cancel else 0)
    data = json.loads(report.read_text())
    assert data["completed_phases"] == ([] if cancel else list(tool.PHASES))
    assert [sample["phase"] for sample in data["samples"]] == ([] if cancel else list(tool.PHASES))
    assert factory.call_count == 2  # models persist across all three stages
    cap.release.assert_called_once()
    video.close.assert_called_once()
    image.close.assert_called_once()
    destroy.assert_called_once()


def test_partial_model_initialization_releases_camera_and_first_model(tmp_path, monkeypatch):
    monkeypatch.setattr(tool.sys, "argv", ["compare", "--report", str(tmp_path / "report.json")])
    cap, model = Mock(), Mock()
    monkeypatch.setattr(tool, "open_camera", lambda _: cap)
    monkeypatch.setattr(tool.Vision.PoseLandmarker, "create_from_options", Mock(side_effect=[model, RuntimeError("model failure")]))
    with pytest.raises(RuntimeError, match="model failure"):
        tool.main()
    cap.release.assert_called_once()
    model.close.assert_called_once()
