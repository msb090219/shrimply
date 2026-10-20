#!/usr/bin/env python3
"""Unshrimp — don't get shrimped. Entry point.

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

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket

import config as config_mod
from unshrimp import diag
from unshrimp.ui.app import UnshrimpApp

ROOT = Path(__file__).resolve().parent


def _activation_name() -> str:
    return "unshrimp-" + hashlib.sha256(str(config_mod.APP_DIR.resolve()).casefold().encode()).hexdigest()[:24]


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
    parser = argparse.ArgumentParser(description="Unshrimp posture guard")
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--background", action="store_true", help="Start in the tray without opening the main window")
    parser.add_argument("--smoke-test", type=Path, metavar="REPORT_JSON")
    args, qt_args = parser.parse_known_args()
    app = QApplication([sys.argv[0], *qt_args])
    app.setWindowIcon(QIcon(str(ROOT / "assets" / "unshrimp.png")))
    if args.smoke_test:
        from unshrimp.smoke import run

        return run(ROOT, args.smoke_test)
    try:
        config_mod.APP_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        QMessageBox.critical(None, "Unshrimp could not start", "Cannot access the application data folder.")
        return 1
    instance_lock = QLockFile(str(config_mod.APP_DIR / "instance.lock"))
    instance_lock.setStaleLockTime(0)  # a healthy working-day session must never expire
    if not instance_lock.tryLock(0):
        if instance_lock.error() == QLockFile.LockFailedError:
            if not args.background and not _activate_existing():
                QMessageBox.information(None, "Unshrimp is already running",
                                    "Use the shrimp icon in the system tray to open Unshrimp's controls.")
            return 0
        QMessageBox.critical(None, "Unshrimp could not start",
                             "Cannot lock the application data folder. Check its permissions and available disk space.")
        return 1
    config_mod.migrate_legacy()  # carry OSA-era baseline/history across
    diag.start(detailed=args.diagnostics)
    from unshrimp import autostart
    try:
        if autostart.is_enabled():
            autostart.set_enabled(True)  # refresh older entries and packaged executable paths
    except OSError as exc:
        diag.log(f"app: could not refresh login startup: {exc}")
    app.setApplicationName("Unshrimp")
    app.setQuitOnLastWindowClosed(False)  # tray app — overlays aren't windows

    unshrimp = UnshrimpApp(ROOT / "models")
    from unshrimp.ui.power import PowerMonitor

    power_monitor = PowerMonitor(unshrimp.hud.winId(), unshrimp._on_system_suspend,
                                 unshrimp._on_system_resume)
    activation_server = _activation_server(unshrimp)
    unshrimp.start(background=args.background)

    rc = app.exec()
    activation_server.close()
    power_monitor.close()
    unshrimp.worker.stop()
    unshrimp.worker.wait()  # keep the owner alive until camera resources are released
    unshrimp.shutdown()
    diag.log(f"app: exit {rc}")
    diag.close()
    instance_lock.unlock()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
