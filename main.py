#!/usr/bin/env python3
"""Shrimply — don't get shrimped. Entry point.

A private, local posture guard: watches your webcam on-device, compares
against your personal calibrated baseline, and fades in a very large
shrimp when you slouch. Camera frames are processed locally and are not
written to disk. The bundled MediaPipe SDK sends usage metrics.
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path
import hashlib
import os
import sqlite3

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket

import config as config_mod
from shrimply import diag

ROOT = Path(__file__).resolve().parent


def _configure_macos_font_cache(root: Path) -> None:
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return
    # Intel MediaPipe imports Matplotlib before the UI opens. PyInstaller's
    # temporary font cache otherwise triggers a system-font scan every launch.
    # This is a persistent app bundle; separate locations need separate caches
    # because Matplotlib stores absolute paths to its bundled fonts.
    cache = (Path.home() / "Library/Caches/Shrimply/matplotlib" /
             hashlib.sha256(str(root).encode()).hexdigest()[:16])
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except OSError:
        return  # retain PyInstaller's temporary-cache fallback
    os.environ["MPLCONFIGDIR"] = str(cache)


_configure_macos_font_cache(ROOT)
from shrimply.ui.app import ShrimplyApp


def _activation_name() -> str:
    return "shrimply-" + hashlib.sha256(str(config_mod.APP_DIR.resolve()).casefold().encode()).hexdigest()[:24]


def _activate_existing() -> bool:
    if sys.platform == "win32":
        import ctypes

        pid, _, _ = QLockFile(str(config_mod.APP_DIR / "instance.lock")).getLockInfo()
        if pid:
            # Let the foreground launcher hand focus to the existing process.
            ctypes.windll.user32.AllowSetForegroundWindow(pid)
    socket = QLocalSocket()
    socket.connectToServer(_activation_name())
    if not socket.waitForConnected(1500):
        return False
    socket.disconnectFromServer()
    return True


def _activation_server(controller):
    name = _activation_name()
    QLocalServer.removeServer(name)  # only the lock owner may replace a stale endpoint
    server = QLocalServer(controller)
    server.setSocketOptions(QLocalServer.UserAccessOption)

    def accept():
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            socket.disconnected.connect(socket.deleteLater)
            controller._open_main_window()
            socket.disconnectFromServer()

    server.newConnection.connect(accept)
    if not server.listen(name):
        diag.log("app: activation listener unavailable: " + server.errorString())
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Shrimply posture guard")
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--background", action="store_true", help="Start in the tray without opening the main window")
    parser.add_argument("--smoke-test", type=Path, metavar="REPORT_JSON")
    args, qt_args = parser.parse_known_args()
    app = QApplication([sys.argv[0], *qt_args])
    app.setWindowIcon(QIcon(str(ROOT / "assets" / "shrimply.png")))
    if args.smoke_test:
        from shrimply.smoke import run

        return run(ROOT, args.smoke_test)
    try:
        config_mod.APP_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        QMessageBox.critical(None, "Shrimply could not start", "Cannot access the application data folder.")
        return 1
    instance_lock = QLockFile(str(config_mod.APP_DIR / "instance.lock"))
    instance_lock.setStaleLockTime(0)  # a healthy working-day session must never expire
    if not instance_lock.tryLock(0):
        if instance_lock.error() == QLockFile.LockFailedError:
            if not args.background and not _activate_existing():
                QMessageBox.information(None, "Shrimply is already running",
                                    "Use the shrimp icon in the menu bar to open Shrimply's controls."
                                    if sys.platform == "darwin" else
                                    "Use the shrimp icon in the system tray to open Shrimply's controls.")
            return 0
        QMessageBox.critical(None, "Shrimply could not start",
                             "Cannot lock the application data folder. Check its permissions and available disk space.")
        return 1
    legacy_lock = None
    if config_mod.LEGACY_APP_DIR.is_dir():
        legacy_lock = QLockFile(str(config_mod.LEGACY_APP_DIR / "instance.lock"))
        legacy_lock.setStaleLockTime(0)
        if not legacy_lock.tryLock(0):
            if legacy_lock.error() == QLockFile.LockFailedError:
                QMessageBox.information(None, "Quit Unshrimp first",
                                        "Quit the old Unshrimp app before opening Shrimply so your saved data can be copied safely.")
                result = 0
            else:
                QMessageBox.critical(None, "Shrimply could not start",
                                     "Cannot access the old Unshrimp data folder.")
                result = 1
            instance_lock.unlock()
            return result
    config_mod.migrate_legacy()
    diag.start(detailed=args.diagnostics)
    from shrimply import autostart
    try:
        if autostart.is_enabled():
            autostart.set_enabled(True)  # refresh older entries and packaged executable paths
    except OSError as exc:
        diag.log(f"app: could not refresh login startup: {exc}")
    app.setApplicationName("Shrimply")
    app.setQuitOnLastWindowClosed(False)  # tray app — overlays aren't windows

    try:
        shrimply = ShrimplyApp(ROOT / "models")
    except (OSError, sqlite3.Error) as exc:
        diag.log(f"app: could not open local data: {exc}")
        QMessageBox.critical(None, "Shrimply could not start",
                             "Cannot open the local history database. Check folder permissions "
                             "and available disk space. Your existing data has not been replaced."
                             f"\n\nData folder: {config_mod.APP_DIR}\n\n{exc}")
        diag.close()
        if legacy_lock is not None:
            legacy_lock.unlock()
        instance_lock.unlock()
        return 1
    from shrimply.ui.power import PowerMonitor

    power_monitor = PowerMonitor(shrimply.hud.winId(), shrimply._on_system_suspend,
                                 shrimply._on_system_resume)
    activation_server = _activation_server(shrimply)
    shrimply.start(background=args.background)

    rc = app.exec()
    activation_server.close()
    power_monitor.close()
    shrimply.worker.stop()
    shrimply.worker.wait()  # keep the owner alive until camera resources are released
    shrimply.shutdown()
    diag.log(f"app: exit {rc}")
    diag.close()
    if legacy_lock is not None:
        legacy_lock.unlock()
    instance_lock.unlock()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
