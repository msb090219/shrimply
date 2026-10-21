"""Short worker/camera lifecycle check. Saves counts and timings, never images."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtWidgets import QApplication
import config
import shrimply.vision.worker as worker_module
from shrimply.vision.worker import VisionWorker


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--seconds", type=int, default=8, help="Seconds per rate, including camera startup")
    parser.add_argument("--rates", nargs="+", type=float, default=[.5, 1., 2., 4.])
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "diagnostics" / f"camera-{time.time_ns()}.json")
    args = parser.parse_args()
    if args.camera < 0 or args.seconds < 5 or args.cycles < 1 or any(not math.isfinite(rate) or rate <= 0 for rate in args.rates):
        parser.error("Use a nonnegative camera, at least five seconds, and positive cycles/rates")
    if args.output.exists():
        parser.error("output already exists; choose a new report path")
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(str(config.APP_DIR / "instance.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        parser.error("Quit Shrimply before checking the camera so it has one owner")
    original_open, original_models = worker_module.open_camera, worker_module.Landmarkers
    stages = []
    reads = []
    def open_camera(index, **options):
        started = time.monotonic()
        try:
            cap = original_open(index, **options)
            def read():
                before = time.monotonic()
                ok, frame = cap.read()
                reads.append({"ok": bool(ok and frame is not None),
                              "ms": round(1000 * (time.monotonic() - before), 2)})
                return ok, frame
            return SimpleNamespace(read=read, release=cap.release)
        finally:
            stages.append({"stage": "camera_open_and_warmup", "ms": round(1000 * (time.monotonic() - started), 2)})
    def models(folder):
        started = time.monotonic()
        try:
            return original_models(folder)
        finally:
            stages.append({"stage": "model_load", "ms": round(1000 * (time.monotonic() - started), 2)})
    worker_module.open_camera, worker_module.Landmarkers = open_camera, models
    results = []
    for fps in args.rates * args.cycles:
        stages.clear()
        reads.clear()
        print(f"Camera {args.camera}: testing {fps:g} fps, then stopping capture", flush=True)
        worker = VisionWorker(ROOT / "models", args.camera, fps)
        worker.inference_enabled = not args.preview_only
        worker.preview_enabled = args.preview_only
        arrivals = []
        previews = []
        usable = []
        errors = []
        stop_requested = []
        worker.frame.connect(lambda sig: (arrivals.append(time.monotonic()), usable.append(sig.ok)))
        worker.preview.connect(lambda _: previews.append(time.monotonic()))
        worker.cam_error.connect(lambda: errors.append(worker.camera_error))
        worker.finished.connect(app.quit)
        def stop():
            stop_requested.append(time.monotonic())
            worker.stop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(stop)
        timer.start(args.seconds * 1000)
        started = time.monotonic()
        worker.start()
        app.exec()
        # Preserve the QThread owner until the native thread has fully returned.
        worker.wait()
        timer.stop()
        stopped = time.monotonic()
        outputs = previews if args.preview_only else arrivals
        row = summarize(fps, outputs, usable, errors, stop_requested, stopped)
        row.update(frames=len(arrivals), preview_frames=len(previews),
                   first_output_ms=round(1000 * (outputs[0] - started), 2) if outputs else None,
                   startup_stages=list(stages),
                   read_median_ms=round(statistics.median(r["ms"] for r in reads), 2) if reads else None,
                   read_max_ms=max((r["ms"] for r in reads), default=None),
                   failed_reads=[r for r in reads if not r["ok"]])
        results.append(row)
        print(json.dumps(row), flush=True)
    worker_module.open_camera, worker_module.Landmarkers = original_open, original_models
    lock.unlock()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as report:
        json.dump({"camera": args.camera, "results": results,
                   "scope": "worker health only; posture accuracy and physical camera light not verified"}, report, indent=2)
    print(f"Report: {args.output}")
    return 0 if all(row["ok"] for row in results) else 1


def summarize(fps, arrivals, usable, errors, stop_requested, stopped):
    gaps = [b - a for a, b in zip(arrivals, arrivals[1:])]
    stop_ms = (stopped - stop_requested[0]) * 1000 if stop_requested else None
    return {"requested_fps": fps, "frames": len(arrivals), "usable_frames": sum(usable),
            "max_delivery_gap_s": round(max(gaps), 3) if gaps else None,
            "stop_ms": round(stop_ms, 2) if stop_ms is not None else None,
            "errors": list(errors),
            "ok": len(arrivals) >= 2 and not errors and stop_ms is not None and stop_ms < 4000}


if __name__ == "__main__":
    raise SystemExit(main())
