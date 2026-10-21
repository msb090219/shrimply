"""Check packaged Qt, art, and real model inference without opening a camera."""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage

from shrimply import __version__
from shrimply.vision.landmarks import Landmarkers


def run(root: Path, report_path: Path) -> int:
    result = {"version": __version__, "frozen": bool(getattr(sys, "frozen", False)),
              "ok": False, "checks": []}
    try:
        if sys.platform == "darwin":
            from AVFoundation import AVCaptureDevice, AVMediaTypeVideo
            from Foundation import NSBundle

            status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeVideo)
            result["camera_authorization"] = {
                0: "not_determined", 1: "restricted", 2: "denied", 3: "authorized",
            }.get(status, "unknown")
            result["bundle_version"] = NSBundle.mainBundle().objectForInfoDictionaryKey_("CFBundleShortVersionString")
        image = QImage(str(root / "assets" / "shrimply.ico"))
        if image.isNull():
            raise RuntimeError("Bundled application icon could not be decoded")
        result["checks"].append("qt_image_plugins_and_icon")
        landmarks = Landmarkers(root / "models")
        try:
            result["checks"].append("both_models_loaded")
            # Synthetic black input exercises native inference without capturing a person.
            landmarks.signals(np.zeros((480, 640, 3), dtype=np.uint8), 1)
            result["checks"].append("native_inference")
        finally:
            landmarks.close()
        result["ok"] = True
    except Exception:
        result["error"] = traceback.format_exc()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8") as report:
        json.dump(result, report, indent=2)
    return 0 if result["ok"] else 1
