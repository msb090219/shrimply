"""Mac permission failures should explain recovery without opening capture."""
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import numpy as np

from shrimply.vision import camera


@pytest.mark.parametrize("status,expected", [
    (2, "Privacy & Security → Camera and enable Shrimply"),
    (1, "restricted by macOS"),
])
def test_mac_permission_failure_does_not_open_camera(monkeypatch, status, expected):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    native = SimpleNamespace(
        AVCaptureDevice=SimpleNamespace(authorizationStatusForMediaType_=Mock(return_value=status)),
        AVMediaTypeVideo="video", AVAuthorizationStatusDenied=2,
        AVAuthorizationStatusRestricted=1,
    )
    monkeypatch.setitem(sys.modules, "AVFoundation", native)
    capture = Mock()
    monkeypatch.setattr(camera.cv2, "VideoCapture", capture)
    with pytest.raises(camera.CameraError, match=expected):
        camera.open_camera()
    capture.assert_not_called()


@pytest.mark.parametrize("warmup", [True, False])
def test_authorized_mac_camera_uses_existing_capture_path(monkeypatch, warmup):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setitem(sys.modules, "AVFoundation", SimpleNamespace(
        AVCaptureDevice=SimpleNamespace(authorizationStatusForMediaType_=Mock(return_value=3)),
        AVMediaTypeVideo="video", AVAuthorizationStatusDenied=2,
        AVAuthorizationStatusRestricted=1,
    ))
    capture = Mock()
    capture.isOpened.return_value = True
    capture.read.return_value = (True, object())
    factory = Mock(return_value=capture)
    monkeypatch.setattr(camera.cv2, "VideoCapture", factory)
    settle = Mock()
    monkeypatch.setattr(camera, "warm_up", settle)
    opened = camera.open_camera(0, warmup=warmup)
    assert opened._capture is capture
    capture.set.assert_not_called()
    factory.assert_called_once_with(0, camera._BACKEND)
    assert settle.call_count == int(warmup)


def test_open_session_without_frames_is_released_before_models_can_start(monkeypatch):
    # Exercise readiness independently of native permission state.
    monkeypatch.setattr(camera.sys, "platform", "win32")
    cap = Mock()
    cap.isOpened.return_value = True
    clock = [0.]
    def read():
        clock[0] += 1.
        return False, None
    cap.read.side_effect = read
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda *_: cap)
    monkeypatch.setattr(camera.time, "perf_counter", lambda: clock[0])
    settle = Mock()
    monkeypatch.setattr(camera, "warm_up", settle)
    with pytest.raises(camera.CameraNotReady, match="first frame"):
        camera.open_camera()
    assert cap.read.call_count == 2
    cap.release.assert_called_once()
    settle.assert_not_called()


def test_matching_capture_size_does_not_reconfigure_stream(monkeypatch):
    monkeypatch.setattr(camera.sys, "platform", "win32")
    cap = Mock()
    cap.isOpened.return_value = True
    cap.get.side_effect = [640, 480]
    cap.read.return_value = (True, object())
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda *_: cap)
    assert camera.open_camera(warmup=False) is cap
    cap.set.assert_not_called()


@pytest.mark.parametrize("source_shape,output_shape", [
    ((720, 1280), (360, 640)),
    ((1280, 720), (480, 270)),
    ((480, 640), (480, 640)),
    ((240, 320), (240, 320)),
])
def test_mac_capture_preserves_ratio_and_failed_reads(source_shape, output_shape):
    native = Mock()
    image = np.full((*source_shape, 3), 123, dtype=np.uint8)
    native.read.side_effect = [(True, image), (False, None)]
    native.get.return_value = 30.
    capture = camera._MacCapture(native, 640, 480)
    ok, resized = capture.read()
    assert ok and resized.shape == (*output_shape, 3) and np.all(resized == 123)
    assert capture.read() == (False, None)
    assert capture.get(camera.cv2.CAP_PROP_FRAME_WIDTH) == output_shape[1]
    assert capture.get(camera.cv2.CAP_PROP_FRAME_HEIGHT) == output_shape[0]
    assert capture.get(camera.cv2.CAP_PROP_FPS) == 30.
    capture.release()
    native.release.assert_called_once()
    native.set.assert_not_called()
