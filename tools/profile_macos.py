"""Measure production camera/widgets in short isolated runs; save numbers only."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import resource
import platform
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QEvent, QEventLoop, QLockFile, QTimer, Qt
from PySide6.QtWidgets import QApplication

import config
from shrimply.ui import theme
from shrimply.ui.hud import Hud
from shrimply.ui.mascot import MascotWindow
from shrimply.ui.preview import PreviewWindow
from shrimply.vision.worker import VisionWorker


def spin(seconds):
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.setTimerType(Qt.PreciseTimer)
    timer.timeout.connect(loop.quit)
    timer.start(max(1, round(seconds * 1000)))
    loop.exec()


def cpu_time():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


def load_baseline(folder, name, filename):
    spec = importlib.util.spec_from_file_location(name, folder / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=ROOT / "models")
    parser.add_argument("--seconds", type=float, default=8)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, help="Trusted snapshots of camera.py, worker.py and mascot.py")
    parser.add_argument("--modes", nargs="+", help="Run only the named modes")
    args = parser.parse_args()
    if args.seconds < 3 or args.output.exists():
        parser.error("Use at least three seconds and a fresh output path")
    worker_class, mascot_class = VisionWorker, MascotWindow
    if args.baseline_dir:
        camera = load_baseline(args.baseline_dir, "shrimply.vision._profile_camera", "camera.py")
        worker = load_baseline(args.baseline_dir, "shrimply.vision._profile_worker", "worker.py")
        worker.open_camera = camera.open_camera
        worker_class = worker.VisionWorker
        mascot_class = load_baseline(args.baseline_dir, "shrimply.ui._profile_mascot", "mascot.py").MascotWindow

    application = QApplication([])
    application.setQuitOnLastWindowClosed(False)
    lock = QLockFile(str(config.APP_DIR / "instance.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        parser.error("Quit Shrimply before profiling so the camera has one owner")
    theme.set_mode("dark")
    class MeasuredMascot(mascot_class):
        paints = 0
        paint_requests = 0
        def update(self, *args):
            self.paint_requests += 1
            super().update(*args)
        def paintEvent(self, event):
            self.paints += 1
            super().paintEvent(event)
    hud, mascot, preview = Hud(), MeasuredMascot(), PreviewWindow()
    modes = [
        ("paused", 0, False, True, None, True, False),
        ("tracking_steady", 1, False, True, .3, True, False),
        ("tracking_alert", 4, False, True, 2., True, False),
        ("away", .5, False, True, None, True, False),
        ("tracking_preview", 2, True, True, None, True, False),
        ("preview_only", 15, True, False, None, True, False),
        ("static_shrimp", 0, False, True, 2., False, False),
        ("bobbing_shrimp", 0, False, True, 2., True, False),
        ("reduced_motion_shrimp", 0, False, True, 2., True, True),
    ]
    if args.modes:
        unknown = set(args.modes) - {row[0] for row in modes}
        if unknown:
            parser.error(f"Unknown modes: {sorted(unknown)}")
        modes = [row for row in modes if row[0] in args.modes]
    report = {"scope": "Source worker and production Cocoa widgets; fixed rates; live input varies; no settings/history writes or saved frames",
              "variant": "baseline" if args.baseline_dir else "current", "ok": False,
              "python": sys.version, "platform": platform.platform(),
              "modes": [], "camera_setups": []}
    worker_module = sys.modules[worker_class.__module__]
    original_open = worker_module.open_camera
    def observe_open(index, **options):
        import cv2
        cap = original_open(index, **options)
        report["camera_setups"].append({
            "mode": name, "reported_fps": round(cap.get(cv2.CAP_PROP_FPS), 3),
            "width": cap.get(cv2.CAP_PROP_FRAME_WIDTH), "height": cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
        })
        return cap
    worker_module.open_camera = observe_open
    worker = None
    try:
        hud.show()
        for name, rate, show_preview, infer, level, bob, reduced in modes:
            mascot.force_hide()
            mascot.reduce_motion = reduced
            mascot.set_options(.87, "m", bob)
            mascot.set_level(level)
            hud.set_live(level, "") if level is not None else hud.set_status("paused" if not rate else "away", "")
            counts = {"frames": 0, "valid_frames": 0, "face_frames": 0,
                      "pose_frames": 0, "previews": 0, "animation_ticks": 0,
                      "camera_errors": 0}
            frame_times, preview_times = [], []
            def camera_error():
                counts["camera_errors"] += 1
            def tick():
                counts["animation_ticks"] += 1
            def frame(signals):
                frame_times.append(time.monotonic())
                counts["frames"] += 1
                counts["valid_frames"] += int(signals.ok)
                counts["face_frames"] += int(signals.face_found)
                counts["pose_frames"] += int(signals.pose_found)
                if level is not None:
                    hud.set_live(level, "")
                    mascot.set_level(level)
            def mirror(payload):
                preview_times.append(time.monotonic())
                counts["previews"] += 1
                preview.update_frame(payload)
            mascot._timer.timeout.connect(tick)
            if show_preview:
                preview.begin()
                preview.show()
            if rate:
                worker = worker_class(args.models, fps=rate)
                worker.inference_enabled, worker.preview_enabled = infer, show_preview
                worker.frame.connect(frame)
                worker.preview.connect(mirror)
                worker.cam_error.connect(camera_error)
                worker.start()
                deadline = time.monotonic() + 20
                while worker.camera_state != "running":
                    if time.monotonic() >= deadline:
                        raise RuntimeError(worker.camera_error or "Camera did not start")
                    spin(.05)
            spin(2)
            start_counts = dict(counts)
            before_paints = mascot.paints
            before_requests = mascot.paint_requests
            started, before = time.monotonic(), cpu_time()
            frame_times.clear()
            preview_times.clear()
            spin(args.seconds)
            used, elapsed = cpu_time() - before, time.monotonic() - started
            row = {"mode": name, "seconds": round(elapsed, 3),
                   "cpu_percent_one_logical_cpu": round(100 * used / elapsed, 2),
                   "animation_paints": mascot.paints - before_paints,
                   "animation_paint_requests": mascot.paint_requests - before_requests,
                   "animation_exposed": mascot.windowHandle().isExposed() if mascot.windowHandle() else False,
                   **{key: value - start_counts[key] for key, value in counts.items()}}
            row["camera_errors"] = counts["camera_errors"]  # include warmup interruptions
            for key, times in (("inference", frame_times), ("preview", preview_times)):
                row[key + "_fps"] = round(len(times) / elapsed, 2)
                # Include the edges so stalls at the beginning/end aren't hidden.
                boundaries = [started, *times, started + elapsed]
                row[key + "_max_gap_s"] = round(max(
                    b - a for a, b in zip(boundaries, boundaries[1:])), 3)
            report["modes"].append(row)
            print(json.dumps(row), flush=True)
            if worker is not None:
                if worker.camera_state != "running" or counts["camera_errors"]:
                    raise RuntimeError(worker.camera_error or "Camera interrupted during profiling")
                if (infer and not row["frames"]) or (show_preview and not row["previews"]):
                    raise RuntimeError("Camera produced no output during measurement")
            if worker is not None:
                worker.stop()
                if not worker.wait(10000):
                    raise RuntimeError("Worker did not stop")
                application.processEvents()
                worker.deleteLater()
                worker = None
            mascot._timer.timeout.disconnect(tick)
            preview.stop_preview()
            preview.hide()
            application.sendPostedEvents(None, QEvent.DeferredDelete)
        report["ok"] = True
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        if worker is not None:
            worker.stop()
            worker.wait()
        mascot.force_hide()
        preview.stop_preview()
        for window in (hud, mascot, preview):
            window.hide()
            window.deleteLater()
        application.sendPostedEvents(None, QEvent.DeferredDelete)
        lock.unlock()
        worker_module.open_camera = original_open
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
