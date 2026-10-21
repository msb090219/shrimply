"""Camera capture via OpenCV, paced to ~2 fps for OSA's needs.

Frames are processed in memory and never written to disk. The capture
backend is platform-appropriate: DirectShow on Windows (fast, reliable),
AVFoundation on macOS, the OS default elsewhere.
"""
from __future__ import annotations

import sys
import time
from typing import Iterator

import cv2
import numpy as np

if sys.platform == "win32":
    _BACKEND = cv2.CAP_DSHOW
elif sys.platform == "darwin":
    _BACKEND = cv2.CAP_AVFOUNDATION
else:
    _BACKEND = cv2.CAP_ANY


class CameraError(RuntimeError):
    """Raised when the camera can't be opened at all."""


class CameraNotReady(CameraError):
    """The backend opened a session but did not supply a first frame."""


class _MacCapture:
    """Resize in memory: changing AVFoundation output settings can stall capture."""

    def __init__(self, capture, width, height):
        self._capture = capture
        self._bounds = (width, height)
        self._size = (width, height)

    def read(self):
        ok, frame = self._capture.read()
        if ok and frame is not None:
            height, width = frame.shape[:2]
            scale = min(self._bounds[0] / width, self._bounds[1] / height, 1.)
            self._size = (max(1, round(width * scale)), max(1, round(height * scale)))
            if (width, height) != self._size:
                frame = cv2.resize(frame, self._size, interpolation=cv2.INTER_AREA)
        return ok, frame

    def get(self, prop):
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return self._size[0]
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return self._size[1]
        return self._capture.get(prop)

    def release(self):
        self._capture.release()


def open_camera(index: int = 0, width: int = 640, height: int = 480, *, warmup: bool = True) -> cv2.VideoCapture | _MacCapture:
    """Open a camera using the platform's preferred backend."""
    if sys.platform == "darwin":
        from AVFoundation import (
            AVCaptureDevice, AVMediaTypeVideo,
            AVAuthorizationStatusDenied, AVAuthorizationStatusRestricted,
        )

        permission = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeVideo)
        if permission == AVAuthorizationStatusDenied:
            owner = "Shrimply" if getattr(sys, "frozen", False) else "your terminal or Python application"
            raise CameraError(
                "Camera access was denied by macOS. Open System Settings → "
                f"Privacy & Security → Camera and enable {owner}, then reopen the app."
            )
        if permission == AVAuthorizationStatusRestricted:
            raise CameraError(
                "Camera access is restricted by macOS. Check Screen Time or "
                "contact the administrator managing this Mac."
            )
    cap = cv2.VideoCapture(index, _BACKEND)
    if not cap.isOpened():
        cap.release()
        raise CameraError(
            f"Could not open camera {index}. Is another app (Zoom/Teams) using it?"
        )
    try:
        # Changing a live AVFoundation output size intermittently stops frames.
        # Keep its native format and supply the requested size in memory.
        if sys.platform != "darwin" and (cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) != (width, height):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        # isOpened() only establishes a session, not a working video stream.
        deadline = time.perf_counter() + 2.
        while time.perf_counter() < deadline:
            ok, frame = cap.read()
            if ok and frame is not None:
                break
            time.sleep(.02)
        else:
            raise CameraNotReady("Camera opened but did not deliver a first frame")
        if warmup:
            warm_up(cap)
    except Exception:
        cap.release()
        raise
    return _MacCapture(cap, width, height) if sys.platform == "darwin" else cap


def warm_up(cap: cv2.VideoCapture, seconds: float = 1.5) -> None:
    """Read and discard frames so auto-exposure settles before anyone measures."""
    t_end = time.perf_counter() + seconds
    while time.perf_counter() < t_end:
        cap.read()


def paced_frames(
    cap: cv2.VideoCapture, fps: float = 2.0
) -> Iterator[tuple[int, np.ndarray | None]]:
    """Yield (ts_ms, bgr_frame_or_None) at ~fps with strictly increasing ts.

    A None frame means the read failed this tick (camera hiccup) — callers
    treat a streak of those as a camera error, a blip as "away".
    """
    interval = 1.0 / fps
    t0 = time.perf_counter()
    tick = 0
    while True:
        ok, frame = cap.read()
        ts_ms = int((time.perf_counter() - t0) * 1000) + 1  # +1: strictly increasing
        yield ts_ms, frame if ok else None
        tick += 1
        wake = t0 + tick * interval
        delay = wake - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
