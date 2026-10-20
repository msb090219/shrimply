"""UnshrimpApp — the controller wiring worker, state machine, tray, HUD,
camera preview, mascot, and the adaptive inference-rate engine."""
from __future__ import annotations

import time
import math
import sqlite3
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer

import config as config_mod
from unshrimp.core.baseline import Baseline
from unshrimp.core.breaks import BreakReminder
from unshrimp.core.calibration import CalibrationSession
from unshrimp.core.idle import IDLE_STOP_S, seconds_idle, should_idle_stop
from unshrimp.core.history import HistoryAccumulator
from unshrimp.core.rates import inference_rate
from unshrimp.core.smoother import Smoother
from unshrimp.core.states import (
    EVENT_ALERT,
    EVENT_CAM_ERROR,
    EVENT_RECOVERED,
    EVENT_RENAG,
    State,
    PostureStateMachine,
    Thresholds,
)
from unshrimp.storage.db import PostureLog
from unshrimp.vision.worker import VisionWorker
from .hud import Hud
from .mascot import MascotGroup
from .preview import PreviewWindow, CameraPreviewWindow
from .tray import Tray
from .main_window import MainWindow
from .break_prompt import BreakPrompt
from .status import camera_mode

def _chime() -> None:
    """Cross-platform system beep (Windows used winsound before; Qt covers all)."""
    from PySide6.QtWidgets import QApplication

    QApplication.beep()

_CAL_TOASTS = {
    "enter_tall": (
        "Sit tall",
        "Spine long · shoulders back & down · chin gently tucked. Hold ~10 s.",
    ),
    "enter_normal": (
        "Sit normally",
        "Return to your everyday working posture. This sets your baseline. Hold ~8 s.",
    ),
    "enter_hunch": (
        "Demonstrate a comfortable slouch",
        "Let your chin move forward and your back round gently. Don't strain. Hold ~6 s.",
    ),
    "enter_verify": (
        "Sit normally again",
        "Return to your everyday posture while we verify your baseline. Hold ~12 s.",
    ),
}

_CAL_INSTRUCTIONS = {
    "setup": ("Face your screen", "Look at the centre. Keep your face and both shoulders visible."),
    "enter_tall": ("Sit tall", "Lengthen your spine gently. Relax your shoulders and tuck your chin slightly."),
    "enter_normal": ("Sit normally", "Return to your usual working posture. Don't deliberately straighten up."),
    "enter_hunch": ("Slouch comfortably", "Let your chin move forward and your back round gently. Don't strain."),
    "enter_verify": ("Sit normally again", "Return to your usual working posture while we check the baseline."),
}


class UnshrimpApp(QObject):
    def __init__(self, models_dir: Path):
        super().__init__()
        self.models_dir = Path(models_dir)
        self.cfg = config_mod.load()
        from . import theme
        theme.set_mode(self.cfg.get("theme_mode", "dark"))
        self.machine = PostureStateMachine(
            Thresholds(
                drift=self.cfg["drift"],
                bad=self.cfg["bad"],
                grace_s=self.cfg["grace_s"],
                renag_s=self.cfg["renag_s"],
                away_s=self.cfg["away_s"],
                recovery_s=self.cfg["recovery_s"],
            )
        )
        self.baseline: Baseline | None = None
        if self.cfg.get("baseline"):
            try:
                self.baseline = Baseline.from_dict(self.cfg["baseline"])
                self.machine.mark_calibrated()
            except (KeyError, TypeError, ValueError):
                # stale calibration format or corrupt data — start fresh
                self.cfg["baseline"] = None
        self.smoother = Smoother()  # 2.5s time window, min 3 frames, 30° yaw gate

        self.hud = Hud()
        hud_cfg = self.cfg["hud"]
        self.hud.set_orientation(hud_cfg.get("orientation", "horizontal"))
        self.hud.set_size(hud_cfg.get("size", "m"))
        self.hud.set_compact(hud_cfg.get("compact", False))
        self.hud.setWindowOpacity(hud_cfg.get("opacity", 1.0))
        if hud_cfg.get("x") is not None and hud_cfg.get("y") is not None:
            self.hud.move(hud_cfg["x"], hud_cfg["y"])
        self._rescue_offscreen_hud()
        self.hud.setVisible(hud_cfg.get("visible", True))

        self.tray = Tray()
        self.tray.unavailable.connect(self._ensure_controls_visible)
        self.tray.calibrate_requested.connect(self.start_calibration)
        self.tray.pause_toggled.connect(self._on_pause_toggled)
        self.tray.hud_toggled.connect(self._on_hud_toggled)
        self.tray.compact_toggled.connect(self._on_compact_toggled)
        self.tray.sync_compact_action(self.hud.compact)
        self.tray.settings_requested.connect(lambda: QTimer.singleShot(0, self._open_settings))
        self.tray.about_requested.connect(lambda: QTimer.singleShot(0, self._show_about))
        self.tray.mascot_toggled.connect(self.set_mascot_enabled)
        self.tray.quit_requested.connect(self._on_quit)
        self.tray.continue_anyway.connect(self._on_continue_anyway)
        self.tray.sync_hud_action(self.hud.isVisible())
        self.hud.doubleClicked.connect(self._on_hud_double_clicked)
        self.hud.pause_requested.connect(
            lambda: self._on_pause_toggled(self._cal is not None or self.machine.state is not State.PAUSED))
        # the HUD context menu mirrors the tray menu, so the app stays
        # fully controllable even if a platform never shows the tray icon
        self.hud.set_context_menu(self.tray.menu)

        self.worker = VisionWorker(
            self.models_dir, self.cfg["camera_index"], self.cfg["fps"]
        )
        self.worker.frame.connect(self._on_frame)
        self.worker.cam_error.connect(self._on_cam_error)
        self.worker.cam_recovered.connect(self._on_cam_recovered)
        self.worker.finished.connect(self._on_worker_finished)
        self._restart_pending = False
        self._shutdown_done = False
        self._settings_dlg = None
        self._about_dlg = None
        self._camera_preview = None

        # calibration camera preview (hidden until a calibration runs)
        self.preview_win = PreviewWindow()
        self.worker.preview.connect(self._on_calibration_preview)
        self.preview_win.cancel_requested.connect(self._cancel_calibration)
        self.preview_win.retry_requested.connect(self.start_calibration)
        self.preview_win.camera_retry_requested.connect(self.restart_camera)
        self.preview_win.continue_requested.connect(self._on_continue_anyway)
        self.preview_win.start_requested.connect(self._start_after_calibration)

        # calibration bookkeeping
        self._cal: CalibrationSession | None = None

        # the mascot: a very large shrimp that fades in as you slouch
        self.mascot = MascotGroup()
        self.apply_motion_settings()
        self._good_streak = 0

        # system-idle camera stop: 5 min without input anywhere → camera off
        self._idle_stopped = False
        self._suspended = False
        self.idle_timer = QTimer(self)
        self.idle_timer.setInterval(5000)
        self.idle_timer.timeout.connect(self._idle_check)

        # posture history + stretch reminders
        self.log = PostureLog(config_mod.APP_DIR / "log.db")
        self.session_id = self.log.start_session()
        self.history = HistoryAccumulator()
        self._history_save_failed = False
        self.breaks = BreakReminder(bool(self.cfg["reminder_enabled"]),
                                    self.cfg["reminder_interval_min"] * 60,
                                    self.cfg["reminder_break_min"] * 60)
        self.break_prompt = BreakPrompt(break_minutes=self.cfg["reminder_break_min"])
        self.break_prompt.take_requested.connect(self._take_break)
        self.break_prompt.later_requested.connect(self._snooze_break)
        self.break_prompt.skip_requested.connect(self._skip_break)
        self.break_prompt.end_requested.connect(self._end_break)
        self.hud.moved.connect(self._position_break_prompt)
        self._break_suggestion = "Stand up for a short walk or a comfortable stretch."
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(1000)
        self.reminder_timer.timeout.connect(self._reminder_fire)
        self._ex_i = 0

        self._quitting = False
        self._display_deviation = None
        self.main_window = MainWindow(self)
        self.tray.open_requested.connect(lambda: QTimer.singleShot(0, self._open_main_window))
        self.tray.menu.aboutToShow.connect(self._refresh_tray)
        self._sync_uncalibrated_ui()
        self._refresh_tray()

    def _rescue_offscreen_hud(self) -> None:
        """If the saved HUD position isn't on any connected screen (e.g. a
        monitor was unplugged since last run), bring it home."""
        from PySide6.QtGui import QGuiApplication

        from unshrimp import diag

        screens = [s.availableGeometry() for s in QGuiApplication.screens()]
        if not screens:
            return
        frame = self.hud.frameGeometry()
        visible = [g for g in screens if frame.intersects(g)]
        if visible:
            area = max(visible, key=lambda g: frame.intersected(g).width() * frame.intersected(g).height())
            self.hud.move(max(area.left(), min(frame.left(), area.right() - self.hud.width() + 1)),
                          max(area.top(), min(frame.top(), area.bottom() - self.hud.height() + 1)))
            return
        prim = QGuiApplication.primaryScreen().availableGeometry()
        self.hud.move(
            max(prim.left(), prim.right() - self.hud.width() - 24),
            prim.top() + 80,
        )
        diag.log(
            f"hud: saved position off-screen "
            f"({self.cfg['hud'].get('x')},{self.cfg['hud'].get('y')}) — moved on-screen"
        )

    # ------------------------------------------------------------------
    def start(self, *, background: bool = False) -> None:
        from unshrimp import diag

        diag.log(f"app: starting (baseline={'yes' if self.baseline else 'no'})")
        QTimer.singleShot(0, self.tray.show_when_ready)
        needs_setup = self.baseline is None and not self.cfg.get("welcome_seen", False)
        if self.cfg.get("tracking_paused", False):
            self.machine.pause()
            self.hud.set_status("paused", "paused")
            self._refresh_tray()
        if needs_setup:
            self._show_welcome()
            self.cfg["welcome_seen"] = True
            try:
                config_mod.save(self.cfg)
            except OSError as exc:
                diag.log(f"app: could not save welcome preference: {exc}")
        if self.machine.state is not State.PAUSED and not self.worker.isRunning() and not self._restart_pending:
            self.worker.start()
        self.reminder_timer.start()
        self.idle_timer.start()
        if (not background or needs_setup) and self._cal is None:
            self._open_main_window()

    def _ensure_controls_visible(self) -> None:
        if not self._quitting and not self.hud.isVisible() and not self.main_window.isVisible():
            self._open_main_window()

    def _open_main_window(self) -> None:
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        else:
            self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _show_welcome(self) -> None:
        from .welcome import WelcomeDialog

        dlg = WelcomeDialog()
        if dlg.exec() and dlg.calibrate_requested:
            self.start_calibration()
        else:
            self._on_pause_toggled(True)

    def _show_about(self) -> None:
        from .welcome import WelcomeDialog

        if self._about_dlg is None:
            dialog = WelcomeDialog(about_mode=True)
            self._about_dlg = dialog
            dialog.finished.connect(lambda _: setattr(self, "_about_dlg", None))
            dialog.finished.connect(dialog.deleteLater)
        self._about_dlg.show()
        self._about_dlg.raise_()
        self._about_dlg.activateWindow()

    def _on_hud_double_clicked(self) -> None:
        self._open_main_window()

    # ------------------------------------------------------------------
    # Settings commits a patch; tray actions continue to apply immediately.
    def save_cfg(self) -> None:
        config_mod.save(self.cfg)

    def apply_preferences(self, changes, startup=None):
        """Save before applying; merge only edited fields into current runtime state."""
        import copy
        import unshrimp.autostart as autostart
        candidate = copy.deepcopy(self.cfg)
        for key, value in changes.items():
            if key == "hud":
                candidate["hud"].update(value)
            else:
                candidate[key] = value
        previous_startup = autostart.is_enabled() if startup is not None else None
        startup_changed = startup is not None and startup != previous_startup
        if startup_changed:
            autostart.set_enabled(startup)
        try:
            config_mod.save(candidate)
        except OSError:
            if startup_changed:
                autostart.set_enabled(previous_startup)
            raise
        self.cfg.update(candidate)
        if "theme_mode" in changes:
            from . import theme
            theme.set_mode(candidate["theme_mode"])
        if any(key in changes for key in ("grace_s", "renag_s", "away_s")):
            self.apply_thresholds(save=False)
        if any(key in changes for key in ("reminder_enabled", "reminder_interval_min", "reminder_break_min", "exercises")):
            self.apply_breaks(save=False)
        if any(key.startswith("mascot_") or key == "reduce_motion" for key in changes):
            self.apply_mascot_settings(save=False)
        if "hud" in changes:
            hud = candidate["hud"]
            self.hud.set_orientation(hud.get("orientation", "horizontal"))
            self.hud.set_size(hud.get("size", "m"))
            self.hud.set_compact(hud.get("compact", False))
            self.hud.setWindowOpacity(hud.get("opacity", 1.0))
            self.hud.setVisible(hud.get("visible", True))
            self.tray.sync_hud_action(hud.get("visible", True))
            self.tray.sync_compact_action(hud.get("compact", False))
            if "x" in changes["hud"]:
                area = self.hud.screen().availableGeometry()
                self.hud.move(max(area.left(), area.right() - self.hud.width() - 24), area.top() + 80)
        if "camera_index" in changes:
            self.restart_camera()

    def apply_breaks(self, save=True) -> None:
        """Apply reminder settings without resetting time for unrelated edits."""
        self.breaks.configure(bool(self.cfg["reminder_enabled"]),
                              self.cfg["reminder_interval_min"] * 60,
                              self.cfg["reminder_break_min"] * 60)
        self.break_prompt.set_break_minutes(self.cfg["reminder_break_min"])
        self._reminder_fire()
        if save:
            config_mod.save(self.cfg)

    def apply_thresholds(self, save=True) -> None:
        self.machine.thr.grace_s = self.cfg["grace_s"]
        self.machine.thr.renag_s = self.cfg["renag_s"]
        self.machine.thr.away_s = self.cfg["away_s"]
        if save:
            config_mod.save(self.cfg)

    def apply_mascot_settings(self, save=True) -> None:
        self.apply_motion_settings()
        if not self.cfg.get("mascot_enabled"):
            self.mascot.force_hide()
        self.tray.set_mascot_checked(bool(self.cfg.get("mascot_enabled")))
        if save:
            config_mod.save(self.cfg)

    def apply_motion_settings(self) -> None:
        reduced = bool(self.cfg.get("reduce_motion", False))
        self.preview_win.countdown.set_reduced_motion(reduced)
        self.mascot.reduce_motion = reduced
        self.mascot.position = self.cfg.get("mascot_position", "center")
        self.mascot.screen_name = self.cfg.get("mascot_screen", "")
        self.mascot.bad_hold_s = max(0, min(15, float(self.cfg.get("mascot_bad_hold_s", 2))))
        self.mascot.recovery_hold_s = max(0, min(15, float(self.cfg.get("mascot_recovery_hold_s", 3))))
        self.mascot.set_options(float(self.cfg.get("mascot_opacity", .87)),
                                str(self.cfg.get("mascot_size", "m")),
                                bool(self.cfg.get("mascot_bob", True)) and not reduced,
                                str(self.cfg.get("mascot_entrance", "rise")),
                                float(self.cfg.get("bad", 1.5)),
                                str(self.cfg.get("mascot_style", "shrimp")))

    def set_mascot_enabled(self, on: bool) -> None:
        self.cfg["mascot_enabled"] = on
        self.apply_mascot_settings()

    def _toast(self, title: str, body: str, seconds: int = 6) -> None:
        if self.cfg.get("toasts_enabled", True):
            self.tray.toast(title, body, seconds)

    def shutdown(self) -> bool:
        if self._shutdown_done:
            return True
        self._quitting = True
        self.preview_win.stop_preview()
        self.preview_win.hide()
        self.mascot.force_hide()
        if self._camera_preview is not None:
            self._camera_preview.close()
        self._restart_pending = False
        self.reminder_timer.stop()
        if self._about_dlg is not None:
            self._about_dlg.close()
        self.break_prompt.hide()
        self.idle_timer.stop()
        self.worker.stop()
        if self.worker.isRunning():
            return False
        self._try_flush_bucket()
        try:
            self.log.end_session(self.session_id)
        except (OSError, sqlite3.Error) as exc:
            from unshrimp import diag
            diag.log(f"history: could not close session: {exc}")
        self.cfg["hud"]["x"], self.cfg["hud"]["y"] = (
            self.hud.pos().x(),
            self.hud.pos().y(),
        )
        self.cfg["hud"]["visible"] = self.hud.isVisible()
        try:
            config_mod.save(self.cfg)
        except OSError as exc:
            from unshrimp import diag
            diag.log(f"app: could not save final window state: {exc}")
        try:
            self.log.close()
        except sqlite3.Error as exc:
            from unshrimp import diag
            diag.log(f"history: could not close database: {exc}")
        self.hud.hide()
        self._shutdown_done = True
        return True

    # ------------------------------------------------------------------
    # calibration flow (guided, v3)
    def _on_calibration_preview(self, payload) -> None:
        if self.sender() is self.worker and self._cal is not None and not self._suspended:
            self.preview_win.update_frame(payload)

    def _preview_changed(self) -> None:
        self.worker.preview_enabled = self._cal is not None or (
            self._camera_preview is not None and self._camera_preview.isVisible())
        if camera_mode(self) in ("off", "preview"):
            self._restart_worker()
        else:
            self.worker.wake()
        if self._cal is None and (self.machine.state is State.PAUSED or self._idle_stopped):
            self._render(self.machine.state, None)
        self._refresh_tray()

    def open_camera_preview(self) -> None:
        if self._cal is not None:
            self.start_calibration()
            return
        if self._camera_preview is None:
            self._camera_preview = CameraPreviewWindow(self)
            self.worker.preview.connect(self._camera_preview.update_frame)
        self._camera_preview.show()
        self._camera_preview.raise_()
        self._camera_preview.activateWindow()

    def start_calibration(self) -> None:
        if self._cal is not None:
            self.preview_win.show()
            self.preview_win.raise_()
            self.preview_win.activateWindow()
            return
        if self._camera_preview is not None:
            self._camera_preview.close()
        self._end_history_segment()
        self.breaks.pause()
        self.break_prompt.hide()
        self._cal_was_paused = self.machine.state is State.PAUSED
        needs_restart = self._idle_stopped or self.machine.state is State.PAUSED
        self._idle_stopped = False
        self._cal = CalibrationSession()
        self.machine.pause()  # suspend scoring clocks without changing the saved pause preference
        self.smoother.reset()
        self._good_streak = 0
        self.tray.show_continue(False)
        self.mascot.force_hide()
        self.worker.preview_enabled = True
        self.worker.inference_interval = 0.5
        if needs_restart or not self.worker.isRunning():
            self._restart_worker()
        self.preview_win.begin()
        self.preview_win.set_instruction(*_CAL_INSTRUCTIONS["setup"])
        self.preview_win.set_caption("Checking your camera…")
        self.preview_win.show()
        self._place_preview()
        self.preview_win.raise_()
        self._toast(
            "Setup check",
            "Sit facing the camera and look at the CENTER of your screen…",
        )
        self.hud.set_status("calibrating", "setup 0/5")

    def _on_continue_anyway(self) -> None:
        if self._cal is not None and self._cal.phase == "setup":
            res = self._cal.force_continue(time.monotonic())
            self._apply_cal_result(res)
            self.tray.show_continue(False)
            self.preview_win.set_override_available(False)
            self._toast(
                "Setup checks skipped",
                "Calibrating anyway — watch for wobblier scoring.",
            )

    def _place_preview(self) -> None:
        """Keep calibration independent of the floating indicator's position."""
        screen = self.hud.screen()
        if screen:
            self.preview_win.move(screen.availableGeometry().center() - self.preview_win.rect().center())

    def _cancel_calibration(self) -> None:
        if self._cal is None:
            return
        from unshrimp import diag

        diag.log("cal: cancelled — previous baseline unchanged")
        self._cal = None
        self.worker.preview_enabled = False
        self.preview_win.stop_preview()
        self.preview_win.hide()
        self.tray.show_continue(False)
        self._end_history_segment()
        self.breaks.pause()
        self.break_prompt.hide()
        self.smoother.reset()
        self._good_streak = 0
        if self._quitting:
            return
        if self._cal_was_paused:
            self._on_pause_toggled(True)
        else:
            self.machine.resume(time.monotonic())
            if self.baseline is None:
                self._sync_uncalibrated_ui()
            else:
                self._render(self.machine.state, None)

    def _cal_step(self, sig) -> None:
        from unshrimp import diag

        diag.sample("calibration", phase=self._cal.phase, ok=sig.ok,
                    head_pitch=sig.head_pitch, head_yaw=sig.head_yaw,
                    head_roll=sig.head_roll, head_sink=sig.head_sink,
                    lean_in=sig.lean_in, shoulder_w=sig.shoulder_w,
                    luminance=sig.luminance)
        res = self._cal.feed(sig, time.monotonic())
        self._apply_cal_result(res)

    def _apply_cal_result(self, res) -> None:
        from unshrimp import diag

        self.hud.set_status("calibrating", res.progress or res.phase)
        for ev in res.events:
            diag.log(f"cal: {ev}")
        caption = res.progress or res.phase
        if res.activity is not None:
            caption = {"preparing": "Get ready", "capturing": "Hold still",
                       "paused": "Collection paused",
                       "checking": "Keep holding · Checking sample quality"}[res.activity]
        if res.phase == "setup":
            caption = "Checking your camera…"
        if res.phase in ("tall", "normal", "hunch", "verify") and caption.startswith(("TALL", "NORMAL", "HUNCH", "CHECK")):
            caption = "Hold still · " + caption.split(" ", 1)[-1]
        if res.hint and not caption.startswith(("Get ready", "Ready to collect")) and not res.progress.startswith("Ready to collect"):
            caption = f"{caption} · {res.hint}"
        self.preview_win.set_caption(caption)
        self.preview_win.countdown.set_progress(res)
        self.preview_win.set_phase(res.phase)
        if res.phase != "setup":
            self.preview_win.set_override_available(False)
        if self._cal is not None:
            self.preview_win.set_checks(self._cal.setup_report)
        for ev in res.events:
            if ev in _CAL_TOASTS:
                self._toast(*_CAL_TOASTS[ev])
                self.preview_win.set_instruction(*_CAL_INSTRUCTIONS[ev])
                if ev == "enter_tall":
                    self.tray.show_continue(False)
            elif ev == "setup_stuck":
                self.tray.show_continue(True)
                self.preview_win.set_override_available(True)
                self._toast(
                    "Setup check stuck",
                    "Review the camera checks in the calibration window before continuing.",
                )
            elif ev.startswith("failed:"):
                self._toast("Calibration failed", res.hint or ev)
            elif ev == "calibrated" and res.baseline is not None:
                if not self._accept_baseline(res.baseline):
                    res.phase = "failed"
                    res.hint = "Calibration was not saved. Check that your settings folder is writable and try again."
                    self._toast("Calibration was not saved", res.hint)

        if res.phase in ("done", "failed"):
            self._cal = None
            if res.phase == "failed" and not self._cal_was_paused:
                self.machine.resume(time.monotonic())
            self.tray.show_continue(False)
            self.worker.preview_enabled = False
            if self.baseline is None:
                self._sync_uncalibrated_ui()
            else:
                self._render(self.machine.state, None)
            if res.phase == "failed":
                if self._cal_was_paused:
                    self._on_pause_toggled(True)
                retained = ("Your previous calibration is still active." if self.baseline
                            else "Tracking needs a successful calibration before it can start.")
                self.preview_win.show_result(False, f"{res.hint or 'Calibration could not be completed.'}\n{retained}")
            else:
                self._on_pause_toggled(True)
                self.preview_win.show_result(True, "Your new baseline was saved. The camera can now track against it.")

    def _start_after_calibration(self) -> None:
        if self._cal is not None or self.baseline is None:
            return
        self.preview_win.hide()
        if self.machine.state is State.PAUSED:
            self._on_pause_toggled(False)
        self._open_main_window()

    def _accept_baseline(self, built: Baseline) -> bool:
        candidate = dict(self.cfg, baseline=built.to_dict(), tracking_paused=True)
        try:
            config_mod.save(candidate)
        except OSError as exc:
            from unshrimp import diag
            diag.log(f"cal: could not save baseline: {exc}")
            return False
        self.cfg.update(baseline=candidate["baseline"], tracking_paused=True)
        self.baseline = built
        self.machine.mark_calibrated()
        self.smoother.reset()
        self._good_streak = 0
        tune = (built.report or {}).get("tune", 1.0)
        notes = " (auto-tuned ✓)" if tune > 1.0 else ""
        if (built.report or {}).get("degraded"):
            notes += " · setup checks were skipped"
        self._toast("Calibration saved", f"Choose Start tracking when you're ready{notes}.")
        self.hud.set_live(0.0, "good")
        return True

    # ------------------------------------------------------------------
    def _on_frame(self, sig) -> None:
        if isinstance(self, QObject) and self.sender() is not None and self.sender() is not self.worker:
            return
        if self._quitting or self._suspended or self._restart_pending:
            return
        if self._cal is not None:
            self._cal_step(sig)
            return

        if self._idle_stopped or self.machine.state is State.PAUSED:
            return
        if self.machine.state is State.CAMERA_ERROR:
            self._on_cam_recovered()

        if self.baseline is None:
            return

        now = time.monotonic()
        if self.breaks.observe(sig.ok, now):
            exs = self.cfg.get("exercises") or []
            if exs:
                ex = exs[self._ex_i % len(exs)]
                self._ex_i += 1
                self._break_suggestion = f"{ex.get('name', 'Stretch')} — {ex.get('how', '')}"[:500]
            else:
                self._break_suggestion = "Stand up for a short walk or a comfortable stretch."
            self.break_prompt.set_suggestion(self._break_suggestion)
        self._reminder_fire()
        smoothed = self.smoother.push(sig, now)
        dev = (
            self.baseline.deviation(smoothed, sensitivity=self.cfg["sensitivity"])
            if smoothed is not None
            else None
        )
        previous = self.machine.state
        state, events = self.machine.update(dev, now)
        from unshrimp import diag

        diag.sample("posture", state=state.value, deviation=dev, raw_ok=sig.ok)
        if state is not previous:
            diag.log(f"posture: {previous.value} -> {state.value}")
        self._accumulate(state, dev)
        self._render(state, dev)
        self._adapt(state, dev)
        if state is State.AWAY and sig.ok and sig.head_yaw is not None and abs(sig.head_yaw) <= self.smoother.max_yaw_deg:
            self.worker.inference_interval = 1 / inference_rate(state.value, 0, returning=True)
        for ev in events:
            self._handle_event(ev)

    def _idle_check(self) -> None:
        """Poll system idle: stop the camera after long silence, restart on
        any input. Never while calibrating or manually paused."""
        if self._quitting:
            return
        from unshrimp import diag

        if self._suspended:
            return
        idle = seconds_idle()
        if not self._idle_stopped:
            if should_idle_stop(
                idle, self._cal is not None, self.machine.state is State.PAUSED
            ):
                self._idle_stopped = True
                self._end_history_segment()
                self.breaks.pause()
                self.break_prompt.hide()
                diag.log(f"idle: {idle:.0f}s without input — camera off")
                self.mascot.force_hide()
                self._restart_worker()
                self.smoother.reset()
        elif idle < IDLE_STOP_S:  # some input came back
            self._idle_stopped = False
            diag.log("idle: input returned — camera on")
            self._restart_worker()

    def _adapt(self, state: State, dev: float | None) -> None:
        """Mascot visibility + adaptive inference rate, driven per frame."""
        scorable = state.value in ("good", "drifting", "bad")
        if self.breaks.in_break:
            self.mascot.force_hide()
        elif self.cfg.get("mascot_enabled", True):
            self.mascot.set_level(dev if scorable else None, bad=state is State.BAD)
        elif self.mascot.isVisible():
            self.mascot.force_hide()

        if dev is not None and dev < 0.6:
            self._good_streak += 1
        else:
            self._good_streak = 0
        rate = inference_rate(state.value, self._good_streak)
        interval = 1.0 / rate
        if getattr(self.worker, "inference_interval", None) != interval:
            self.worker.inference_interval = interval

    def _accumulate(self, state: State, dev: float | None) -> None:
        wall = time.time()
        self.history.push(state.value if dev is not None else None, time.monotonic(), wall)
        if self.history.minutes and min(self.history.minutes) < int(wall // 60) * 60:
            self._try_flush_bucket()

    def _end_history_segment(self) -> None:
        self.history.reset()
        self._try_flush_bucket()

    def _try_flush_bucket(self) -> None:
        try:
            self._flush_bucket()
        except (OSError, sqlite3.Error) as exc:
            from unshrimp import diag
            if not self._history_save_failed:
                diag.log(f"history: could not save pending time: {exc}")
            self._history_save_failed = True
        else:
            self._history_save_failed = False

    def _flush_bucket(self) -> None:
        for minute, bucket in list(self.history.minutes.items()):
            self.log.record_duration(minute, bucket["good"], bucket["drifting"], bucket["bad"])
            del self.history.minutes[minute]

    def _reminder_fire(self) -> None:
        now = time.monotonic()
        self.breaks.tick(now)
        available = not (self._quitting or self._suspended or self._idle_stopped
                         or self._restart_pending or self._cal is not None
                         or self.machine.state in (State.PAUSED, State.CAMERA_ERROR)
                         or self.baseline is None)
        visible = (available and self.breaks.enabled and (self.breaks.in_break
                   or (self.breaks.pending and self.breaks.recently_present(now))))
        self.hud.set_break_prompt_visible(visible)
        if visible:
            self.break_prompt.set_break_state(self.breaks.break_remaining(now) if self.breaks.in_break else None)
            if not self.break_prompt.isVisible():
                self.break_prompt.show()
            self._position_break_prompt()
        else:
            self.break_prompt.hide()
        self._refresh_tray()

    def _refresh_tray(self) -> None:
        state = self.machine.state
        key = state.value
        if self._suspended:
            key = "sleeping"
        elif self._cal is not None:
            key = "calibrating"
        elif camera_mode(self) == "preview":
            key = "preview"
        elif state is State.PAUSED:
            key = "paused"
        elif self._idle_stopped:
            key = "idle"
        elif self.baseline is None:
            key = "uncalibrated"
        elif state is State.CAMERA_ERROR:
            key = "camera_error"
        elif self.breaks.in_break:
            key = "break"
        elif self._restart_pending or self._display_deviation is None:
            key = "starting"
        self.tray.set_state(key, "")
        self.tray.set_paused_ui(state is State.PAUSED)
        self.tray.set_controls(self._cal is not None, self._suspended)
        self.tray.sync_hud_action(self.hud.isVisible())
        self.tray.set_mascot_checked(bool(self.cfg.get("mascot_enabled", True)))
        text = ""
        if self.breaks.enabled:
            if self.breaks.in_break:
                seconds = math.ceil(self.breaks.break_remaining(time.monotonic()))
                text = f"Break · {seconds // 60}:{seconds % 60:02d} remaining"
            elif self.breaks.pending:
                text = "Break reminder due"
            else:
                prefix = "Snoozed" if self.breaks.snoozed else "Next break"
                text = f"{prefix} · {math.ceil(self.breaks.remaining / 60)} min of sitting"
        self.tray.set_break_text(text)

    def _position_break_prompt(self) -> None:
        if not self.break_prompt.isVisible():
            return
        screen = self.hud.screen()
        if screen is None:
            return
        bounds = screen.availableGeometry()
        prompt = self.break_prompt
        width = (max(340, self.hud.bar.width()) if self.hud.orientation == "vertical"
                 else self.hud.bar.width()) if self.hud.isVisible() else 340
        if prompt.width() != width:
            prompt.setFixedWidth(width)
            prompt.adjustSize()
        anchor = self.hud.frameGeometry()
        anchor.setHeight(self.hud.bar.height())
        x = anchor.left() if self.hud.isVisible() else bounds.right() - prompt.width() - 16
        y = anchor.top() + anchor.height() + 8 if self.hud.isVisible() else bounds.bottom() - prompt.height() - 16
        if y + prompt.height() > bounds.bottom():
            y = anchor.top() - prompt.height() - 8
        prompt.move(max(bounds.left(), min(x, bounds.right() - prompt.width() + 1)),
                    max(bounds.top(), min(y, bounds.bottom() - prompt.height() + 1)))

    def _take_break(self) -> None:
        self.breaks.take_break(time.monotonic())
        self.mascot.force_hide()
        self._reminder_fire()

    def _end_break(self) -> None:
        self.breaks.end_break()
        self._reminder_fire()

    def _snooze_break(self, minutes=5) -> None:
        self.breaks.snooze(minutes * 60)
        self._reminder_fire()

    def _skip_break(self) -> None:
        self.breaks.skip()
        self._reminder_fire()

    # ------------------------------------------------------------------
    def _render(self, state: State, dev: float | None) -> None:
        self._display_deviation = dev
        # dev is None while the smoother warms up (or the head is turned):
        # show the band colour without a number
        if self._cal is not None:
            self.hud.set_status("calibrating", "posture tracking suspended")
        elif self.breaks.in_break:
            self.hud.set_status("break", "Break in progress")
        elif camera_mode(self) == "preview":
            self.hud.set_status("preview", "Preview only · tracking paused")
        elif self._idle_stopped:
            self.hud.set_status("idle", "Tracking stopped while idle")
        elif state is State.GOOD:
            self.hud.set_live(dev, "good")
        elif state is State.DRIFTING:
            self.hud.set_live(dev, "drift")
        elif state is State.BAD:
            self.hud.set_live(dev, "hunched")
        elif state is State.AWAY:
            self.hud.set_status("away", "away")
        elif state is State.PAUSED:
            self.hud.set_status("paused", "paused")
        elif state is State.CAMERA_ERROR:
            self.hud.set_status("cam_error", "camera…")
        self._refresh_tray()

    def _handle_event(self, ev: str) -> None:
        if self.breaks.in_break and ev in (EVENT_ALERT, EVENT_RENAG, EVENT_RECOVERED):
            return
        if ev in (EVENT_ALERT, EVENT_RENAG):
            if ev == EVENT_ALERT:
                self.hud.show_feedback("Adjust posture")
            self._toast(
                "Sit tall" if ev == EVENT_ALERT else "Still hunched…",
                "Lengthen the back of your neck, chin gently back, "
                "shoulders down.",
            )
            if self.cfg.get("sound_on"):
                _chime()
        elif ev == EVENT_RECOVERED:
            self._toast("Back in line ✓", "Good posture restored.")
        elif ev == EVENT_CAM_ERROR:
            self._toast("Camera unavailable", "Check the privacy shutter / "
                              "other apps. Retrying every few seconds…")

    # ------------------------------------------------------------------
    def _on_pause_toggled(self, paused: bool) -> None:
        from unshrimp import diag

        self.cfg["tracking_paused"] = paused
        try:
            config_mod.save(self.cfg)
        except OSError as exc:
            diag.log(f"pause: could not save preference: {exc}")
        self.tray.set_paused_ui(paused)
        if paused:
            self._end_history_segment()
            self.breaks.pause()
            self.break_prompt.hide()
            self._restart_pending = False
            self.smoother.reset()
            self._good_streak = 0
            if self._cal is not None:  # abort any calibration in flight
                self._cal = None
                self.tray.show_continue(False)
                self.worker.preview_enabled = False
                self.preview_win.stop_preview()
                self.preview_win.set_instruction("", "")
                self.preview_win.hide()
            self.mascot.force_hide()
            self.machine.pause()
            self.hud.set_status("paused", "paused")
            self.tray.set_state("paused", "")
            # Release capture on the worker thread without blocking the UI.
            diag.log("pause: applying camera policy")
            self._restart_worker()
            if self._camera_preview is not None:
                self._camera_preview.refresh()
            if self.worker.isRunning() and camera_mode(self) == "off":
                self.hud.set_status("paused", "stopping camera")
                self.tray.set_state("paused", "stopping camera")
            elif camera_mode(self) == "preview":
                self._render(State.PAUSED, None)
        else:
            self.machine.resume(time.monotonic())
            self._idle_stopped = False  # manual resume overrides idle state
            diag.log("resume: restarting camera")
            self._restart_worker()

    def _on_hud_toggled(self, visible: bool) -> None:
        self.hud.setVisible(visible)
        self.tray.sync_hud_action(visible)
        self.cfg["hud"]["visible"] = visible
        config_mod.save(self.cfg)

    def _on_compact_toggled(self, compact: bool) -> None:
        self.hud.set_compact(compact)
        self.tray.sync_compact_action(compact)
        self.cfg["hud"]["compact"] = compact
        config_mod.save(self.cfg)

    def _on_cam_error(self) -> None:
        from unshrimp import diag

        if isinstance(self, QObject) and self.sender() is not None and self.sender() is not self.worker:
            return
        diag.log("camera: error")
        if self._cal is not None:
            self.preview_win.camera_unavailable(self.worker.camera_error)
        if self._camera_preview is not None:
            self._camera_preview.refresh()
        if camera_mode(self) == "tracking" and not self._restart_pending:
            self._end_history_segment()
            self.breaks.pause()
            self.break_prompt.hide()
            self.smoother.reset()
            self._good_streak = 0
            self.mascot.force_hide()
            events = self.machine.camera_failed()
            self._render(self.machine.state, None)
            for ev in events:
                self._handle_event(ev)

    def _on_cam_recovered(self) -> None:
        from unshrimp import diag

        diag.log("camera: recovered")
        if isinstance(self, QObject) and self.sender() is not None and self.sender() is not self.worker:
            return
        if camera_mode(self) == "tracking" and self.machine.state is State.CAMERA_ERROR:
            self.machine.camera_ok(time.monotonic())

    def _on_quit(self) -> None:
        from PySide6.QtWidgets import QApplication

        if not self._quitting and self._settings_dlg is not None:
            if not self._settings_dlg._finish_pending():
                return
        if self.shutdown():
            QApplication.instance().quit()
        else:
            QTimer.singleShot(100, self._on_quit)

    def _open_settings(self) -> None:
        from .settings import SettingsDialog

        main = self.main_window
        dlg = self._settings_dlg
        if dlg is None:
            dlg = SettingsDialog(self.cfg, self, parent=main.pages)
            dlg.setWindowFlags(Qt.Widget)
            dlg.setMinimumSize(0, 0)
            dlg.done_button.hide()
            self._settings_dlg = dlg
            dlg.calibrate_requested.connect(
                self.start_calibration
            )
            dlg.reset_baseline_requested.connect(self._reset_baseline)
            dlg.select_page(getattr(self, "_settings_page", "Tracking"))
            def settings_finished(_):
                self._settings_page = dlg.tabs.tabText(dlg.tabs.currentIndex())
                main.show_dashboard(dlg)
                self._settings_dlg = None
            dlg.finished.connect(settings_finished)
            dlg.finished.connect(dlg.deleteLater)
        main.show_settings(dlg)

    def restart_camera(self) -> None:
        """Public hook for Settings' camera picker."""
        self._restart_worker()

    def _open_settings_page(self, name: str) -> None:
        self._open_settings()
        self._settings_dlg.select_page(name)

    def _reset_baseline(self) -> None:
        candidate = dict(self.cfg, baseline=None)
        try:
            config_mod.save(candidate)
        except OSError as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self.main_window, "Calibration was not reset",
                                f"Your previous calibration is still active.\n\n{exc}")
            return
        was_paused = self.machine.state is State.PAUSED
        self._end_history_segment()
        self.breaks.pause()
        self.break_prompt.hide()
        self.cfg["baseline"] = None
        self.baseline = None
        self.machine = PostureStateMachine(self.machine.thr)  # back to UNCALIBRATED
        if was_paused:
            self.machine.pause()
            self._render(State.PAUSED, None)
        else:
            self._sync_uncalibrated_ui()
        self._toast("Baseline reset", "Calibrate when you're ready.")

    def _restart_worker(self) -> None:
        self._display_deviation = None
        if self._cal is not None:
            self.preview_win.camera_unavailable("Reconnecting to the selected camera.")
        self._end_history_segment()
        self.breaks.pause()
        self.break_prompt.hide()
        self._restart_pending = False
        self.worker.stop()
        mode = camera_mode(self)
        if mode == "off":
            return
        if self.worker.isRunning():
            self._restart_pending = True
            return
        self.smoother.reset()
        self._good_streak = 0
        self.worker = VisionWorker(
            self.models_dir, self.cfg["camera_index"], self.cfg["fps"]
        )
        self.worker.frame.connect(self._on_frame)
        self.worker.cam_error.connect(self._on_cam_error)
        self.worker.cam_recovered.connect(self._on_cam_recovered)
        self.worker.preview.connect(self._on_calibration_preview)
        if self._camera_preview is not None:
            self.worker.preview.connect(self._camera_preview.update_frame)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.preview_enabled = self._cal is not None or (
            self._camera_preview is not None and self._camera_preview.isVisible())
        self.worker.inference_enabled = mode != "preview"
        if mode == "calibration":
            self.worker.inference_interval = 0.5
        self.worker.start()

    def _on_system_suspend(self) -> None:
        from unshrimp import diag

        diag.log("power: suspend — stopping camera")
        self._suspended = True
        self._restart_pending = False
        self._end_history_segment()
        self.breaks.pause()
        self.break_prompt.hide()
        self.smoother.reset()
        self._good_streak = 0
        self.mascot.force_hide()
        self.worker.stop()
        if self._camera_preview is not None:
            self._camera_preview.refresh()
        if self._cal is not None:
            self.preview_win.camera_unavailable("The camera is off while the computer sleeps.", retry=False)

    def _on_system_resume(self) -> None:
        from unshrimp import diag

        diag.log("power: resume — restoring camera policy")
        self._suspended = False
        if not self._quitting:
            self._restart_worker()

    def _on_worker_finished(self) -> None:
        if self._restart_pending:
            self._restart_worker()
        elif not self._quitting and self._cal is None and self.machine.state is State.PAUSED:
            self._render(State.PAUSED, None)

    def _sync_uncalibrated_ui(self) -> None:
        self.hud.set_status("uncalibrated", "double-click = calibrate")
        self.tray.set_state("uncalibrated", "")
