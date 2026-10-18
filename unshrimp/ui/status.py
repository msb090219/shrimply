"""Shared camera and calibration descriptions for desktop surfaces."""
from datetime import datetime

from unshrimp.core.states import State


def camera_mode(app):
    """One camera policy shared by the controller and its status surfaces."""
    if getattr(app, "_quitting", False) or app._suspended:
        return "off"
    if app._cal is not None:
        return "calibration"
    if app.machine.state is not State.PAUSED and not app._idle_stopped:
        return "tracking"
    preview = getattr(app, "_camera_preview", None)
    return "preview" if preview is not None and preview.isVisible() else "off"


def camera_status(app):
    running = app.worker.isRunning()
    mode = camera_mode(app)
    if mode == "off":
        if running:
            return "stopping", "Releasing the camera. Please wait."
        if app.machine.state is State.PAUSED and not app._suspended:
            return "paused", "The camera is off. Open Camera preview for framing, or resume tracking."
        return "off", ("The camera is off while the computer sleeps." if app._suspended
                       else "The camera is off while idle. Tracking resumes when computer activity returns.")
    if app._restart_pending:
        return "reconnecting", "Waiting for the previous camera to close before reconnecting."
    if not running:
        return "off", "The camera is not running. Retry or check the selected device in Settings."
    if app.worker.camera_state == "reconnecting":
        return "reconnecting", (app.worker.camera_error +
            " Check camera permissions and close other apps using the camera. Retrying automatically.")
    if app.worker.camera_state == "running":
        if mode == "preview":
            return "preview", "Preview only. Posture tracking is paused; no posture history or sitting time is counted. Close this preview to release the camera."
        if mode == "calibration":
            return "running", "Calibrating. Normal posture tracking and reminders are suspended."
        return "running", "Camera frames are being processed on this device."
    return "starting", "Opening the camera and waiting for the first processed frame."


def calibration_status(app):
    if app._cal is not None:
        return ("Calibration in progress. Your saved baseline is kept until a new one succeeds."
                if app.baseline is not None else "Calibration in progress. No baseline has been saved yet.")
    baseline = app.baseline
    if baseline is None:
        return "Not calibrated. Calibrate before posture can be scored."
    if baseline.created_at:
        return "Saved " + datetime.fromtimestamp(baseline.created_at).strftime("%d %b %Y, %H:%M")
    return "Saved baseline available"
