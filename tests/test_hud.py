from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from unshrimp.ui.hud import Hud
from unshrimp.ui import theme


@pytest.fixture
def hud():
    application = QApplication.instance() or QApplication([])
    widget = Hud()
    widget.setAttribute(Qt.WA_DontShowOnScreen)
    yield widget
    widget.hide()
    widget.deleteLater()
    application.processEvents()


def test_hud_shows_status_only_when_it_needs_explanation(hud):
    hud.show()
    QApplication.processEvents()
    width = hud.width()
    for mode, text in [("paused", "paused"), ("paused", "stopping camera"),
                       ("cam_error", "camera…"), ("uncalibrated", "double-click = calibrate"),
                       ("calibrating", "NORMAL 8/10s")]:
        hud.set_status(mode, text)
        QApplication.processEvents()
        assert hud.width() == width
        assert hud.height() > theme.HUD_HEIGHT
        assert not hud.label.isHidden()
    hud.set_status("away", "away")
    assert hud.height() == theme.HUD_HEIGHT
    for score in (None, .3, 1.2, 2.):
        hud.set_live(score, "legacy label")
        if score is None:
            assert hud.height() > theme.HUD_HEIGHT
        else:
            assert hud.height() == theme.HUD_HEIGHT
    assert hud.bar.height() == theme.HUD_HEIGHT
    assert hud.pause_button.size() == hud.menu_button.size()
    assert hud.pause_button.height() == theme.COMPACT_CONTROL_HEIGHT


def test_unknown_reading_and_accessible_pause_state(hud):
    hud.set_live(None, "good")
    assert hud.label.text() == "Finding posture"
    assert hud.level is None
    hud.set_status("paused", "stopping camera")
    assert hud.text == "Stopping camera"
    assert hud.pause_button.accessibleName() == "Resume tracking"
    assert hud.accessibleDescription() == "Stopping camera"


def test_zero_drag_offset_is_valid_and_release_ends_drag(hud):
    hud.move(100, 100)
    hud.mousePressEvent(SimpleNamespace(button=lambda: Qt.LeftButton,
                                       globalPosition=lambda: hud.frameGeometry().topLeft().toPointF()))
    assert hud.cursor().shape() == Qt.ClosedHandCursor
    hud.mouseMoveEvent(SimpleNamespace(buttons=lambda: Qt.LeftButton,
                                      globalPosition=lambda: QPoint(140, 150).toPointF()))
    assert hud.pos() == QPoint(140, 150)
    hud.mouseReleaseEvent(None)
    assert hud.cursor().shape() == Qt.OpenHandCursor
    hud.mouseMoveEvent(SimpleNamespace(buttons=lambda: Qt.LeftButton,
                                      globalPosition=lambda: QPoint(200, 200).toPointF()))
    assert hud.pos() == QPoint(140, 150)


def test_bar_surface_forwards_drag_press_and_release(hud):
    hud.show()
    QApplication.processEvents()
    QTest.mousePress(hud.bar, Qt.LeftButton, Qt.NoModifier, QPoint(3, 3))
    assert hud._drag_off is not None
    assert hud.cursor().shape() == Qt.ClosedHandCursor
    QTest.mouseRelease(hud.bar, Qt.LeftButton, Qt.NoModifier, QPoint(3, 3))
    assert hud._drag_off is None
    assert hud.cursor().shape() == Qt.OpenHandCursor


def test_keyboard_controls_emit_intent_and_menu_uses_existing_actions(hud):
    pause, menu = Mock(), Mock()
    hud.pause_requested.connect(pause)
    QTest.keyClick(hud.pause_button, Qt.Key_Space)
    pause.assert_called_once()
    hud.set_context_menu(menu)
    hud.menu_button.click()
    menu.popup.assert_called_once()


def test_hud_buttons_use_pointer_cursor_without_losing_drag_cursor(hud):
    assert hud.cursor().shape() == Qt.OpenHandCursor
    assert all(button.cursor().shape() == Qt.PointingHandCursor for button in (
        hud.pause_button, hud.menu_button,
    ))


def test_shrimp_row_lights_in_order_and_unknown_resets_to_neutral(hud):
    lit = []
    for score in (0., .5, 1., 1.49, 1.5, 2.5):
        hud.set_live(score, "")
        lit.append(hud.shrimp.lit_count)
        assert hud.height() == theme.HUD_HEIGHT
    assert lit == [1, 4, 7, 9, 10, 10]
    assert hud.shrimp.COLORS[0] == theme.GOOD
    assert hud.shrimp.COLORS[-1] == theme.BAD
    hud.set_live(None, "")
    assert hud.shrimp.lit_count == 0


def test_inactive_hud_keeps_all_shrimp_neutral_and_preview_keeps_resume_action(hud):
    hud.show()
    hud.set_live(2., "")
    assert hud.shrimp.lit_count == 10
    hud.set_status("preview", "Preview only · tracking paused")
    assert hud.shrimp.lit_count == 0
    assert hud.pause_button.accessibleName() == "Resume tracking"


def test_compact_row_keeps_controls_and_explains_missing_readings(hud):
    hud.show()
    hud.set_live(.5, "")
    expanded_width = hud.width()
    assert hud.height() == theme.HUD_HEIGHT
    hud.set_compact(True)
    QApplication.processEvents()
    compact_width = hud.width()
    assert compact_width == expanded_width
    assert hud.height() == theme.HUD_HEIGHT
    assert hud.label.isHidden()
    assert all(button.isVisible() for button in (hud.pause_button, hud.menu_button))
    assert hud.shrimp.lit_count == 4
    for mode in ("cam_error", "uncalibrated", "calibrating"):
        hud.set_status(mode, "details")
        assert not hud.label.isHidden()
        assert hud.width() == compact_width
        assert hud.height() > theme.HUD_HEIGHT
        assert hud.compact
    hud.set_live(None, "")
    assert not hud.label.isHidden()
    hud.set_live(.5, "")
    assert hud.width() == compact_width
    hud.set_status("paused", "paused")
    assert hud.pause_button.accessibleName() == "Resume tracking"
    assert not hud.label.isHidden()
    hud.set_compact(False)
    assert hud.width() == compact_width


def test_feedback_is_brief_and_break_prompt_takes_its_place(hud):
    hud.show()
    for score in (.2, 1.1, 1.8):
        hud.set_live(score, "")
        assert hud.label.isHidden()
        assert hud.height() == hud.bar.height()
    hud.show_feedback("Adjust posture")
    QApplication.processEvents()
    assert hud.shrimp.geometry().right() < hud.pause_button.x() < hud.menu_button.x()
    assert hud.label.text() == "Adjust posture"
    assert abs(hud.label.geometry().center().x() - hud.bar.geometry().center().x()) <= 1
    assert hud.label.y() > hud.bar.geometry().bottom()
    assert hud.label.alignment() == Qt.AlignCenter
    hud.set_break_prompt_visible(True)
    assert hud.label.isHidden()
    assert hud.height() == hud.bar.height()
    hud.show_feedback("Adjust posture")
    assert hud.label.isHidden()
    hud.set_break_prompt_visible(False)
    assert hud.label.isHidden()
    assert not hasattr(hud, "open_button")
    hud.set_status("calibrating", "NORMAL 8/10s")
    assert hud.label.text() == "Calibrating"
    assert "NORMAL 8/10s" in hud.toolTip()
    message = "Preview only · tracking paused while the camera preview is active"
    hud.set_status("preview", message)
    assert hud.label.width() == hud.bar.width() - 8
    assert hud.label.text() != message
    assert hud.toolTip() == message
    assert hud.bar.height() == theme.HUD_HEIGHT
    image = hud.grab().toImage()
    ratio = image.devicePixelRatio()
    assert image.pixelColor(round(ratio), round((hud.bar.height() + 5) * ratio)).alpha() == 0


def test_adjustment_caption_fades_and_recovery_clears_it(hud):
    hud.show()
    hud.set_live(1.8, "")
    hud.show_feedback("Adjust posture")
    assert not hud.label.isHidden()
    hud._caption_timer.stop()
    hud._fade_caption()
    QTest.qWait(300)
    assert hud.label.isHidden()
    hud.show_feedback("Adjust posture")
    hud.set_live(.4, "")
    assert hud.label.isHidden()


def test_compact_error_expansion_stays_on_screen(hud):
    hud.set_live(.5, "")
    hud.set_compact(True)
    area = hud.screen().availableGeometry()
    hud.move(area.right() - hud.width() + 1, area.bottom() - hud.height() + 1)
    hud.set_status("cam_error", "error")
    assert hud.frameGeometry().right() <= area.right()
    assert hud.frameGeometry().bottom() <= area.bottom()


def test_meter_spacing_has_no_reserved_drag_handle(hud):
    hud.show()
    hud.set_live(1.1, "")
    QApplication.processEvents()
    assert hud.bar.layout().itemAt(0).widget() is hud.shrimp
    assert hud.shrimp.x() == 12
    divider = hud.bar.layout().itemAt(2).widget()
    assert divider.x() - (hud.shrimp.x() + hud.shrimp.width()) == 12
    for compact in (True, False):
        hud.set_compact(compact)
        QApplication.processEvents()
        assert hud.shrimp.x() == 12
        assert hud.bar.height() == theme.HUD_HEIGHT


@pytest.mark.parametrize("key,height", [("s", 36), ("m", 40), ("l", 48)])
def test_meter_presets_scale_all_parts_and_keep_ten_segments(hud, key, height):
    hud.set_live(1.5, "")
    hud.set_size(key)
    hud.show()
    QApplication.processEvents()
    assert hud.bar.height() == height
    assert hud.height() == height
    assert hud.shrimp.lit_count == 10
    assert len(hud.shrimp.COLORS) == 10
    assert hud.pause_button.height() >= 28
    assert hud.pause_button.y() >= 0
    assert hud.menu_button.geometry().right() < hud.width()
    width = hud.width()
    hud.show_feedback("Adjust posture")
    assert hud.height() > height
    hud.set_compact(True)
    assert hud.height() == height
    assert hud.width() == width
