"""Verify real camera/preview lifecycle with isolated settings; never save frames."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback
import weakref
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "cocoa" if sys.platform == "darwin" else "offscreen")

from PySide6.QtCore import QEventLoop, QLockFile, QTimer
from PySide6.QtWidgets import QApplication
from PyInstaller.archive.readers import CArchiveReader

import config
from shrimply.ui.app import ShrimplyApp
import shrimply.ui.app as app_module
from shrimply.ui.status import camera_status
from shrimply.core.states import State


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--source-only", action="store_true", help="Use source models and skip packaged-bytecode verification")
    parser.add_argument("--unavailable-camera", type=int, default=9999)
    parser.add_argument("--executable", type=Path, default=ROOT / (
        "dist/macos-parity/Shrimply.app/Contents/MacOS/Shrimply" if sys.platform == "darwin"
        else "dist/shrimply/shrimply.exe"))
    parser.add_argument("--output", type=Path, default=ROOT / "diagnostics" / f"camera-ui-{time.time_ns()}.json")
    args = parser.parse_args()
    if args.camera < 0 or args.unavailable_camera < 0 or args.camera == args.unavailable_camera:
        parser.error("Choose distinct nonnegative camera and unavailable-camera indices")
    if args.output.exists():
        parser.error("Choose a fresh output path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    application = QApplication([])
    application.setQuitOnLastWindowClosed(False)
    lock = QLockFile(str(config.APP_DIR / "instance.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        parser.error("Quit Shrimply before running this camera check")
    report = {"camera": args.camera, "ok": False, "steps": [], "workers": [],
              "power_events": [], "qt_errors": [],
              "scope": ("Real camera in a source Qt host; "
                        + ("source only. " if args.source_only else "package bytecode compared. ")
                        + "No desktop automation or physical disconnect. No frames saved.")}
    previous_hook = sys.excepthook
    def qt_error(kind, value, tb):
        report["qt_errors"].append("".join(traceback.format_exception(kind, value, tb)))
        previous_hook(kind, value, tb)
    sys.excepthook = qt_error

    def record(name, **values):
        row = {"step": name, **values}
        report["steps"].append(row)
        print(json.dumps(row), flush=True)

    def wait_for(condition, name, seconds=20):
        if condition():
            return
        loop = QEventLoop()
        poll, deadline = QTimer(), QTimer()
        poll.setInterval(20)
        poll.timeout.connect(lambda: loop.quit() if condition() else None)
        deadline.setSingleShot(True)
        deadline.timeout.connect(loop.quit)
        poll.start()
        deadline.start(round(seconds * 1000))
        loop.exec()
        poll.stop()
        deadline.stop()
        if not condition():
            raise TimeoutError(name)

    observed = weakref.WeakKeyDictionary()
    def observe(worker):
        if worker in observed:
            return observed[worker]
        row = {"camera": worker.camera_index, "frames": 0, "previews": 0, "errors": 0,
               "error_messages": []}
        observed[worker] = row
        report["workers"].append(row)
        reference = weakref.ref(worker)
        def frame(_):
            row["frames"] += 1
        def preview(_):
            row["previews"] += 1
        def error():
            row["errors"] += 1
            current = reference()
            row["error_messages"].append(current.camera_error if current is not None else "worker released")
        worker.frame.connect(frame)
        worker.preview.connect(preview)
        worker.cam_error.connect(error)
        return row

    original_worker = app_module.VisionWorker
    def create_worker(*args, **kwargs):
        worker = original_worker(*args, **kwargs)
        observe(worker)
        return worker

    try:
        if args.source_only:
            models = ROOT / "models"
            record("source_only_no_package_verification")
        else:
            archive = CArchiveReader(str(args.executable))
            pyz = archive.open_embedded_archive(next(n for n, e in archive.toc.items() if e[-1] == "z"))
            modules = ["shrimply.ui.app", "shrimply.ui.main_window", "shrimply.ui.settings",
                       "shrimply.ui.preview", "shrimply.ui.status", "shrimply.vision.worker",
                       "shrimply.ui.countdown", "shrimply.ui.hud", "shrimply.core.calibration",
                       "shrimply.vision.camera", "config"]
            for name in modules:
                bundled = pyz.extract(name)
                source = (ROOT / (name.replace(".", "/") + ".py")).read_text(encoding="utf-8")
                assert compile(source, bundled.co_filename, "exec", dont_inherit=True) == bundled, f"Stale package module: {name}"
            record("package_matches_source", modules=len(modules))
            models = (args.executable.parent.parent / "Resources/models" if sys.platform == "darwin"
                      else args.executable.parent / "_internal/models")
        with tempfile.TemporaryDirectory(prefix="camera-ui-", dir=args.output.parent) as session:
            isolated = Path(session).resolve()
            assert isolated.is_relative_to(ROOT.resolve()), "Test data must remain inside the workspace"
            with (patch.object(config, "APP_DIR", isolated),
                  patch.object(config, "CONFIG_PATH", isolated / "config.json"),
                  patch.object(app_module, "VisionWorker", create_worker)):
                cfg = copy.deepcopy(config.DEFAULTS)
                cfg.update(camera_index=args.camera, tracking_paused=True, welcome_seen=True,
                           toasts_enabled=False, mascot_enabled=False, reminder_enabled=False, sound_on=False)
                cfg["hud"]["visible"] = False
                config.save(cfg)
                controller = ShrimplyApp(models)
                power_monitor = None
                try:
                    if sys.platform == "darwin":
                        from shrimply.ui.power import PowerMonitor
                        def suspend():
                            report["power_events"].append("suspend")
                            controller._on_system_suspend()
                        def resume():
                            report["power_events"].append("resume")
                            controller._on_system_resume()
                        power_monitor = PowerMonitor(controller.hud.winId(), suspend, resume)
                    controller._on_pause_toggled(True)
                    controller.open_camera_preview()
                    controller._open_settings()
                    mirror = controller._camera_preview
                    row = observe(controller.worker)
                    wait_for(lambda: camera_status(controller)[0] == "preview" and mirror.video.image is not None
                             and row["previews"] >= 2, "Paused preview did not deliver real frames")
                    assert controller.machine.state is State.PAUSED and controller.cfg["tracking_paused"]
                    assert not controller.worker.inference_enabled and row["frames"] == 0
                    record("preview_only_preserves_pause_without_inference", previews=row["previews"])
                    mirror.close()
                    wait_for(lambda: not controller.worker.isRunning(), "Closing paused preview did not release capture", 4)
                    assert mirror.video.image is None

                    old = controller.worker
                    controller.start_calibration()
                    wait_for(lambda: controller.worker is not old, "Calibration did not start a new worker")
                    row = observe(controller.worker)
                    wait_for(lambda: row["frames"] >= 2, "Calibration did not receive real inference")
                    assert controller.machine.state is State.PAUSED and controller.cfg["tracking_paused"]
                    assert not controller.history.minutes and controller.breaks.remaining == 2400
                    record("calibration_receives_frames_without_normal_tracking", frames=row["frames"])
                    controller._cancel_calibration()
                    wait_for(lambda: not controller.worker.isRunning(), "Cancelling paused calibration did not stop capture", 4)
                    assert controller.machine.state is State.PAUSED
                    controller.open_camera_preview()
                    wait_for(lambda: camera_status(controller)[0] == "preview" and mirror.video.image is not None,
                             "Preview did not reopen after calibration cancellation")

                    controller.main_window.refresh()
                    old = controller.worker
                    controller.tray.pause_action.trigger()
                    wait_for(lambda: controller.worker is not old, "Resuming tracking did not replace preview-only worker")
                    row = observe(controller.worker)
                    wait_for(lambda: camera_status(controller)[0] == "running" and mirror.video.image is not None
                             and row["previews"] >= 2, "Live preview did not receive real frames")
                    controller.main_window.refresh()
                    controller._settings_dlg.refresh_status()
                    assert camera_status(controller)[0] == "running"
                    assert controller._settings_dlg.camera_status_label.text().startswith("Running")
                    record("live_camera_and_shared_status", frames=row["frames"], previews=row["previews"])

                    mirror.close()
                    assert not controller.worker.preview_enabled and mirror.video.image is None
                    target = row["frames"] + 2
                    wait_for(lambda: row["frames"] >= target, "Closing preview stopped tracking")
                    assert mirror.video.image is None and not mirror.timer.isActive()
                    record("closing_preview_keeps_tracking_and_clears_image")
                    controller.open_camera_preview()
                    wait_for(lambda: mirror.video.image is not None, "Reopened preview stayed empty")

                    old = controller.worker
                    controller.cfg["camera_index"] = args.unavailable_camera
                    controller.restart_camera()
                    wait_for(lambda: controller.worker is not old and camera_status(controller)[0] == "reconnecting",
                             "Unavailable device did not enter reconnecting")
                    mirror.refresh()
                    controller.main_window.refresh()
                    controller._settings_dlg.refresh_status()
                    assert mirror.video.image is None and not mirror.retry_button.isHidden()
                    assert not controller.main_window.camera_retry.isHidden()
                    assert not controller._settings_dlg.camera_retry.isHidden()
                    record("unavailable_device_shows_retry_and_clears_image", detail=controller.worker.camera_error)

                    old = controller.worker
                    controller.cfg["camera_index"] = args.camera
                    mirror.retry_button.click()
                    wait_for(lambda: controller.worker is not old, "Retry did not replace the failed worker")
                    observe(controller.worker)
                    wait_for(lambda: camera_status(controller)[0] == "running" and mirror.video.image is not None,
                             "Retry did not recover the real webcam")
                    record("retry_recovers_real_camera_and_mirror")

                    for cycle in range(2):
                        controller.main_window.refresh()
                        old = controller.worker
                        controller.tray.pause_action.trigger()
                        wait_for(lambda: controller.worker is not old and camera_status(controller)[0] == "preview"
                                 and mirror.video.image is not None, "Pausing did not preserve preview-only capture")
                        assert not controller.worker.inference_enabled and controller.machine.state is State.PAUSED
                        record("pause_with_open_mirror_keeps_preview_only", cycle=cycle + 1)
                        started = time.monotonic()
                        mirror.close()
                        wait_for(lambda: not controller.worker.isRunning(), "Camera did not stop within four seconds", 4)
                        mirror.refresh()
                        assert camera_status(controller)[0] == "paused" and mirror.video.image is None
                        record("pause_releases_camera", cycle=cycle + 1, stop_ms=round((time.monotonic() - started) * 1000, 1))
                        if cycle == 0:
                            controller.open_camera_preview()
                            wait_for(lambda: camera_status(controller)[0] == "preview" and mirror.video.image is not None,
                                     "Paused preview failed to reopen")
                            controller.main_window.refresh()
                            old = controller.worker
                            controller.tray.pause_action.trigger()
                            wait_for(lambda: controller.worker is not old, "Tracking did not replace preview-only worker")
                            observe(controller.worker)
                            wait_for(lambda: camera_status(controller)[0] == "running" and mirror.video.image is not None,
                                     "Camera did not reopen after pause")
                    unexpected = [row for row in report["workers"] if row["camera"] == args.camera and row["errors"]]
                    assert not unexpected, f"Unexpected camera interruption, even if recovered: {unexpected}"
                    assert not report["power_events"], "Power/session change interrupted the check"
                    report["ok"] = True
                finally:
                    if power_monitor is not None:
                        power_monitor.close()
                    controller._quitting = True
                    controller._restart_pending = False
                    controller.worker.stop()
                    controller.worker.wait()
                    application.processEvents()
                    controller.shutdown()
                    if controller._settings_dlg is not None:
                        controller._settings_dlg.close()
                    for window in application.topLevelWidgets():
                        window.hide()
                    controller.tray.icon.hide()
    except Exception:
        report["error"] = traceback.format_exc()
        print(report["error"], flush=True)
    finally:
        sys.excepthook = previous_hook
        if report["qt_errors"]:
            report["ok"] = False
        lock.unlock()
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
        print(f"Report: {args.output}", flush=True)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
