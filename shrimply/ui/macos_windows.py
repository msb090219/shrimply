"""Allow floating Qt tools to accompany other apps across Mac Spaces."""
import sys

from PySide6.QtGui import QGuiApplication


def join_fullscreen_spaces(widget):
    if sys.platform != "darwin" or QGuiApplication.platformName() != "cocoa":
        return

    import AppKit
    import objc

    # On Cocoa, QWidget.winId() is the NSView pointer, not the NSWindow.
    view = objc.objc_object(c_void_p=int(widget.winId()))
    window = view.window()
    if window is None:
        return
    behavior = int(window.collectionBehavior())
    behavior &= ~(AppKit.NSWindowCollectionBehaviorMoveToActiveSpace
                  | AppKit.NSWindowCollectionBehaviorFullScreenPrimary
                  | AppKit.NSWindowCollectionBehaviorFullScreenNone)
    behavior |= (AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
                 | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary)
    # macOS 13+ also has an explicit cross-application overlay behavior.
    all_apps = getattr(AppKit, "NSWindowCollectionBehaviorCanJoinAllApplications", 0)
    if all_apps:
        behavior &= ~(AppKit.NSWindowCollectionBehaviorPrimary
                      | AppKit.NSWindowCollectionBehaviorAuxiliary)
        behavior |= all_apps
    window.setCollectionBehavior_(behavior)
