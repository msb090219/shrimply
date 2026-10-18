"""Short worker/camera lifecycle check. Saves counts and timings, never images."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication, QTimer
from unshrimp.vision.worker import VisionWorker


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--seconds", type=int, default=8, help="Seconds per rate, including camera startup")
    parser.add_argument("--output", type=Path, default=ROOT / "diagnostics" / f"camera-{time.time_ns()}.json")
    args = parser.parse_args()
    if args.camera < 0 or args.seconds < 5:
        parser.error("camera must be nonnegative and seconds must be at least 5")
    if args.output.exists():
        parser.error("output already exists; choose a new report path")
    app = QCoreApplication([])
    results = []
    for fps in (.5, 1., 2., 4.):
        print(f"Camera {args.camera}: testing {fps:g} fps, then stopping capture", flush=True)
        worker = VisionWorker(ROOT / "models", args.camera, fps)
        arrivals = []
        usable = []
        errors = []
        stop_requested = []
        worker.frame.connect(lambda sig: (arrivals.append(time.monotonic()), usable.append(sig.ok)))
        worker.cam_error.connect(lambda: errors.append("camera_or_inference_error"))
        worker.finished.connect(app.quit)
        def stop():
            stop_requested.append(time.monotonic())
            worker.stop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(stop)
        timer.start(args.seconds * 1000)
        worker.start()
        app.exec()
        # Preserve the QThread owner until the native thread has fully returned.
        worker.wait()
        timer.stop()
        stopped = time.monotonic()
        row = summarize(fps, arrivals, usable, errors, stop_requested, stopped)
        results.append(row)
        print(json.dumps(row), flush=True)
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
