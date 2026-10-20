"""Compare IMAGE and VIDEO pose predictions on identical, unsaved camera frames."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2

from shrimply.vision.camera import open_camera, paced_frames
from shrimply.vision.landmarks import ImageFormat, MpImage, Vision, mp
from shrimply.vision.metrics import LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER

POINTS = {"left_ear": LEFT_EAR, "right_ear": RIGHT_EAR,
          "left_shoulder": LEFT_SHOULDER, "right_shoulder": RIGHT_SHOULDER}
PHASES = ("normal", "shoulder_out", "normal_return")
WINDOW = "Shrimply pose comparison"


def pose_snapshot(result):
    """Keep raw required-point predictions; no images or inferred posture scores."""
    if not result.pose_landmarks:
        return {"found": False, "points": {}}
    landmarks = result.pose_landmarks[0]
    points = {}
    for name, index in POINTS.items():
        point = landmarks[index] if len(landmarks) > index else None
        values = {}
        for field in ("x", "y", "visibility", "presence"):
            value = getattr(point, field, None)
            values[field] = float(value) if value is not None and math.isfinite(value) else None
        points[name] = values
    return {"found": True, "points": points}


def compare_frame(rgb, timestamp, video, image):
    frame = MpImage(image_format=ImageFormat, data=rgb)
    # Both modes receive the same pixels, before the preview adds any annotations.
    return {"video": pose_snapshot(video.detect_for_video(frame, timestamp)),
            "image": pose_snapshot(image.detect(frame))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=8.)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("report already exists; choose a new path")
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("seconds must be finite and positive")

    samples, completed = [], []
    phase_index, start, failures = 0, None, 0
    with ExitStack() as cleanup:
        cap = open_camera(args.camera)
        cleanup.callback(cap.release)
        models = []
        for mode in (Vision.RunningMode.VIDEO, Vision.RunningMode.IMAGE):
            model = Vision.PoseLandmarker.create_from_options(Vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(ROOT / "models/pose_landmarker_lite.task")),
                running_mode=mode, num_poses=1))
            cleanup.callback(model.close)
            models.append(model)
        cleanup.callback(cv2.destroyAllWindows)
        for timestamp, frame in paced_frames(cap, 2.):
            if frame is None:
                failures += 1
                if failures >= 5:
                    raise RuntimeError("Camera stopped producing frames")
                continue
            failures = 0
            now = time.perf_counter()
            if start is not None and now - start >= args.seconds:
                completed.append(PHASES[phase_index])
                phase_index += 1
                start = None
                if phase_index == len(PHASES):
                    break
            phase = PHASES[phase_index]
            result = compare_frame(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), timestamp, *models)
            display = frame.copy()
            h, w = display.shape[:2]
            for mode, color in (("video", (0, 255, 0)), ("image", (255, 200, 0))):
                for name, point in result[mode]["points"].items():
                    x, y = point["x"], point["y"]
                    if x is not None and y is not None and 0 <= x <= 1 and 0 <= y <= 1:
                        position = (int(x * (w - 1)), int(y * (h - 1)))
                        cv2.circle(display, position, 4, color, 1)
                        if "shoulder" in name:
                            cv2.putText(display, name, position, cv2.FONT_HERSHEY_SIMPLEX, .35, color, 1)
            status = f"HOLD {max(0, args.seconds - (now - start)):.0f}s" if start is not None else "SPACE to start"
            cv2.putText(display, f"{phase}: {status} / ESC cancels", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 255), 1)
            cv2.putText(display, "VIDEO green / IMAGE blue", (8, 46), cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 255, 255), 1)
            cv2.imshow(WINDOW, display)
            key = cv2.waitKey(1) & 0xff
            if key == 27 or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
            if start is None and key == 32:
                start = time.perf_counter()
            if start is not None:
                samples.append({"phase": phase, "elapsed_s": round(max(0., now - start), 3), **result})

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump({"camera": args.camera, "fps": 2., "seconds_per_phase": args.seconds,
                   "completed_phases": completed, "samples": samples}, output, indent=2, allow_nan=False)
    print(f"Comparison complete: {completed}; {len(samples)} paired frames. Report: {args.report}")
    return 0 if len(completed) == len(PHASES) else 2


if __name__ == "__main__":
    raise SystemExit(main())
