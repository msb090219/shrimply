from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog
from PySide6.QtTest import QTest

from unshrimp.ui import theme
from unshrimp.ui.welcome import WelcomeDialog


@pytest.fixture
def qt_app():
    return QApplication.instance() or QApplication([])


def test_application_icon_loads_photo_shrimp(qt_app):
    icon = theme.app_icon()
    assert not icon.isNull()
    assert not icon.pixmap(64, 64).isNull()


def test_windows_keep_standard_native_titlebar(qt_app):
    window = QMainWindow()
    theme.apply_desktop_theme(window)
    window.setWindowTitle("Unshrimp")
    window.setAttribute(Qt.WA_DontShowOnScreen)
    try:
        window.show()
        qt_app.processEvents()
        assert not window.windowIcon().isNull()
        assert window.windowTitle() == "Unshrimp"
        assert not window.windowFlags() & Qt.FramelessWindowHint
        assert window.windowFlags() & Qt.WindowTitleHint
        assert window.windowFlags() & Qt.WindowCloseButtonHint
    finally:
        window.close()
        window.deleteLater()


def test_about_is_modeless_reused_and_released_on_close(qt_app):
    from unshrimp.ui.app import UnshrimpApp
    controller = SimpleNamespace(_about_dlg=None)
    try:
        UnshrimpApp._show_about(controller)
        dialog = controller._about_dlg
        assert not dialog.isModal()
        assert not dialog.windowIcon().isNull()
        UnshrimpApp._show_about(controller)
        assert controller._about_dlg is dialog
        dialog.reject()
        assert controller._about_dlg is None
    finally:
        if controller._about_dlg is not None:
            controller._about_dlg.close()
        qt_app.processEvents()


def test_welcome_still_distinguishes_calibration_from_dismissal(qt_app):
    dialog = WelcomeDialog()
    dialog._calibrate()
    assert dialog.calibrate_requested
    assert dialog.result() == QDialog.Accepted
    dialog = WelcomeDialog()
    dialog.reject()
    assert not dialog.calibrate_requested
    dialog.deleteLater()


@pytest.mark.parametrize("key,accepted", [(Qt.Key_Return, True), (Qt.Key_Escape, False)])
def test_welcome_keyboard_can_start_or_defer_setup(qt_app, key, accepted):
    dialog = WelcomeDialog()
    dialog.setAttribute(Qt.WA_DontShowOnScreen)
    try:
        dialog.show()
        qt_app.processEvents()
        QTest.keyClick(dialog, key)
        assert dialog.calibrate_requested is accepted
        assert dialog.result() == (QDialog.Accepted if accepted else QDialog.Rejected)
        assert not dialog.isVisible()
    finally:
        dialog.close()
        dialog.deleteLater()
