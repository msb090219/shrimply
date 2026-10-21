"""Quiet login startup: a Windows Run entry or a per-user Mac LaunchAgent."""
from __future__ import annotations

import sys
import os
import plistlib
import tempfile
from pathlib import Path

try:
    import winreg
except ImportError:  # non-Windows platforms
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Shrimply"
OLD_VALUE_NAME = "Unshrimp"
MAC_LABEL = "com.msb090219.shrimply"
LEGACY_MAC_LABEL = "com.msb090219.unshrimp"


def _mac_path() -> Path:
    return Path.home() / f"Library/LaunchAgents/{MAC_LABEL}.plist"


def _legacy_mac_path() -> Path:
    return _mac_path().with_name(f"{LEGACY_MAC_LABEL}.plist")


def _mac_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        # LaunchServices gives packaged apps their normal launch environment.
        for parent in Path(sys.executable).parents:
            if parent.suffix == ".app":
                return ["/usr/bin/open", "-g", str(parent), "--args", "--background"]
        return [sys.executable, "--background"]
    main = Path(__file__).resolve().parent.parent / "main.py"
    return [sys.executable, str(main), "--background"]


def _command() -> str:
    if getattr(sys, "frozen", False):  # packaged exe — it *is* the app
        return f'"{sys.executable}" --background'
    py = Path(sys.executable)
    pyw = py.with_name("pythonw.exe")
    exe = str(pyw) if pyw.exists() else str(py)
    main = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{exe}" "{main}" --background'


def is_enabled() -> bool:
    if sys.platform == "darwin":
        for path, label in ((_mac_path(), MAC_LABEL), (_legacy_mac_path(), LEGACY_MAC_LABEL)):
            try:
                with path.open("rb") as stream:
                    entry = plistlib.load(stream)
                if isinstance(entry, dict) and entry.get("Label") == label and entry.get("RunAtLoad") is True:
                    return True
            except (OSError, ValueError, plistlib.InvalidFileException):
                pass
        return False
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            for name in (VALUE_NAME, OLD_VALUE_NAME):
                try:
                    winreg.QueryValueEx(k, name)
                    return True
                except OSError:
                    pass
    except OSError:
        return False
    return False


def set_enabled(on: bool) -> None:
    if sys.platform == "darwin":
        path = _mac_path()
        if not on:
            path.unlink(missing_ok=True)
            _legacy_mac_path().unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replacement also lets a settings-save failure safely roll back.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                plistlib.dump({
                    "Label": MAC_LABEL,
                    "ProgramArguments": _mac_arguments(),
                    "RunAtLoad": True,
                    "LimitLoadToSessionType": "Aqua",
                }, stream)
            os.replace(temporary, path)
            _legacy_mac_path().unlink(missing_ok=True)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        # launchd reads this at the next login. No immediate second launch.
        return
    if winreg is None:
        raise RuntimeError("Login startup is supported on Windows and macOS")
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, VALUE_NAME, 0, winreg.REG_SZ, _command())
        for name in ((OLD_VALUE_NAME,) if on else (VALUE_NAME, OLD_VALUE_NAME)):
            try:
                winreg.DeleteValue(k, name)
            except OSError:
                pass  # already off
