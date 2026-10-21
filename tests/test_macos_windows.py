"""Check native panel behavior without taking over another app's Space."""
import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="native Mac panels")
def test_native_overlays_join_fullscreen_spaces_after_show_and_reshow():
    env = dict(os.environ, QT_QPA_PLATFORM="cocoa")
    result = subprocess.run(
        [sys.executable, "-c", "import runpy, sys; runpy.run_path(sys.argv[1], run_name='__main__')", __file__],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _check_native_panels():
    import AppKit
    import objc
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from shrimply.ui.hud import Hud
    from shrimply.ui.mascot import MascotWindow
    from shrimply.ui.break_prompt import BreakPrompt

    app = QApplication([])
    for cls, option in ((Hud, "horizontal"), (Hud, "vertical"),
                        (MascotWindow, "shrimp"), (MascotWindow, "text"),
                        (BreakPrompt, "reminder")):
        widget = cls()
        if cls is Hud:
            widget.set_orientation(option)
            widget.set_status("paused", "Tracking paused")
        elif cls is MascotWindow:
            widget.set_options(.87, "m", False, style=option)
        widget.setAttribute(Qt.WA_ShowWithoutActivating)
        try:
            for _ in range(2):
                widget.show()
                app.processEvents()
                native = objc.objc_object(c_void_p=int(widget.winId())).window()
                behavior = int(native.collectionBehavior())
                assert behavior & AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
                assert behavior & AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
                assert not behavior & AppKit.NSWindowCollectionBehaviorFullScreenPrimary
                assert not behavior & AppKit.NSWindowCollectionBehaviorMoveToActiveSpace
                if hasattr(AppKit, "NSWindowCollectionBehaviorCanJoinAllApplications"):
                    assert behavior & AppKit.NSWindowCollectionBehaviorCanJoinAllApplications
                    assert not behavior & AppKit.NSWindowCollectionBehaviorPrimary
                    assert not behavior & AppKit.NSWindowCollectionBehaviorAuxiliary
                assert native.level() >= AppKit.NSFloatingWindowLevel
                if cls is MascotWindow:
                    assert native.ignoresMouseEvents()
                if cls is BreakPrompt:
                    assert not native.ignoresMouseEvents()
                if cls is Hud and option == "vertical":
                    assert widget.label.isVisible()
                    caption = objc.objc_object(c_void_p=int(widget.label.winId())).window()
                    assert int(caption.collectionBehavior()) & AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
                    assert int(caption.collectionBehavior()) & AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
                    assert caption.ignoresMouseEvents()
                widget.hide()
        finally:
            widget.hide()
            widget.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    _check_native_panels()
