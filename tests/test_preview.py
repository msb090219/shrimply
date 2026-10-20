from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QImage, QPalette, QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from shrimply.ui.preview import PreviewWindow
from shrimply.ui.preview import CameraPreviewWindow
from shrimply.vision.worker import PreviewPayload
from types import SimpleNamespace
from shrimply.core.states import State


@pytest.fixture
def panel():
    application = QApplication.instance() or QApplication([])
    window = PreviewWindow()
    window.setAttribute(Qt.WA_DontShowOnScreen)
    yield window
    window.hide()
    window.deleteLater()
    application.processEvents()


def test_setup_checks_and_phase_are_named_and_instructions_wrap(panel):
    panel.set_checks({"present": True, "gaze": False})
    assert panel.check_labels["present"].text() == "Face and shoulders: Passed"
    assert panel.check_labels["gaze"].text() == "Camera height: Needs attention"
    assert panel.check_labels["light"].text() == "Lighting: Waiting"
    panel.set_phase("normal")
    assert panel.step_label.text() == "Step 3 of 5"
    assert panel.phase == "normal"
    text = "A long instruction " * 15
    panel.set_instruction("Sit normally", text)
    assert panel.detail.wordWrap()
    assert panel.detail.text() == text


def test_terminal_result_clears_image_and_ignores_queued_frames(panel):
    image = QImage(64, 48, QImage.Format_RGB32)
    image.fill(Qt.black)
    frame = PreviewPayload(image)
    panel.update_frame(frame)
    assert panel.video.image is image
    panel.show_result(False, "Your previous calibration is still active.")
    assert panel.video.image is None
    assert not panel.retry_button.isHidden()
    assert panel.cancel_button.isHidden()
    panel.update_frame(frame)
    assert panel.video.image is None
    panel.begin()
    assert panel.retry_button.isHidden()
    assert not panel.cancel_button.isHidden()
    panel.update_frame(frame)
    assert panel.video.image is image


def test_close_during_calibration_routes_to_cancel_and_completed_close_does_not(panel):
    cancel = Mock()
    panel.cancel_requested.connect(cancel)
    panel.show()
    panel.close()
    cancel.assert_called_once()
    panel.show_result(True, "Baseline saved")
    panel.close()
    cancel.assert_called_once()
    assert panel.phase == "done"


def test_override_and_retry_route_to_existing_controller_actions(panel):
    override, retry = Mock(), Mock()
    panel.continue_requested.connect(override)
    panel.retry_requested.connect(retry)
    assert panel.skip_button.isHidden()
    panel.set_override_available(True)
    panel.skip_button.click()
    override.assert_called_once()
    panel.show_result(False, "Not saved")
    assert panel.skip_button.isHidden()
    panel.retry_button.click()
    retry.assert_called_once()


def test_success_screen_introduces_feedback_and_only_start_emits_start(panel):
    start = Mock()
    panel.start_requested.connect(start)
    panel.show_result(True, "Baseline saved")
    assert panel.video.isHidden()
    assert panel.check_group.isHidden()
    assert panel.feedback_group.isHidden()
    assert not panel.help_button.isHidden()
    panel.help_button.click()
    assert not panel.feedback_group.isHidden()
    assert "paused" in panel.caption.text()
    assert not panel.start_button.isHidden()
    panel.close_button.click()
    start.assert_not_called()
    assert panel.isHidden()
    panel.show_result(True, "Baseline saved")
    panel.start_button.click()
    start.assert_called_once()
    panel.begin()
    assert panel.start_button.isHidden()
    assert panel.feedback_group.isHidden()
    assert not panel.video.isHidden()
    assert panel.check_group.isHidden()
    assert not panel.details_button.isHidden()


def test_setup_details_are_optional_but_revealed_when_checks_stall(panel):
    assert panel.check_group.isHidden()
    panel.details_button.click()
    assert not panel.check_group.isHidden()
    panel.details_button.click()
    assert panel.check_group.isHidden()
    panel.set_override_available(True)
    assert not panel.check_group.isHidden()
    panel.begin()
    assert not panel.details_button.isChecked()
    assert panel.check_group.isHidden()


def test_details_disclosure_keeps_keyboard_access_and_does_not_use_native_blue_fill(panel):
    panel.show()
    button = panel.details_button
    palette = button.palette()
    palette.setColor(QPalette.Highlight, QColor("#2b99f3"))
    palette.setColor(QPalette.Accent, QColor("#2b99f3"))
    button.setPalette(palette)
    button.setFocus()
    QTest.keyClick(button, Qt.Key_Space)
    QApplication.processEvents()
    assert button.isChecked() and button.arrowType() == Qt.DownArrow
    assert not panel.check_group.isHidden()
    image = button.grab().toImage()
    assert not any(color.blue() > color.red() + 40 and color.blue() > color.green() + 40
                   for y in range(image.height()) for x in range(image.width())
                   for color in [image.pixelColor(x, y)])
    QTest.keyClick(button, Qt.Key_Space)
    assert not button.isChecked() and button.arrowType() == Qt.RightArrow
    assert panel.check_group.isHidden()


def test_pose_and_supporting_instruction_precede_the_timing_area(panel):
    panel.set_instruction("Sit tall", "Relax your shoulders.")
    panel.show()
    QApplication.processEvents()
    assert panel.instruction.mapTo(panel, panel.instruction.rect().bottomLeft()).y() < panel.detail.mapTo(panel, panel.detail.rect().topLeft()).y()
    assert panel.detail.mapTo(panel, panel.detail.rect().bottomLeft()).y() < panel.timing.y()
    assert panel.timing.geometry().bottom() < panel.scroll.y()


def test_expanded_camera_details_scroll_into_view_at_compact_size(panel):
    panel.set_instruction("Sit normally", "Return to your usual working posture.")
    panel.resize(480, 500)
    panel.show()
    QApplication.processEvents()
    panel.details_button.click()
    QApplication.processEvents()
    QApplication.processEvents()
    viewport = panel.scroll.viewport()
    assert viewport.rect().contains(panel.check_group.mapTo(viewport, panel.check_group.rect().center()))
    panel.begin()
    assert panel.scroll.verticalScrollBar().value() == 0


def test_pose_and_countdown_stay_visible_when_scrolling_details(panel):
    panel.set_instruction("Sit tall", "Relax your shoulders.")
    panel.set_caption("Get ready · 3s")
    panel.details_button.click()
    panel.resize(480, 500)
    panel.show()
    QApplication.processEvents()
    before = panel.instruction.mapTo(panel, panel.instruction.rect().topLeft())
    panel.scroll.verticalScrollBar().setValue(panel.scroll.verticalScrollBar().maximum())
    QApplication.processEvents()
    assert panel.instruction.mapTo(panel, panel.instruction.rect().topLeft()) == before
    assert not panel.scroll.isAncestorOf(panel.instruction)
    assert not panel.scroll.isAncestorOf(panel.caption)
    assert panel.instruction.mapTo(panel, panel.instruction.rect().bottomLeft()).y() < panel.scroll.y()
    assert panel.caption.mapTo(panel, panel.caption.rect().bottomLeft()).y() < panel.scroll.y()


def test_failure_never_offers_start(panel):
    panel.show_result(False, "Not saved")
    assert panel.start_button.isHidden()
    assert panel.feedback_group.isHidden()
    assert not panel.retry_button.isHidden()


def test_camera_preview_preserves_pause_clears_failed_and_closed_frames(panel):
    worker = Mock(camera_state="running", camera_error="Camera disconnected.")
    worker.isRunning.return_value = False
    controller = SimpleNamespace(worker=worker, machine=SimpleNamespace(state=State.PAUSED),
                                 cfg={"camera_index": 0}, _suspended=False, _idle_stopped=False,
                                 _restart_pending=False, _cal=None, restart_camera=Mock(),
                                 _preview_changed=Mock())
    view = CameraPreviewWindow(controller)
    controller._camera_preview = view
    view.setAttribute(Qt.WA_DontShowOnScreen)
    try:
        view.show()
        assert "Off" in view.status.text()
        worker.start.assert_not_called()
        controller.restart_camera.assert_not_called()
        image = QImage(64, 48, QImage.Format_RGB32)
        image.fill(Qt.black)
        payload = PreviewPayload(image)
        view.update_frame(payload)
        assert view.video.image is None
        controller.machine.state = State.GOOD
        worker.isRunning.return_value = True
        view.refresh()
        view.update_frame(payload)
        assert view.video.image is image
        class OldWorker(QObject):
            preview = Signal(object)
        old = OldWorker()
        old.preview.connect(view.update_frame)
        old.preview.emit(PreviewPayload(QImage(8, 8, QImage.Format_RGB32)))
        assert view.video.image is image
        worker.camera_state = "reconnecting"
        view.refresh()
        assert view.video.image is None
        assert not view.retry_button.isHidden()
        view.retry_button.click()
        controller.restart_camera.assert_called_once()
        worker.camera_state = "running"
        view.close()
        view.update_frame(payload)
        assert view.video.image is None
        assert controller._preview_changed.call_count == 2
        assert not view.timer.isActive()
    finally:
        view.close()
        view.deleteLater()


def test_calibration_camera_error_clears_mirror_without_cancelling(panel):
    image = QImage(64, 48, QImage.Format_RGB32)
    image.fill(Qt.black)
    payload = PreviewPayload(image)
    panel.update_frame(payload)
    panel.set_checks({"present": True})
    retry = Mock()
    panel.camera_retry_requested.connect(retry)
    panel.camera_unavailable("Camera disconnected.")
    assert panel.video.image is None
    assert "Retrying automatically" in panel.caption.text()
    assert panel.check_labels["present"].text() == "Face and shoulders: Waiting"
    panel.camera_retry_button.click()
    retry.assert_called_once()
    panel.update_frame(payload)
    assert panel.video.image is image
    assert panel.camera_retry_button.isHidden()
