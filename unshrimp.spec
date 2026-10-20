# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Unshrimp; Windows is the supported release target.
# One-dir layout (fast startup; onefile would unpack ~150 MB per launch).
import sys
from importlib.metadata import distribution
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH)
NAME = "Unshrimp" if sys.platform == "darwin" else "unshrimp"


def wheel_file(package, suffix):
    wheel = distribution(package)
    for file in wheel.files or ():
        if str(file).replace("\\", "/").endswith(suffix):
            path = wheel.locate_file(file)
            if path.is_file():
                return str(path)
    raise FileNotFoundError(f"{package} wheel is missing {suffix}")

# MediaPipe loads its C bindings dynamically at runtime, invisible to
# static analysis — collect the whole package's submodules and native libs.
mp_hidden = collect_submodules("mediapipe")
mp_bins = collect_dynamic_libs("mediapipe")

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=mp_bins,
    datas=[
        (str(ROOT / "models"), "models"),  # bundle the MediaPipe models
        (str(ROOT / "assets"), "assets"),  # brand art (user-replaceable)
        (str(ROOT / "LICENSE"), "licenses"),
        (wheel_file("mediapipe", "dist-info/licenses/LICENSE"), "licenses/mediapipe"),
        (wheel_file("mediapipe", "dist-info/licenses/NOTICE"), "licenses/mediapipe"),
        (wheel_file("opencv-python", "cv2/LICENSE.txt"), "licenses/opencv"),
        (wheel_file("opencv-python", "cv2/LICENSE-3RD-PARTY.txt"), "licenses/opencv"),
    ],
    hiddenimports=mp_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "assets" / "unshrimp.ico") if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=NAME,
)

if sys.platform == "darwin":
    BUNDLE(
        coll,
        name="Unshrimp.app",
        bundle_identifier="com.msb090219.unshrimp",
        info_plist={
            # without this macOS denies (or crashes on) camera access
            "NSCameraUsageDescription": (
                "Unshrimp uses the camera locally to measure your posture. "
                "No video ever leaves your machine."
            ),
            "LSUIElement": True,  # tray app: no Dock icon
        },
    )
