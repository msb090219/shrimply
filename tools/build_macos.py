#!/usr/bin/env python3
"""Build and verify a local unsigned Mac beta; never upload or publish it."""
from __future__ import annotations

import hashlib
import json
import marshal
import platform
import plistlib
import re
import runpy
import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parent.parent


def run(*args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT, **kwargs)


def main() -> None:
    if sys.platform != "darwin":
        raise SystemExit("Build this package on macOS with its native Python architecture.")
    arch = platform.machine()
    if arch not in ("x86_64", "arm64"):
        raise SystemExit(f"Unsupported build architecture: {arch}")
    release_version = runpy.run_path(str(ROOT / "shrimply/__init__.py"))["__version__"]
    assert version("shrimply") == release_version, "Reinstall the editable project before building"
    release = ROOT / "dist/macos-release"
    release.mkdir(parents=True, exist_ok=True)
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", release / arch, "--workpath", ROOT / "build/macos-release" / arch,
        ROOT / "shrimply.spec")
    app = release / arch / "Shrimply.app"
    run("/usr/bin/codesign", "--verify", "--deep", "--strict", app)
    metadata = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    assert metadata["CFBundleIdentifier"] == "com.msb090219.shrimply"
    assert metadata["CFBundleShortVersionString"] == metadata["CFBundleVersion"] == release_version
    assert metadata["CFBundleDisplayName"] == "Shrimply" and metadata["NSCameraUsageDescription"]
    assert metadata["LSMinimumSystemVersion"] == "15.0"
    assert (app / "Contents/Resources" / metadata["CFBundleIconFile"]).is_file()
    native_files = set()
    for path in (app / "Contents").rglob("*"):
        if path.is_file():
            with path.open("rb") as stream:
                if stream.read(4) in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
                    native_files.add(path.resolve())
    commands = subprocess.check_output(["/usr/bin/otool", "-l", *map(str, sorted(native_files))], text=True)
    targets = [a or b for a, b in re.findall(
        r"\bminos\s+([\d.]+)|\bcmd LC_VERSION_MIN_MACOSX\s+cmdsize \d+\s+version ([\d.]+)", commands)]
    os_version = lambda value: tuple((list(map(int, value.split("."))) + [0, 0])[:3])
    native_minimum = max(targets, key=os_version)
    assert os_version(native_minimum) <= os_version(metadata["LSMinimumSystemVersion"]), native_minimum

    archive = CArchiveReader(str(app / "Contents/MacOS/Shrimply"))
    pyz = archive.open_embedded_archive(next(n for n, e in archive.toc.items() if e[-1] == "z"))
    assert not any(n == "unshrimp" or n.startswith("unshrimp.") for n in pyz.toc)
    matched = []
    for name in sorted(pyz.toc):
        if name != "config" and name != "shrimply" and not name.startswith("shrimply."):
            continue
        source = ROOT / (name.replace(".", "/") + ".py")
        if not source.exists():
            source = ROOT / name.replace(".", "/") / "__init__.py"
        bundled = pyz.extract(name)
        assert compile(source.read_text(encoding="utf-8-sig"), bundled.co_filename,
                       "exec", dont_inherit=True) == bundled, f"Stale module: {name}"
        matched.append(name)
    bundled = marshal.loads(archive.extract("main"))
    assert compile((ROOT / "main.py").read_text(), bundled.co_filename,
                   "exec", dont_inherit=True) == bundled
    matched.append("main")

    stem = f"shrimply-macos-{arch}"
    with tempfile.TemporaryDirectory(prefix="Shrimply extracted check ", dir=release) as folder:
        temporary = Path(folder)
        packed = temporary / f"{stem}.zip"
        run("/usr/bin/ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", app, packed)
        extracted = temporary / "extracted app"
        run("/usr/bin/ditto", "-x", "-k", packed, extracted)
        extracted_app = extracted / "Shrimply.app"
        run("/usr/bin/codesign", "--verify", "--deep", "--strict", extracted_app)
        smoke_path = temporary / "smoke.json"
        run(extracted_app / "Contents/MacOS/Shrimply", "--smoke-test", smoke_path, timeout=120)
        smoke = json.loads(smoke_path.read_text())
        assert smoke["ok"] and smoke["frozen"] and smoke["version"] == release_version
        assert smoke["bundle_version"] == release_version
        with packed.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        packed.replace(release / f"{stem}.zip")
        smoke_path.replace(release / f"{stem}-smoke.json")
    (release / f"{stem}.sha256").write_text(f"{digest}  {stem}.zip\n")
    report = {"version": release_version, "architecture": arch,
              "signing": "ad hoc; no Developer ID or notarization",
              "bundle_identifier": metadata["CFBundleIdentifier"],
              "minimum_macos": metadata["LSMinimumSystemVersion"],
              "native_minimum_macos": native_minimum,
              "bundled_modules_match_source": matched, "sha256": digest,
              "strict_signature_verified": True, "extracted_frozen_smoke": True,
              "published": False}
    (release / f"{stem}-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Local beta prepared: {release / (stem + '.zip')}\nSHA-256: {digest}")


if __name__ == "__main__":
    main()
