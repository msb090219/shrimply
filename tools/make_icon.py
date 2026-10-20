#!/usr/bin/env python3
"""Build the Windows and website icons from the app's realistic shrimp PNG."""
from __future__ import annotations

from pathlib import Path
from shutil import copyfile

ROOT = Path(__file__).resolve().parent.parent

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> int:
    from PIL import Image

    ico_path = ROOT / "assets" / "shrimply.ico"
    with Image.open(ROOT / "assets" / "shrimply.png") as image:
        image.save(ico_path, format="ICO", sizes=ICO_SIZES)
    copyfile(ico_path, ROOT / "docs" / "assets" / "shrimply.ico")
    with Image.open(ico_path) as icon:
        assert icon.info["sizes"] == set(ICO_SIZES)
    print(f"wrote {ico_path} ({len(ICO_SIZES)} sizes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
