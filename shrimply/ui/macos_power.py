"""Observe macOS power and session changes without keeping the machine awake."""
from __future__ import annotations

from AppKit import (
    NSWorkspace, NSWorkspaceWillSleepNotification, NSWorkspaceDidWakeNotification,
    NSWorkspaceScreensDidSleepNotification, NSWorkspaceScreensDidWakeNotification,
    NSWorkspaceSessionDidResignActiveNotification, NSWorkspaceSessionDidBecomeActiveNotification,
)
from Foundation import NSObject, NSDistributedNotificationCenter
from PySide6.QtCore import QObject, Signal, Slot


class _PowerObserver(NSObject):
    def powerChanged_(self, notification):
        self.callback(str(notification.name()))


class MacPowerMonitor(QObject):
    notification = Signal(str)

    def __init__(self, suspend, resume):
        super().__init__()
        self._suspend, self._resume = suspend, resume
        self._blocked = set()
        self._events = {
            NSWorkspaceWillSleepNotification: ("sleep", True),
            NSWorkspaceDidWakeNotification: ("sleep", False),
            NSWorkspaceScreensDidSleepNotification: ("display", True),
            NSWorkspaceScreensDidWakeNotification: ("display", False),
            NSWorkspaceSessionDidResignActiveNotification: ("session", True),
            NSWorkspaceSessionDidBecomeActiveNotification: ("session", False),
            # macOS sends these distributed notifications on screen lock/unlock.
            "com.apple.screenIsLocked": ("lock", True),
            "com.apple.screenIsUnlocked": ("lock", False),
        }
        self.notification.connect(self._changed)
        self._observer = _PowerObserver.alloc().init()
        self._observer.callback = self.notification.emit
        self._centers = [NSWorkspace.sharedWorkspace().notificationCenter(),
                         NSDistributedNotificationCenter.defaultCenter()]
        for name in self._events:
            center = self._centers[1 if name.startswith("com.apple.") else 0]
            center.addObserver_selector_name_object_(self._observer, "powerChanged:", name, None)

    @Slot(str)
    def _changed(self, name):
        if self._observer is None:
            return
        reason, blocked = self._events[name]
        was_blocked = bool(self._blocked)
        if blocked:
            self._blocked.add(reason)
        else:
            self._blocked.discard(reason)
        if bool(self._blocked) != was_blocked:
            (self._suspend if self._blocked else self._resume)()

    def close(self):
        if self._observer is not None:
            for center in self._centers:
                center.removeObserver_(self._observer)
            self._observer.callback = lambda _name: None
            self._observer = None
