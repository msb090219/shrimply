"""Modeless preferences with automatic saving and isolated samples."""
from __future__ import annotations

import sys
import copy

import cv2
from PySide6.QtCore import Qt, QPoint, Signal, QSignalBlocker, QTimer, QEvent, QUrl
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QFrame,
    QGraphicsOpacityEffect,
    QPlainTextEdit,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QSizePolicy,
)

from . import theme
from .sections import section
from .status import camera_status, calibration_status
from .appearance import ShrimpPreview
from .hud import Hud
from .tray import shrimp_icon
from .icons import refresh_icon
from PySide6.QtGui import QGuiApplication, QDesktopServices, QPainter


def available_cameras(max_index: int = 4, skip: int | None = None) -> list[int]:
    """Probe camera indices — without ever opening the live in-use device
    (`skip`), which on Windows disturbs the running capture."""
    out = []
    for i in range(max_index):
        if i == skip:
            out.append(i)  # we're streaming from it; it demonstrably exists
            continue
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            out.append(i)
        cap.release()
    return out or [0]


class _SettingsTabs(QTabWidget):
    def paintEvent(self, event):
        super().paintEvent(event)
        scroll = self.currentWidget()
        if scroll is None:
            return
        card = scroll.widget().layout().itemAt(0).widget()
        left = card.mapTo(self, QPoint(0, 0)).x()
        right = card.mapTo(self, QPoint(card.width(), 0)).x()
        painter = QPainter(self)
        painter.setPen(self.palette().mid().color())
        y = self.tabBar().geometry().bottom()
        painter.drawLine(left, y, right, y)


class SettingsDialog(QDialog):
    calibrate_requested = Signal()
    reset_baseline_requested = Signal()

    def __init__(self, cfg: dict, app, parent=None):
        super().__init__(parent)
        self._live_cfg = cfg
        self._ready = False
        self._original = copy.deepcopy(cfg)
        self.cfg = copy.deepcopy(cfg)
        self._reset_hud_position = False
        self._startup_original = None
        self.app = app  # live-apply hooks: save_cfg/apply_thresholds/…
        self._cam_changed = False
        self._theme_muted_labels = []
        self._rescan_timer = QTimer(self)
        self._rescan_timer.setSingleShot(True)
        self._rescan_timer.timeout.connect(self._finish_rescan)
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._finish_retry_feedback)
        self.setWindowTitle("Settings")
        self.resize(760, 640)
        theme.apply_desktop_theme(self)
        tabs = self.tabs = self._general_tab()

        done = self.done_button = QPushButton("Done")
        done.setProperty("primary", True)
        done.clicked.connect(self.accept)
        btns = QHBoxLayout()
        note = self.save_status = QLabel("Changes save automatically")
        note.setWordWrap(True)
        note.setAccessibleName("Save status")
        btns.addWidget(note, 1)
        btns.addWidget(done)
        btns.setContentsMargins(0, 0, 16, 0)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 0, 0, 16)
        lay.setSpacing(12)
        lay.addWidget(tabs)
        lay.addLayout(btns)
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(1000)
        self.status_timer.timeout.connect(self.refresh_status)
        self.refresh_status()
        self._refresh_samples()
        self._ready = True
        for slider in (self.sens, self.mascot_op, self.hud_op):
            slider.sliderReleased.connect(self._commit)
            slider.installEventFilter(self)
        self._update_dependencies()
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            if button not in (self.reminder_sample.take_button, self.reminder_sample.later_button):
                button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        for control in self.findChildren(QSpinBox):
            control.setFixedWidth(112)
            control.setKeyboardTracking(False)
        screen = self.screen()
        if screen is not None:
            area = screen.availableGeometry()
            self.resize(min(760, max(620, area.width() - 48)),
                        min(640, max(500, area.height() - 64)))

    # ------------------------------------------------------------------
    def _general_tab(self) -> QWidget:
        c = self.cfg
        tabs = _SettingsTabs()
        tabs.setObjectName("settingsTabs")
        tabs.tabBar().setObjectName("settingsTabBar")
        tabs.tabBar().setExpanding(True)
        tabs.currentChanged.connect(tabs.update)
        columns = {}
        for name in ("Tracking", "Alerts and breaks", "Appearance", "General"):
            inner = QWidget()
            layout = QVBoxLayout(inner)
            layout.setContentsMargins(0, 16, 16, 16)
            layout.setSpacing(16)
            columns[name] = layout
            scroll = QScrollArea()
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidget(inner)
            tabs.addTab(scroll, name)
        col = columns["Appearance"]

        card, form = section("Application theme")
        self.theme_mode = QComboBox()
        self.theme_mode.addItem("Use device setting", "system")
        self.theme_mode.addItem("Dark", "dark")
        self.theme_mode.addItem("Light", "light")
        self.theme_mode.setFixedWidth(168)
        selected_theme = self.theme_mode.findData(c.get("theme_mode", "dark"))
        self.theme_mode.setCurrentIndex(selected_theme if selected_theme >= 0 else self.theme_mode.findData("dark"))
        self.theme_mode.currentIndexChanged.connect(self._theme_changed)
        form.addRow("Colour mode", self.theme_mode)
        theme_note = QLabel("Use your device setting, or choose a theme for all Shrimply windows and the posture meter.")
        theme_note.setWordWrap(True)
        form.addRow(theme_note)
        col.addWidget(card)

        # --- Mascot -----------------------------------------------------
        card, form = section("Floating cue", theme.app_icon())
        self.shrimp_preview = ShrimpPreview()
        self.mascot_on = QCheckBox("Show a floating cue when I slouch")
        self.mascot_on.setChecked(bool(c.get("mascot_enabled", True)))
        self.mascot_on.toggled.connect(self._mascot_changed)
        form.addRow(self.mascot_on)

        self.mascot_style = QComboBox()
        self.mascot_style.addItem("Shrimp", "shrimp")
        self.mascot_style.addItem("Text · Don't get shrimped.", "text")
        self.mascot_style.setMaximumWidth(220)
        self.mascot_style.setCurrentIndex(max(0, self.mascot_style.findData(c.get("mascot_style", "shrimp"))))
        self.mascot_style.currentIndexChanged.connect(self._mascot_changed)
        form.addRow("Style", self.mascot_style)

        self.mascot_size = QComboBox()
        for label, key in (("Small", "s"), ("Medium", "m"), ("Large", "l")):
            self.mascot_size.addItem(label, key)
        self.mascot_size.setFixedWidth(112)
        self.mascot_size.setCurrentIndex(
            {"s": 0, "m": 1, "l": 2}.get(str(c.get("mascot_size", "m")), 1)
        )
        self.mascot_size.currentIndexChanged.connect(self._mascot_changed)
        form.addRow("Size", self.mascot_size)

        self.mascot_op = QSlider(Qt.Horizontal)
        self.mascot_op.setAccessibleName("Floating cue transparency")
        self.mascot_op.setRange(0, 70)
        self.mascot_op.setMaximumWidth(220)
        self.mascot_op.setValue(round((1 - float(c.get("mascot_opacity", 0.87))) * 100))
        self.mascot_op.valueChanged.connect(self._mascot_changed)
        self.opacity_label = QLabel(f"{self.mascot_op.value()}%")
        self.opacity_label.setFixedWidth(36)
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(8)
        opacity_row.addWidget(self.mascot_op)
        opacity_row.addWidget(self.opacity_label)
        self.mascot_op.setToolTip("0% is opaque. This changes appearance, not tracking sensitivity.")
        form.addRow("Transparency", opacity_row)

        self.mascot_position = QComboBox()
        self.mascot_position.setMaximumWidth(220)
        for label, key in (("Top left", "top_left"), ("Top centre", "top_center"),
                           ("Top right", "top_right"), ("Centre", "middle"),
                           ("Bottom left", "left"), ("Bottom centre", "center"),
                           ("Bottom right", "right")):
            self.mascot_position.addItem(label, key)
        self.mascot_position.setCurrentIndex(max(0, self.mascot_position.findData(c.get("mascot_position", "center"))))
        self.mascot_position.currentIndexChanged.connect(self._mascot_changed)
        form.addRow("Position", self.mascot_position)
        self.mascot_screen = QComboBox(self)
        self.mascot_screen.setMaximumWidth(260)
        self.mascot_screen.addItem("Default display", "")
        for index, screen in enumerate(QGuiApplication.screens(), 1):
            self.mascot_screen.addItem(f"Display {index}" + (" (main)" if screen is QGuiApplication.primaryScreen() else ""), screen.name())
        self.mascot_screen.addItem("All displays", "*")
        saved_screen = c.get("mascot_screen", "")
        if self.mascot_screen.findData(saved_screen) < 0:
            self.mascot_screen.addItem("Unavailable display (uses default)", saved_screen)
        self.mascot_screen.setCurrentIndex(self.mascot_screen.findData(saved_screen))
        self.mascot_screen.currentIndexChanged.connect(self._mascot_changed)
        form.addRow("Display", self.mascot_screen)
        self.mascot_entrance = QComboBox()
        for label, key in (("Fade and rise", "rise"), ("Fade only", "fade"),
                           ("Appear instantly", "instant")):
            self.mascot_entrance.addItem(label, key)
        self.mascot_entrance.setMaximumWidth(220)
        entrance = self.mascot_entrance.findData(c.get("mascot_entrance", "rise"))
        self.mascot_entrance.setCurrentIndex(max(0, entrance))
        self.mascot_entrance.currentIndexChanged.connect(self._mascot_changed)
        form.addRow("Entrance", self.mascot_entrance)
        self.mascot_bad_hold = QSpinBox()
        self.mascot_bad_hold.setRange(0, 15)
        self.mascot_bad_hold.setSuffix(" s")
        self.mascot_bad_hold.setValue(int(c.get("mascot_bad_hold_s", 2)))
        self.mascot_bad_hold.setToolTip("How long posture must stay Bad before the floating cue appears. 0 means immediately.")
        self.mascot_bad_hold.valueChanged.connect(self._mascot_changed)
        form.addRow("Appear after bad", self.mascot_bad_hold)
        self.mascot_recovery_hold = QSpinBox()
        self.mascot_recovery_hold.setRange(0, 15)
        self.mascot_recovery_hold.setSuffix(" s")
        self.mascot_recovery_hold.setValue(int(c.get("mascot_recovery_hold_s", 3)))
        self.mascot_recovery_hold.setToolTip("How long posture must stay Good before the floating cue fades. 0 means immediately.")
        self.mascot_recovery_hold.valueChanged.connect(self._mascot_changed)
        form.addRow("Fade after good", self.mascot_recovery_hold)
        self.mascot_bob = QCheckBox("Gentle bobbing")
        self.mascot_bob.setChecked(bool(c.get("mascot_bob", True)))
        self.mascot_bob.toggled.connect(self._mascot_changed)
        form.addRow(self.mascot_bob)
        self.reduce_motion = QCheckBox("Reduce motion")
        self.reduce_motion.setChecked(bool(c.get("reduce_motion", False)))
        self.reduce_motion.toggled.connect(self._motion_changed)
        form.addRow(self.reduce_motion)
        motion_note = QLabel("Removes cue movement and reduces calibration animation. Your entrance and bobbing choices stay saved.")
        motion_note.setWordWrap(True)
        form.addRow(motion_note)
        form.addRow(self._preview_area(self.shrimp_preview, "Preview · after entrance · no camera needed"))
        col.addWidget(card)

        card, form = section("Posture meter", shrimp_icon(theme.GOOD))
        self.hud_preview = Hud()
        self.hud_preview.setWindowFlags(Qt.Widget)
        self.hud_preview.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hud_preview_opacity = QGraphicsOpacityEffect(self.hud_preview)
        self.hud_preview.setGraphicsEffect(self.hud_preview_opacity)
        for button in (self.hud_preview.pause_button, self.hud_preview.menu_button):
            button.setEnabled(False)
            button.setFocusPolicy(Qt.NoFocus)
        self.hud_preview.set_live(1.1, "")
        self.hud_visible = QCheckBox("Show the posture meter")
        self.hud_visible.setChecked(c["hud"].get("visible", True))
        self.hud_visible.toggled.connect(self._hud_changed)
        form.addRow(self.hud_visible)
        self.hud_orientation = QComboBox()
        self.hud_orientation.setFixedWidth(144)
        self.hud_orientation.addItem("Horizontal", "horizontal")
        self.hud_orientation.addItem("Vertical", "vertical")
        self.hud_orientation.setCurrentIndex(max(0, self.hud_orientation.findData(c["hud"].get("orientation", "horizontal"))))
        self.hud_orientation.currentIndexChanged.connect(self._hud_changed)
        form.addRow("Orientation", self.hud_orientation)
        self.hud_size = QComboBox()
        self.hud_size.setFixedWidth(112)
        for label, key in (("Small", "s"), ("Medium", "m"), ("Large", "l")):
            self.hud_size.addItem(label, key)
        self.hud_size.setCurrentIndex(max(0, self.hud_size.findData(c["hud"].get("size", "m"))))
        self.hud_size.currentIndexChanged.connect(self._hud_changed)
        form.addRow("Size", self.hud_size)
        self.hud_op = QSlider(Qt.Horizontal)
        self.hud_op.setAccessibleName("Posture meter transparency")
        self.hud_op.setRange(0, 70)
        self.hud_op.setMaximumWidth(220)
        self.hud_op.setValue(round((1 - float(c["hud"].get("opacity", 1.0))) * 100))
        self.hud_op.valueChanged.connect(self._hud_changed)
        self.hud_op.setToolTip("0% is opaque. This changes the meter and its feedback text together.")
        self.hud_op_label = QLabel(f"{self.hud_op.value()}%")
        self.hud_op_label.setFixedWidth(36)
        hud_op_row = QHBoxLayout()
        hud_op_row.setSpacing(8)
        hud_op_row.addWidget(self.hud_op)
        hud_op_row.addWidget(self.hud_op_label)
        form.addRow("Transparency", hud_op_row)
        self.hud_compact = QCheckBox("Hide brief adjustment cue")
        self.hud_compact.setToolTip("Hides the short adjustment caption after a sustained alert. Camera and calibration messages remain visible.")
        self.hud_compact.setChecked(c["hud"].get("compact", False))
        self.hud_compact.toggled.connect(self._hud_changed)
        form.addRow(self.hud_compact)
        reset_position = self.reset_position_button = QPushButton("Reset meter position")
        reset_position.setIcon(refresh_icon(self.palette().text().color()))
        reset_position.clicked.connect(self._reset_meter_position)
        reset_row = QHBoxLayout()
        reset_row.addWidget(reset_position)
        reset_row.addStretch()
        form.addRow(reset_row)
        form.addRow(self._preview_area(self.hud_preview, "Preview · sample meter"))
        col.addWidget(card)
        defaults = self.defaults_button = QPushButton("Restore appearance defaults")
        defaults.setIcon(refresh_icon(self.palette().text().color()))
        defaults.clicked.connect(self._restore_appearance)
        col.addWidget(defaults, 0, Qt.AlignLeft)

        # --- Detection ----------------------------------------------------
        col = columns["Tracking"]
        card, form = section("Detection")
        sens_row = QHBoxLayout()
        self.sens = QSlider(Qt.Horizontal)
        self.sens.setAccessibleName("Posture sensitivity")
        self.sens.setRange(5, 30)
        self.sens.setMaximumWidth(220)
        self.sens.setValue(int(c["sensitivity"] * 10))
        self.sens_lbl = QLabel(f"{c['sensitivity']:.1f}×")
        self.sens_lbl.setMinimumWidth(34)
        self.sens.valueChanged.connect(self._sensitivity_changed)
        sens_row.addWidget(self.sens, 1)
        sens_row.addWidget(self.sens_lbl)
        form.addRow("Sensitivity (higher = stricter)", sens_row)

        self.grace = QSpinBox()
        self.grace.setRange(15, 300)
        self.grace.setSuffix(" s")
        self.grace.setValue(int(c["grace_s"]))
        self.grace.valueChanged.connect(self._thresholds_changed)

        self.renag = QSpinBox()
        self.renag.setRange(60, 900)
        self.renag.setSuffix(" s")
        self.renag.setValue(int(c["renag_s"]))
        self.renag.valueChanged.connect(self._thresholds_changed)

        self.away = QSpinBox()
        self.away.setRange(5, 60)
        self.away.setSuffix(" s")
        self.away.setValue(int(c["away_s"]))
        self.away.valueChanged.connect(self._thresholds_changed)
        self.away.setToolTip("Mark you away after tracking is lost for this long.")
        detection_card = card

        # --- Alerts -------------------------------------------------------
        col = columns["Alerts and breaks"]
        card, form = section("Posture alerts")
        self.toasts = QCheckBox("System notifications")
        self.toasts.setToolTip("Allow system notifications for posture, calibration and camera status. Break cards have their own switch below.")
        self.toasts.setChecked(bool(c.get("toasts_enabled", True)))
        self.toasts.toggled.connect(self._simple_save)
        form.addRow(self.toasts)
        self.sound = QCheckBox("Chime with posture alerts")
        self.sound.setChecked(bool(c["sound_on"]))
        self.sound.toggled.connect(self._simple_save)
        test_sound = QPushButton("Test sound")
        test_sound.clicked.connect(self._test_sound)
        sound_row = QHBoxLayout()
        sound_row.addWidget(self.sound)
        sound_row.addWidget(test_sound)
        sound_row.addStretch()
        form.addRow(sound_row)
        form.addRow("Posture alert delay", self.grace)
        form.addRow("Repeat alert after", self.renag)
        note = QLabel("System notifications include camera and calibration notices. Break cards have their own switch below.")
        note.setWordWrap(True)
        form.addRow(note)
        test_notification = QPushButton("Send test notification")
        test_notification.clicked.connect(self._test_notification)
        form.addRow(test_notification)
        self.test_status = QLabel()
        self.test_status.setWordWrap(True)
        self.test_status.hide()
        form.addRow(self.test_status)
        col.addWidget(card)

        # --- Stretch breaks + editor --------------------------------------
        card, form = section("Break reminders")
        rem_row = QHBoxLayout()
        self.reminder = QCheckBox("Enable break reminders")
        self.reminder.setChecked(bool(c["reminder_enabled"]))
        self.reminder.toggled.connect(self._simple_save)
        self.reminder_min = QSpinBox()
        self.reminder_min.setRange(5, 180)
        self.reminder_min.setSuffix(" min")
        self.reminder_min.setValue(int(c["reminder_interval_min"]))
        self.reminder_min.valueChanged.connect(self._simple_save)
        form.addRow(self.reminder)
        rem_row.addWidget(self.reminder_min)
        rem_row.addWidget(QLabel("of detected sitting"))
        rem_row.addStretch(1)
        form.addRow("Remind after", rem_row)
        self.break_min = QSpinBox()
        self.break_min.setRange(1, 30)
        self.break_min.setSuffix(" min")
        self.break_min.setValue(int(c["reminder_break_min"]))
        self.break_min.valueChanged.connect(self._simple_save)
        form.addRow("Break length", self.break_min)
        explanation = QLabel("The reminder counts detected sitting; time away, pauses and calibration do not count. Breaks use a countdown while camera tracking continues.")
        explanation.setWordWrap(True)
        form.addRow(explanation)
        restart_note = QLabel("The sitting timer starts fresh when Shrimply restarts.")
        restart_note.setWordWrap(True)
        form.addRow(restart_note)
        col.addWidget(card)

        card, form = section("Break suggestions")
        form.addRow(self._exercise_editor())
        col.addWidget(card)

        from .break_prompt import BreakPrompt
        example_card, example_form = section("Reminder preview")
        preview_note = QLabel("Preview uses your first suggestion. Live reminders rotate through the list; these controls do not change your timer.")
        preview_note.setWordWrap(True)
        example_form.addRow(preview_note)
        preview_stack = QWidget()
        preview_layout = QVBoxLayout(preview_stack)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)
        self.reminder_meter_preview = Hud()
        self.reminder_meter_preview.setWindowFlags(Qt.Widget)
        self.reminder_meter_preview.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.reminder_meter_preview.set_orientation(c["hud"].get("orientation", "horizontal"))
        self.reminder_meter_preview.set_size(c["hud"].get("size", "m"))
        self.reminder_meter_preview.set_live(.5, "")
        self.reminder_meter_preview.set_break_prompt_visible(True)
        preview_layout.addWidget(self.reminder_meter_preview, 0, Qt.AlignLeft)
        self.reminder_sample = BreakPrompt(example=True, break_minutes=c["reminder_break_min"])
        self.reminder_sample.setWindowFlags(Qt.Widget)
        self.reminder_sample.setFixedWidth(
            (max(340, self.reminder_meter_preview.bar.width())
             if c["hud"].get("orientation") == "vertical" else self.reminder_meter_preview.bar.width())
            if c["hud"].get("visible", True) else 340)
        preview_layout.addWidget(self.reminder_sample, 0, Qt.AlignLeft)
        self.preview_status = QLabel()
        self.preview_status.setWordWrap(True)
        preview_layout.addWidget(self.preview_status)
        self.reminder_sample.example_action.connect(self.preview_status.setText)
        example_form.addRow(preview_stack)
        col.addWidget(example_card)

        # --- Camera -------------------------------------------------------
        col = columns["Tracking"]
        card, form = section("Camera")
        cam_row = QHBoxLayout()
        self.cam = QComboBox()
        self.cam.setAccessibleName("Camera device")
        self.cam.setMinimumWidth(160)
        self.cam.setMaximumWidth(260)
        cams = [int(c["camera_index"])]  # probe other devices only on explicit Rescan
        self.cam.addItems([f"Camera {i}" for i in cams])
        try:
            self.cam.setCurrentIndex(cams.index(int(c["camera_index"])))
        except ValueError:
            pass
        self.cam.currentIndexChanged.connect(lambda _: self._camera_changed())
        rescan = self.rescan_button = QPushButton("Rescan")
        rescan.setMinimumWidth(110)
        rescan.clicked.connect(self._rescan)
        cam_row.addWidget(self.cam, 1)
        cam_row.addWidget(rescan)
        cam_row.addStretch()
        form.addRow(cam_row)
        self.camera_status_label = QLabel()
        self.camera_status_label.setWordWrap(True)
        form.addRow(self.camera_status_label)
        preview_row = QHBoxLayout()
        preview = QPushButton("Camera preview…")
        preview.clicked.connect(lambda: self._task(self.app.open_camera_preview))
        preview_row.addWidget(preview)
        self.camera_retry = QPushButton("Retry camera")
        self.camera_retry.setFixedWidth(self.camera_retry.sizeHint().width())
        self.camera_retry.clicked.connect(self._retry_camera)
        preview_row.addWidget(self.camera_retry)
        preview_row.addStretch()
        form.addRow(preview_row)
        col.addWidget(card)

        # --- Baseline + startup --------------------------------------------
        card, form = section("Calibration")
        self.baseline_status_label = QLabel()
        self.baseline_status_label.setWordWrap(True)
        form.addRow(self.baseline_status_label)
        cal_row = QHBoxLayout()
        cal_btn = self.calibrate_button = QPushButton("Calibrate now…")
        cal_btn.clicked.connect(self._calibrate)
        reset_btn = self.reset_button = QPushButton("Reset baseline…")
        reset_btn.clicked.connect(self._confirm_reset)
        cal_row.addWidget(cal_btn)
        cal_row.addStretch(1)
        form.addRow(cal_row)
        note = QLabel("Keep your face and shoulders visible. Recalibrate after moving your camera or chair.")
        note.setWordWrap(True)
        form.addRow(note)
        form.addRow(reset_btn)
        col.addWidget(card)
        col.addWidget(detection_card)
        advanced = QCheckBox("Advanced tracking")
        col.addWidget(advanced)
        advanced_box = QWidget()
        advanced_layout = QVBoxLayout(advanced_box)
        advanced_layout.addWidget(QLabel("Time without tracking before marking you away"))
        advanced_layout.addWidget(self.away, 0, Qt.AlignLeft)
        advanced_box.hide()
        advanced.toggled.connect(advanced_box.setVisible)
        col.addWidget(advanced_box)
        col = columns["General"]
        card, form = section("Startup")

        import shrimply.autostart as autostart

        if sys.platform == "win32":
            self.autostart = QCheckBox("Start Shrimply at login")
            self.autostart.setToolTip("Start quietly in the system tray; keep the main window hidden.")
            try:
                self.autostart.setChecked(autostart.is_enabled())
            except OSError:
                pass
            self._startup_original = self.autostart.isChecked()
            self.autostart.toggled.connect(self._commit)
            form.addRow(self.autostart)
            note = QLabel("Starts quietly in the system tray.")
            note.setWordWrap(True)
            form.addRow(note)
        else:
            self.autostart = None
        col.addWidget(card)

        note = QLabel("Closing the main window leaves Shrimply in the system tray. Use Quit in the tray menu to exit completely.")
        note.setWordWrap(True)
        form.addRow(note)
        from shrimply import __version__
        card, form = section("About")
        form.addRow(QLabel(f"Shrimply {__version__}"))
        about = QPushButton("Open About…")
        about.clicked.connect(lambda: self._task(self.app._show_about))
        form.addRow(about)
        col.addWidget(card)
        card, form = section("Data and support")
        note = QLabel("Camera processing stays on this device. Settings, posture history and diagnostic logs are stored locally.")
        note.setWordWrap(True)
        form.addRow(note)
        folder = QPushButton("Open data folder")
        folder.clicked.connect(self._open_data_folder)
        form.addRow(folder)
        col.addWidget(card)
        for column in columns.values():
            column.addStretch(1)
        return tabs

    def _preview_area(self, sample, caption):
        area = QWidget()
        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)
        label = QLabel(caption)
        label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        self._theme_muted_labels.append(label)
        layout.addWidget(label)
        layout.addWidget(sample, 0, Qt.AlignLeft)
        return area

    # ------------------------------------------------------------------
    def refresh_status(self):
        state, detail = camera_status(self.app)
        self.camera_status_label.setText(f"{state.capitalize()} · {detail}")
        if state in ("running", "preview") and self._retry_timer.isActive():
            self._retry_timer.stop()
            self._finish_retry_feedback()
        self.camera_retry.setVisible(state in ("reconnecting", "off")
                                    and not self.app._suspended and not self.app._idle_stopped)
        self.baseline_status_label.setText(calibration_status(self.app))
        self.calibrate_button.setEnabled(self.app._cal is None and not self.app._suspended)
        self.reset_button.setEnabled(self.app.baseline is not None and self.app._cal is None)

    def apply_theme(self):
        for label in self._theme_muted_labels:
            label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        self.hud_preview.apply_theme()
        for button in (self.reset_position_button, self.defaults_button):
            button.setIcon(refresh_icon(self.palette().text().color()))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_status()
        self.status_timer.start()

    def hideEvent(self, event):
        self.status_timer.stop()
        super().hideEvent(event)

    def _exercise_editor(self) -> QWidget:
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 6, 0, 0)

        self.ex_list = QListWidget()
        self.ex_list.setMinimumWidth(160)
        self.ex_list.setFixedHeight(166)
        self.ex_list.setAccessibleName("Break suggestions")
        for ex in self.cfg.get("exercises", []):
            QListWidgetItem(ex.get("name", "?"), self.ex_list)
        self.ex_list.currentRowChanged.connect(self._exercise_selected)

        edit_col = QWidget()
        edit = QVBoxLayout(edit_col)
        edit.setContentsMargins(0, 0, 0, 0)
        self.ex_name = QLineEdit()
        name_label = QLabel("Name")
        name_label.setBuddy(self.ex_name)
        edit.addWidget(name_label)
        self.ex_name.setPlaceholderText("e.g. Short walk")
        self.ex_how = QPlainTextEdit()
        self.ex_how.setFixedHeight(72)
        self.ex_how.setPlaceholderText("Describe the suggestion")
        self.ex_how.setTabChangesFocus(True)
        edit.addWidget(self.ex_name)
        how_label = QLabel("Instructions")
        how_label.setBuddy(self.ex_how)
        edit.addWidget(how_label)
        edit.addWidget(self.ex_how, 1)
        btns = QGridLayout()
        add = QPushButton("Add")
        upd = self.ex_update = QPushButton("Update")
        rem = self.ex_remove = QPushButton("Remove")
        add.clicked.connect(self._exercise_add)
        upd.clicked.connect(self._exercise_update)
        rem.clicked.connect(self._exercise_remove)
        btns.addWidget(add, 0, 0)
        btns.addWidget(upd, 0, 1)
        btns.addWidget(rem, 1, 1, Qt.AlignRight)
        edit.addLayout(btns)

        lay.addWidget(self.ex_list, 1)
        lay.addWidget(edit_col, 2)
        if self.ex_list.count():
            self.ex_list.setCurrentRow(0)
        else:
            self._exercise_selected(-1)
        return box

    def _exercise_selected(self, row: int) -> None:
        exs = self.cfg.get("exercises", [])
        valid = 0 <= row < len(exs)
        self.ex_update.setEnabled(valid)
        self.ex_remove.setEnabled(valid)
        if valid:
            self.ex_name.setText(exs[row].get("name", ""))
            self.ex_how.setPlainText(exs[row].get("how", ""))
        else:
            self.ex_name.clear()
            self.ex_how.clear()

    def _exercise_sync(self, select: int) -> None:
        self._commit()
        self.ex_list.clear()
        for ex in self.cfg.get("exercises", []):
            QListWidgetItem(ex.get("name", "?"), self.ex_list)
        if 0 <= select < self.ex_list.count():
            self.ex_list.setCurrentRow(select)
        self._refresh_reminder_preview()

    def _refresh_reminder_preview(self):
        exs = self.cfg.get("exercises") or []
        if exs:
            ex = exs[0]
            suggestion = f"{ex.get('name', 'Stretch')} — {ex.get('how', '')}"[:500]
        else:
            suggestion = "Stand up for a short walk or a comfortable stretch."
        self.reminder_sample.set_suggestion(suggestion)

    def _exercise_add(self) -> None:
        name = self.ex_name.text().strip()
        if not name:
            return
        self.cfg.setdefault("exercises", []).append(
            {"name": name, "how": self.ex_how.toPlainText().strip()}
        )
        self._exercise_sync(len(self.cfg["exercises"]) - 1)

    def _exercise_update(self) -> None:
        row = self.ex_list.currentRow()
        exs = self.cfg.get("exercises", [])
        if 0 <= row < len(exs) and self.ex_name.text().strip():
            exs[row] = {
                "name": self.ex_name.text().strip(),
                "how": self.ex_how.toPlainText().strip(),
            }
            self._exercise_sync(row)

    def _exercise_remove(self) -> None:
        row = self.ex_list.currentRow()
        exs = self.cfg.get("exercises", [])
        if 0 <= row < len(exs):
            exs.pop(row)
            self._exercise_sync(max(0, row - 1))

    # ------------------------------------------------------------------
    # live-apply handlers
    def _motion_changed(self, enabled):
        self.cfg["reduce_motion"] = enabled
        self._update_dependencies()
        self._refresh_samples()
        self._commit()

    def _theme_changed(self, *_):
        self.cfg["theme_mode"] = self.theme_mode.currentData()
        self._commit()

    def _mascot_changed(self, *_):
        self.cfg["mascot_enabled"] = self.mascot_on.isChecked()
        self.cfg["mascot_style"] = self.mascot_style.currentData()
        self.cfg["mascot_size"] = self.mascot_size.currentData()
        self.cfg["mascot_opacity"] = 1 - self.mascot_op.value() / 100
        self.cfg["mascot_bob"] = self.mascot_bob.isChecked()
        self.cfg["mascot_entrance"] = self.mascot_entrance.currentData()
        self.cfg["mascot_bad_hold_s"] = self.mascot_bad_hold.value()
        self.cfg["mascot_recovery_hold_s"] = self.mascot_recovery_hold.value()
        self.cfg["mascot_position"] = self.mascot_position.currentData()
        self.cfg["mascot_screen"] = self.mascot_screen.currentData()
        self.opacity_label.setText(f"{self.mascot_op.value()}%")
        self._refresh_samples()
        if not self.mascot_op.isSliderDown():
            self._commit()

    def _hud_changed(self, *_):
        self.cfg["hud"].update(visible=self.hud_visible.isChecked(),
                               compact=self.hud_compact.isChecked(), size=self.hud_size.currentData(),
                               orientation=self.hud_orientation.currentData(),
                               opacity=1 - self.hud_op.value() / 100)
        self.hud_op_label.setText(f"{self.hud_op.value()}%")
        self._refresh_samples()
        if not self.hud_op.isSliderDown():
            self._commit()

    def _refresh_samples(self):
        self.shrimp_preview.configure(self.cfg)
        self.hud_preview.set_orientation(self.cfg["hud"].get("orientation", "horizontal"))
        self.hud_preview.set_size(self.cfg["hud"].get("size", "m"))
        self.hud_preview.set_compact(self.cfg["hud"].get("compact", False))
        self.hud_preview.setVisible(self.cfg["hud"].get("visible", True))
        self.hud_preview_opacity.setOpacity(self.cfg["hud"].get("opacity", 1.0))
        self.reminder_meter_preview.set_orientation(self.cfg["hud"].get("orientation", "horizontal"))
        self.reminder_meter_preview.set_size(self.cfg["hud"].get("size", "m"))
        self.reminder_meter_preview.setVisible(self.cfg["hud"].get("visible", True))
        self.reminder_sample.setFixedWidth(
            (max(340, self.reminder_meter_preview.bar.width())
             if self.cfg["hud"].get("orientation") == "vertical" else self.reminder_meter_preview.bar.width())
            if self.cfg["hud"].get("visible", True) else 340)
        self._refresh_reminder_preview()

    def _reset_meter_position(self):
        self._reset_hud_position = True
        self.cfg["hud"].update(x=None, y=None)
        if self._ready and self._commit():
            self.save_status.setText("Meter position reset")

    def _restore_appearance(self):
        self._ready = False
        self.theme_mode.setCurrentIndex(self.theme_mode.findData("dark"))
        self.mascot_on.setChecked(True)
        self.mascot_style.setCurrentIndex(self.mascot_style.findData("shrimp"))
        self.mascot_size.setCurrentIndex(1)
        self.mascot_op.setValue(13)
        self.mascot_position.setCurrentIndex(self.mascot_position.findData("center"))
        self.mascot_screen.setCurrentIndex(0)
        self.mascot_bob.setChecked(True)
        self.mascot_entrance.setCurrentIndex(self.mascot_entrance.findData("rise"))
        self.mascot_bad_hold.setValue(2)
        self.mascot_recovery_hold.setValue(3)
        self.reduce_motion.setChecked(False)
        self.hud_visible.setChecked(True)
        self.hud_orientation.setCurrentIndex(self.hud_orientation.findData("horizontal"))
        self.hud_size.setCurrentIndex(1)
        self.hud_op.setValue(0)
        self.hud_compact.setChecked(False)
        self._reset_meter_position()
        self._mascot_changed()
        self._hud_changed()
        self._ready = True
        if self._commit():
            self.save_status.setText("Appearance defaults restored")

    def _sensitivity_changed(self, v: int):
        self.cfg["sensitivity"] = v / 10
        self.sens_lbl.setText(f"{v / 10:.1f}×")
        if not self.sens.isSliderDown():
            self._commit()

    def _thresholds_changed(self, *_):
        self.cfg["grace_s"] = float(self.grace.value())
        self.cfg["renag_s"] = float(self.renag.value())
        self.cfg["away_s"] = float(self.away.value())
        self._commit()

    def _simple_save(self, *_):
        self.cfg["toasts_enabled"] = self.toasts.isChecked()
        self.cfg["sound_on"] = self.sound.isChecked()
        self.cfg["reminder_enabled"] = self.reminder.isChecked()
        self.cfg["reminder_interval_min"] = int(self.reminder_min.value())
        self.cfg["reminder_break_min"] = int(self.break_min.value())
        self.reminder_sample.set_break_minutes(self.break_min.value())
        self._commit()

    def _camera_changed(self):
        text = self.cam.currentText()
        if text:
            new_cam = int(text.split()[-1])
            if new_cam != self.cfg["camera_index"]:
                self.cfg["camera_index"] = new_cam
                self._commit()

    def _changes(self):
        changes = {}
        for key, value in self.cfg.items():
            if key == "hud":
                patch = {k: v for k, v in value.items() if self._original[key].get(k) != v}
                if self._reset_hud_position:
                    patch.update(x=None, y=None)
                if patch:
                    changes[key] = copy.deepcopy(patch)
            elif value != self._original.get(key):
                changes[key] = copy.deepcopy(value)
        return changes

    def _startup_change(self):
        if self.autostart is not None and self.autostart.isChecked() != self._startup_original:
            return self.autostart.isChecked()
        return None

    def _commit(self, *_):
        if not self._ready:
            return True
        changes, startup = self._changes(), self._startup_change()
        if not changes and startup is None:
            return True
        try:
            self.app.apply_preferences(changes, startup=startup)
        except (OSError, RuntimeError) as exc:
            self.cfg = copy.deepcopy(self._original)
            self._reset_hud_position = False
            self._load_controls()
            self.save_status.setText(f"Not saved: {exc}. Your previous setting was restored.")
            self.save_status.setStyleSheet(f"color: {theme.SHRIMP};")
            return False
        self._original = copy.deepcopy(self.cfg)
        if startup is not None:
            self._startup_original = startup
        self._reset_hud_position = False
        self.save_status.setText("Changes saved")
        self.save_status.setStyleSheet("")
        self._update_dependencies()
        return True

    def _load_controls(self):
        c = self.cfg
        values = ((self.mascot_on, c["mascot_enabled"]),
                  (self.mascot_bob, c["mascot_bob"]), (self.reduce_motion, c["reduce_motion"]),
                  (self.hud_visible, c["hud"]["visible"]), (self.hud_compact, c["hud"]["compact"]),
                  (self.toasts, c["toasts_enabled"]), (self.sound, c["sound_on"]),
                  (self.reminder, c["reminder_enabled"]))
        for control, value in values:
            with QSignalBlocker(control):
                control.setChecked(value)
        for control, value in ((self.mascot_size, c["mascot_size"]),
                               (self.mascot_style, c.get("mascot_style", "shrimp")),
                               (self.hud_size, c["hud"]["size"]),
                               (self.hud_orientation, c["hud"].get("orientation", "horizontal")),
                               (self.mascot_position, c["mascot_position"]),
                               (self.mascot_screen, c["mascot_screen"]),
                               (self.mascot_entrance, c.get("mascot_entrance", "rise")),
                               (self.theme_mode, c.get("theme_mode", "dark"))):
            with QSignalBlocker(control):
                control.setCurrentIndex(control.findData(value))
        for control, value in ((self.mascot_op, round((1-c["mascot_opacity"])*100)),
                               (self.hud_op, round((1-c["hud"].get("opacity", 1.0))*100)),
                               (self.sens, round(c["sensitivity"]*10)),
                               (self.grace, c["grace_s"]), (self.renag, c["renag_s"]),
                               (self.away, c["away_s"]), (self.reminder_min, c["reminder_interval_min"]),
                               (self.break_min, c["reminder_break_min"]),
                               (self.mascot_bad_hold, c.get("mascot_bad_hold_s", 2)),
                               (self.mascot_recovery_hold, c.get("mascot_recovery_hold_s", 3))):
            with QSignalBlocker(control):
                control.setValue(int(value))
        with QSignalBlocker(self.cam):
            self.cam.setCurrentText(f"Camera {c['camera_index']}")
        if self.autostart is not None:
            with QSignalBlocker(self.autostart):
                self.autostart.setChecked(self._startup_original)
        self.opacity_label.setText(f"{self.mascot_op.value()}%")
        self.hud_op_label.setText(f"{self.hud_op.value()}%")
        self.sens_lbl.setText(f"{c['sensitivity']:.1f}×")
        self._refresh_samples()
        self.reminder_sample.set_break_minutes(c["reminder_break_min"])
        self._update_dependencies()

    def _update_dependencies(self):
        shrimp_on = self.mascot_on.isChecked()
        for control in (self.mascot_style, self.mascot_size, self.mascot_op,
                        self.mascot_position, self.mascot_screen):
            control.setEnabled(shrimp_on)
        self.mascot_entrance.setEnabled(shrimp_on and not self.reduce_motion.isChecked())
        self.mascot_bad_hold.setEnabled(shrimp_on)
        self.mascot_recovery_hold.setEnabled(shrimp_on)
        self.mascot_bob.setEnabled(shrimp_on and not self.reduce_motion.isChecked())
        self.mascot_bob.setToolTip("Enable the floating cue and turn off Reduce motion to animate it.")
        self.hud_size.setEnabled(self.hud_visible.isChecked())
        self.hud_orientation.setEnabled(self.hud_visible.isChecked())
        self.hud_op.setEnabled(self.hud_visible.isChecked())
        self.hud_compact.setEnabled(self.hud_visible.isChecked())
        self.reminder_min.setEnabled(self.reminder.isChecked())
        self.break_min.setEnabled(self.reminder.isChecked())

    def eventFilter(self, watched, event):
        if watched in (self.sens, self.mascot_op, self.hud_op) and event.type() == QEvent.FocusOut:
            self._commit()
        return super().eventFilter(watched, event)

    def accept(self):
        if not self._commit():
            return False
        super().accept()
        return True

    def _discard(self):
        self.reject()

    def _finish_pending(self):
        return self.accept()

    def reject(self):
        if self._commit():
            super().reject()

    def _task(self, callback):
        if self._commit():
            callback()

    def _retry_camera(self):
        if not self._retry_timer.isActive() and self._commit():
            self.camera_retry.setText("Retrying…")
            self.app.restart_camera()
            self._retry_timer.start(1200)

    def _finish_retry_feedback(self):
        self.camera_retry.setText("Retry camera")

    def _test_sound(self):
        from .app import _chime
        self._task(_chime)

    def _test_notification(self):
        if self._commit():
            self.app.tray.toast("Shrimply · test notification", "Example posture reminder. Your tracking and reminder timer have not changed.")
            self.test_status.setText("Test notification requested. Windows controls whether it is displayed.")
            self.test_status.show()

    def _open_data_folder(self):
        import config
        if self._commit() and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.APP_DIR))):
            self.save_status.setText("Could not open the data folder.")

    def _calibrate(self):
        if self._finish_pending():
            self.calibrate_requested.emit()

    def _rescan(self):
        if self._rescan_timer.isActive() or not self._commit():
            return
        self.rescan_button.setText("Scanning…")
        self._rescan_timer.start(180)

    def _finish_rescan(self):
        selected = int(self.cfg["camera_index"])
        try:
            cams = available_cameras(skip=int(self._live_cfg["camera_index"]))
        except Exception:
            self.rescan_button.setText("Retry scan")
            return
        if selected not in cams:
            cams.append(selected)
        with QSignalBlocker(self.cam):
            self.cam.clear()
            self.cam.addItems([f"Camera {i}" for i in cams])
            self.cam.setCurrentText(f"Camera {self.cfg['camera_index']}")
        self.rescan_button.setText("Rescan")

    def _confirm_reset(self):
        if not self._commit():
            return
        from PySide6.QtWidgets import QMessageBox

        ans = QMessageBox.question(
            self,
            "Reset baseline",
            "Discard your calibrated baseline?\n"
            "You'll need to calibrate again before Shrimply can score your posture.\n"
            "Your saved history and other settings will be kept.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            self.reset_baseline_requested.emit()

    # ------------------------------------------------------------------
    def select_page(self, name: str):
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == name:
                self.tabs.setCurrentIndex(index)
                return
        raise ValueError(f"Unknown settings page: {name}")
