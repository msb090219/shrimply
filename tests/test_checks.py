import json
from unittest.mock import Mock

import pytest

from tools.check_camera import summarize
from unshrimp import smoke


def test_camera_summary_does_not_confuse_detection_with_accuracy():
    result = summarize(2., [1., 1.5, 2.], [False, False, False], [], [3.], 3.2)
    assert result["ok"] is True
    assert result["usable_frames"] == 0
    assert result["stop_ms"] == 200.
    assert not summarize(2., [], [], ["error"], [3.], 3.2)["ok"]
    assert not summarize(2., [1., 2.], [True, True], [], [3.], 9.)["ok"]


@pytest.mark.parametrize("failure", [False, True])
def test_smoke_report_and_model_cleanup(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(smoke, "QImage", lambda _: Mock(isNull=lambda: False))
    landmarks = Mock()
    if failure:
        landmarks.signals.side_effect = RuntimeError("native model failed")
    monkeypatch.setattr(smoke, "Landmarkers", lambda _: landmarks)
    output = tmp_path / "report.json"
    code = smoke.run(tmp_path, output)
    result = json.loads(output.read_text())
    assert result["ok"] is (not failure)
    assert code == int(failure)
    landmarks.close.assert_called_once()
    with pytest.raises(FileExistsError):
        smoke.run(tmp_path, output)
