"""Vision worker thread: camera + landmarkers → FrameSignals on a Qt signal.

Runs off the UI thread and survives camera loss by retrying every few
seconds, recreating the landmarkers whenever the camera reopens (MediaPipe
VIDEO mode needs monotonic timestamps per landmarker instance).

Two rates, decoupled: inference runs on the posture budget (default 2 fps)
while a calibration preview is open, the camera feed is emitted at up to
~15 fps so the mirror feels live. Without a preview the loop paces itself
to the inference rate exactly.
"""
from __future__ import annotations

import time
import threading
import traceback
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .camera import CameraError, open_camera
from .landmarks import Landmarkers
from .metrics import FrameSignals

_READ_FAIL_LIMIT = 5  # consecutive failed reads before declaring camera error
_RETRY_MS = 3000
_PREVIEW_FPS = 15.0


@dataclass
class PreviewPayload:
    """One preview frame for the calibration window. Landmarks may be None."""

    image: QImage  # already mirrored for selfie view
    ls: tuple[int, int] | None = None  # left shoulder (x, y) px
    rs: tuple[int, int] | None = None  # right shoulder
    le: tuple[int, int] | None = None  # left ear
    re: tuple[int, int] | None = None  # right ear


class VisionWorker(QThread):
    frame = Signal(object)  # FrameSignals (may be ok=False)
    preview = Signal(object)  # PreviewPayload, only while preview_enabled
    cam_error = Signal()
    cam_recovered = Signal()

    def __init__(self, models_dir: Path, camera_index: int = 0, fps: float = 2.0):
        super().__init__()
        self.models_dir = Path(models_dir)
        self.camera_index = camera_index
        self.fps = fps
        self.inference_interval = 1.0 / fps  # UI-adjustable (adaptive rates)
        self.preview_enabled = False  # plain bool flip from the UI thread
        self.inference_enabled = True  # set before starting; preview-only skips models
        self.camera_state = "starting"
        self.camera_error = ""
        self._stop = False
        self._wake = threading.Event()

    def stop(self) -> None:
        self._stop = True
        self._wake.set()

    def wake(self) -> None:
        self._wake.set()

    # ------------------------------------------------------------------
    def _emit_preview(self, rgb, overlay) -> None:
        h, w = rgb.shape[:2]
        img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        img = img.copy().mirrored(True, False)
        marks = overlay if overlay is not None else (None, None, None, None)
        self.preview.emit(PreviewPayload(img, *marks))

    def run(self) -> None:
        cap = None
        lm: Landmarkers | None = None
        in_error = False

        while not self._stop:
            try:
                cap = open_camera(self.camera_index)
                if self.inference_enabled:
                    lm = Landmarkers(self.models_dir)

                fails = 0
                t0 = time.perf_counter()
                last_ts = 0
                last_inf = -1e9
                last_prev = -1e9
                last_overlay: tuple | None = None

                while not self._stop:
                    capture_start = time.perf_counter()
                    ok, frame = cap.read()
                    now = time.perf_counter()
                    if self._stop:
                        break
                    if not ok or frame is None:
                        fails += 1
                        if fails >= _READ_FAIL_LIMIT:
                            raise CameraError("camera stopped producing frames")
                        continue
                    fails = 0

                    if not self.inference_enabled:
                        self.camera_state = "running"
                        self.camera_error = ""
                        if in_error:
                            self.cam_recovered.emit()
                            in_error = False
                        if self.preview_enabled:
                            self._emit_preview(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), None)
                        self._wake.wait(max(0, 1 / _PREVIEW_FPS - (time.perf_counter() - now)))
                        self._wake.clear()
                        continue

                    if now - last_inf >= self.inference_interval:
                        inference_start = time.perf_counter()
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        ts = int((now - t0) * 1000)
                        if ts <= last_ts:  # keep MediaPipe VIDEO ts strictly rising
                            ts = last_ts + 1
                        last_ts = ts

                        sig, overlay = lm.signals_with_overlay(rgb, ts)
                        sig = replace(sig, luminance=float(frame.mean()))
                        self.camera_error = ""
                        self.camera_state = "running"
                        from unshrimp import diag

                        diag.sample("vision", capture_ms=round((now - capture_start) * 1000, 2),
                                    inference_ms=round((time.perf_counter() - inference_start) * 1000, 2),
                                    ok=sig.ok, fps=round(1 / self.inference_interval, 2),
                                    pose_visibility=sig.pose_visibility,
                                    pose_presence=sig.pose_presence,
                                    rejection_reason=sig.rejection_reason)
                        if in_error:
                            self.cam_recovered.emit()
                            in_error = False
                        self.frame.emit(sig)
                        last_inf = now
                        last_overlay = overlay

                        if self.preview_enabled:
                            self._emit_preview(rgb, last_overlay)
                            last_prev = now
                        else:
                            # pace to the inference budget when nobody's watching
                            delay = (last_inf + self.inference_interval) - time.perf_counter()
                            if delay > 0:
                                self._wake.wait(delay)
                                self._wake.clear()
                    elif (
                        self.preview_enabled
                        and now - last_prev >= 1.0 / _PREVIEW_FPS
                    ):
                        self._emit_preview(
                            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), last_overlay
                        )
                        last_prev = now

            except Exception as e:
                if self._stop:
                    break
                self.camera_error = str(e) or type(e).__name__
                self.camera_state = "reconnecting"
                if not in_error:
                    from unshrimp import diag

                    diag.log(f"camera problem: {e} — retrying every few seconds")
                    diag.log(traceback.format_exc())
                    self.cam_error.emit()
                    in_error = True
            finally:
                try:
                    if cap is not None:
                        cap.release()
                finally:
                    if lm is not None:
                        lm.close()
                cap = None
                lm = None
            if not self._stop:
                self._wake.wait(_RETRY_MS / 1000)
                self._wake.clear()
        self.camera_state = "stopped"
