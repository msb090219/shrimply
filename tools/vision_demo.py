#!/usr/bin/env python3
"""M1 demo: prove the vision stack end-to-end on your webcam.

Prints the three posture signals live (~2 fps) to the console for a few
seconds. No frames are saved; --preview optionally displays them locally.

Usage:
    python tools/vision_demo.py [--seconds 20] [--camera 0] [--fps 2]
    python tools/vision_demo.py --list-cameras
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2

from shrimply.vision import camera as camera_mod
from shrimply.vision.camera import CameraError, open_camera, paced_frames, warm_up
from shrimply.vision.landmarks import Landmarkers


def list_cameras() -> None:
    print("Probing camera indices 0..3 (platform backend, after exposure warm-up)…")
    found = 0
    for i in range(4):
        cap = cv2.VideoCapture(i, camera_mod._BACKEND)
        if cap.isOpened():
            warm_up(cap, 2.0)
            ok, frame = cap.read()
            lum = f" mean-brightness={frame.mean():5.1f}" if ok and frame is not None else " (no frame)"
            print(f"  camera {i}: OPEN{lum}")
            found += 1
        cap.release()
    if not found:
        print("  none found")


def main() -> int:
    ap = argparse.ArgumentParser(description="Shrimply vision stack demo")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--list-cameras", action="store_true")
    ap.add_argument("--preview", action="store_true", help="Show framing; press Space to begin measuring, Esc to cancel")
    ap.add_argument("--report", type=Path, help="Save numerical measurements as JSON; no images")
    args = ap.parse_args()
    if args.report and args.report.exists():
        ap.error("report already exists; choose a new path")

    if args.list_cameras:
        list_cameras()
        return 0

    lm: Landmarkers | None = None
    cap = None
    stats = {"ok": 0, "no_person": 0, "unreliable": 0, "read_fail": 0, "total": 0}
    samples = []
    fail_streak = 0

    try:
        cap = open_camera(args.camera)
        lm = Landmarkers(ROOT / "models")
        print(f"Camera {args.camera} open. Watching for {args.seconds:.0f}s at {args.fps} fps…")
        print("(frames stay in memory — no images or video are saved)\n")

        t0 = time.perf_counter()
        measuring = not args.preview
        t_end = t0 + args.seconds
        for ts_ms, frame in paced_frames(cap, args.fps):
            if args.preview and frame is not None:
                display = frame.copy()
                label = "Measuring - hold position" if measuring else "Check framing; SPACE to start, ESC to cancel"
                cv2.putText(display, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 255, 255), 1)
                cv2.imshow("Shrimply framing check", display)
                key = cv2.waitKey(1) & 0xff
                if key == 27 or cv2.getWindowProperty("Shrimply framing check", cv2.WND_PROP_VISIBLE) < 1:
                    break
                if not measuring and key == 32:
                    measuring = True
                    t0 = time.perf_counter()
                    t_end = t0 + args.seconds
            if not measuring:
                continue
            if time.perf_counter() >= t_end:
                break
            elapsed = time.perf_counter() - t0
            stats["total"] += 1

            if frame is None:
                fail_streak += 1
                stats["read_fail"] += 1
                print(f"  t={elapsed:5.1f}s  [camera read failed ×{fail_streak}]")
                if fail_streak >= 5:
                    print("\nCamera stopped producing frames — aborting.")
                    break
                continue
            fail_streak = 0

            lum = frame.mean()
            sig = lm.signals(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), ts_ms)
            samples.append({"elapsed_s": round(elapsed, 3), "ok": sig.ok,
                            "face_found": sig.face_found, "pose_found": sig.pose_found,
                            "visibility": sig.pose_visibility, "presence": sig.pose_presence,
                            "rejection_reason": sig.rejection_reason})
            confidence = " ".join(
                f"{name}={value:.3f}" if value is not None else f"{name}=missing"
                for name, value in (("visibility", sig.pose_visibility), ("presence", sig.pose_presence)))
            if sig.ok:
                stats["ok"] += 1
                print(
                    f"  t={elapsed:5.1f}s  lum={lum:5.1f}  pitch={sig.head_pitch:+7.2f}°"
                    f"  yaw={sig.head_yaw:+7.2f}°  roll={sig.head_roll:+7.2f}°"
                    f"  sink={sig.head_sink:5.3f}  lean_in={sig.lean_in:5.3f}  {confidence}"
                )
            elif not sig.face_found or not sig.pose_found:
                stats["no_person"] += 1
                missing = []
                if not sig.face_found:
                    missing.append("face")
                if not sig.pose_found:
                    missing.append("pose")
                print(f"  t={elapsed:5.1f}s  lum={lum:5.1f}  [no {'+'.join(missing)} detected]")
            else:
                stats["unreliable"] += 1
                print(f"  t={elapsed:5.1f}s  lum={lum:5.1f}  [{sig.rejection_reason or 'unreliable landmarks or framing'}] {confidence}")

    except CameraError as e:
        print(f"ERROR: {e}")
        return 1
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        if args.preview:
            cv2.destroyAllWindows()
        if lm is not None:
            lm.close()
        if cap is not None:
            cap.release()

    print(
        f"\nSummary: {stats['ok']}/{stats['total']} frames scored "
        f"(no-person {stats['no_person']}, unreliable {stats['unreliable']}, "
        f"read-fail {stats['read_fail']})"
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as output:
            json.dump({"camera": args.camera, "fps": args.fps, "counts": stats,
                       "samples": samples}, output, indent=2)
        print(f"Numeric report: {args.report}")
    print("Vision stack OK." if stats["ok"] else "No frames scored — check lighting/framing.")
    return 0 if stats["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
