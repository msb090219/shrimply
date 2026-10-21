# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Windows and local macOS development builds.
# One-dir layout (fast startup; onefile would unpack ~150 MB per launch).
import sys
import runpy
import platform
from importlib.metadata import distribution
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH)
NAME = "Shrimply" if sys.platform == "darwin" else "shrimply"


def wheel_file(package, *suffixes, required=True):
    wheel = distribution(package)
    for file in wheel.files or ():
        if str(file).replace("\\", "/").endswith(suffixes):
            path = wheel.locate_file(file)
            if path.is_file():
                return str(path)
    if required:
        raise FileNotFoundError(f"{package} wheel is missing {suffixes}")


# Intel Mac uses the older MediaPipe/OpenCV wheels pinned in pyproject.toml.
opencv_package = ("opencv-contrib-python" if sys.platform == "darwin"
                  and platform.machine() == "x86_64" else "opencv-python")
mp_notice = wheel_file("mediapipe", "dist-info/licenses/NOTICE", "dist-info/NOTICE", required=False)

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
        (wheel_file("mediapipe", "dist-info/licenses/LICENSE", "dist-info/LICENSE"), "licenses/mediapipe"),
        (wheel_file(opencv_package, "cv2/LICENSE.txt"), "licenses/opencv"),
        (wheel_file(opencv_package, "cv2/LICENSE-3RD-PARTY.txt"), "licenses/opencv"),
    ] + ([(mp_notice, "licenses/mediapipe")] if mp_notice else []),
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
    icon=str(ROOT / "assets" / "shrimply.ico") if sys.platform == "win32" else None,
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
    version = runpy.run_path(str(ROOT / "shrimply" / "__init__.py"))["__version__"]
    BUNDLE(
        coll,
        name="Shrimply.app",
        icon=str(ROOT / "assets" / "shrimply.icns"),
        bundle_identifier="com.msb090219.shrimply",
        version=version,
        info_plist={
            "CFBundleVersion": version,
            "LSMinimumSystemVersion": "15.0",  # conservative beta deployment floor, verified against bundled binaries
            # without this macOS denies (or crashes on) camera access
            "NSCameraUsageDescription": (
                "Shrimply uses the camera locally to measure your posture. "
                "No video ever leaves your machine."
            ),
            "LSUIElement": True,  # tray app: no Dock icon
            "CFBundleDisplayName": "Shrimply",
            "NSHighResolutionCapable": True,
        },
    )
