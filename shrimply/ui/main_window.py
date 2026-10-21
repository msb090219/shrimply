"""The ordinary desktop home for Shrimply; closing it leaves tracking in the tray."""
from __future__ import annotations

import sys
from datetime import date

from PySide6.QtCore import QTimer, Qt, QSize, QEvent
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QStackedWidget, QSizePolicy,
)

from . import theme
from .stats import StatsTab
from .sections import section
from .icons import settings_icon, home_icon, sidebar_icon, IconButton
from .status import camera_status


DAILY_LINES = (
    "Stop shrimping. Start shining.",
    "Keep calm and sit tall.",
    "Just keep straightening up.",
    "Seas the day. Sit tall your way.",
    "Fall seven times, straighten up eight.",
    "Where there's a will, there's a straighter way.",
    "Every journey begins with one small stretch.",
    "Good things come to those who take a break.",
    "Dream big. Start small. Sit tall.",
    "If at first you shrimp, straighten up again.",
    "There's no time like now to sit tall.",
    "Believe you can, and you're halfway upright.",
    "Rise and shine. Leave shrimp mode behind.",
    "When life curls you up, rise again.",
    "Progress, not prawn-fection.",
    "The world is your oyster. Stretch first.",
    "Be the change you wish to sea.",
    "Shell yeah, you've got this.",
    "One day or day one? Stand tall today.",
    "Never give up. Never shrimp in.",
)


def _scroll_page(widget):
    scroll = QScrollArea()
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setWidget(widget)
    return scroll


class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Shrimply")
        self.resize(960, 680)
        self.setMinimumSize(620, 480)
        theme.apply_desktop_theme(self)
        if sys.platform == "darwin":
            self._create_mac_menus()

        root = QWidget()
        root.setAttribute(Qt.WA_ContentsMarginsRespectsSafeArea, False)
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("navigationRail")
        nav = QVBoxLayout(self.sidebar)
        nav.setContentsMargins(8, 12, 8, 12)
        nav.setSpacing(8)
        self.sidebar_toggle = IconButton()
        self.sidebar_toggle.setObjectName("sidebarToggle")
        self.sidebar_toggle.setFixedSize(40, 40)
        self.sidebar_toggle.setIconSize(QSize(20, 20))
        self.sidebar_toggle.setAccessibleName("Collapse menu")
        self.sidebar_toggle.setToolTip("Collapse menu")
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        nav.addWidget(self.sidebar_toggle, 0, Qt.AlignLeft)
        self.dashboard_button = IconButton()
        self.dashboard_button.setObjectName("navButton")
        self.dashboard_button.setText("\u2002Dashboard")
        self.dashboard_button.setAccessibleName("Dashboard")
        self.dashboard_button.setToolTip("Dashboard")
        self.dashboard_button.setShortcut("Alt+D")
        self.dashboard_button.clicked.connect(self._navigate_dashboard)
        nav.addWidget(self.dashboard_button)
        nav.addStretch()
        settings = self.settings_button = IconButton()
        settings.setObjectName("navButton")
        settings.setText("\u2002Settings")
        settings.setToolTip("Settings")
        settings.setAccessibleName("Settings")
        if sys.platform != "darwin":  # macOS uses the application menu's ⌘,
            settings.setShortcut("Alt+S")
        settings.setFocusPolicy(Qt.StrongFocus)
        settings.clicked.connect(controller._open_settings)
        nav.addWidget(settings)
        nav_font = QFont(self.font())
        nav_font.setPointSize(11)
        nav_font.setWeight(QFont.DemiBold)
        for button in (self.dashboard_button, settings):
            button.setCheckable(True)
            button.setFixedHeight(44)
            button.setIconSize(QSize(20, 20))
            button.setFont(nav_font)
            button.setFocusPolicy(Qt.StrongFocus)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        shell.addWidget(self.sidebar)
        body = QWidget()
        shell.addWidget(body, 1)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 0, 16, 16)
        layout.setSpacing(12)
        self.settings_heading = QLabel("Settings")
        heading = self.dashboard_heading = QLabel("Dashboard")
        heading_font = QFont(heading.font())
        heading_font.setPointSize(20)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.settings_heading.setFont(heading_font)
        self.settings_heading.setContentsMargins(16, 16, 16, 0)
        layout.addWidget(self.settings_heading)
        self.settings_heading.hide()
        today = QWidget()
        content = QVBoxLayout(today)
        content.setContentsMargins(16, 16, 16, 16)
        content.setSpacing(20)
        content.addWidget(heading)
        content.addSpacing(4)
        notice, form = section("Set up posture tracking")
        self.notice_card = notice
        self.notice_heading = notice.findChild(QLabel, "sectionTitle")
        self.notice_detail = QLabel()
        self.notice_detail.setWordWrap(True)
        form.addRow(self.notice_detail)
        actions = QHBoxLayout()
        self.calibrate = QPushButton("Calibrate…")
        self.calibrate.clicked.connect(controller.start_calibration)
        actions.addWidget(self.calibrate)
        self.camera_retry = QPushButton("Retry camera")
        self.camera_retry.clicked.connect(controller.restart_camera)
        actions.addWidget(self.camera_retry)
        self.tracking_settings = QPushButton("Camera settings…")
        self.tracking_settings.clicked.connect(lambda: controller._open_settings_page("Tracking"))
        actions.addWidget(self.tracking_settings)
        actions.addStretch()
        form.addRow(actions)
        content.addWidget(notice)
        self.daily_line = QLabel()
        quote_font = QFont(self.daily_line.font())
        quote_font.setPointSize(15)
        quote_font.setBold(True)
        self.daily_line.setFont(quote_font)
        self.daily_line.setWordWrap(True)
        content.addWidget(self.daily_line)
        self.progress = StatsTab(controller.log)
        self.progress.layout().setContentsMargins(0, 0, 0, 0)
        content.addWidget(self.progress)
        content.addStretch()
        self.dashboard_page = _scroll_page(today)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.dashboard_page)
        layout.addWidget(self.pages)
        self._sidebar_expanded = False
        self.toggle_sidebar()
        self._set_active_page("Dashboard")
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.refresh()
        screen = self.screen()
        if screen is not None:
            area = screen.availableGeometry()
            self.resize(min(960, max(620, area.width() - 48)),
                        min(680, max(480, area.height() - 64)))

    def toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        self.sidebar.setFixedWidth(168 if self._sidebar_expanded else 56)
        style = Qt.ToolButtonTextBesideIcon if self._sidebar_expanded else Qt.ToolButtonIconOnly
        for button in (self.dashboard_button, self.settings_button):
            button.setToolButtonStyle(style)
        label = "Collapse menu" if self._sidebar_expanded else "Expand menu"
        self.sidebar_toggle.setAccessibleName(label)
        self.sidebar_toggle.setToolTip(label)
        self._refresh_nav_icons()

    def _set_active_page(self, name):
        self.dashboard_button.setChecked(name == "Dashboard")
        self.settings_button.setChecked(name == "Settings")

    def _navigate_dashboard(self):
        settings = getattr(self.controller, "_settings_dlg", None)
        if settings is not None:
            settings.accept()
            if self.pages.currentWidget() is settings:
                self._set_active_page("Settings")
        else:
            self._set_active_page("Dashboard")

    def _refresh_nav_icons(self):
        color = self.palette().text().color()
        self.sidebar_toggle.setIcon(sidebar_icon(color))
        self.dashboard_button.setIcon(home_icon(color))
        self.settings_button.setIcon(settings_icon(color))

    def show_settings(self, settings):
        if self.pages.indexOf(settings) < 0:
            self.pages.addWidget(settings)
        self.pages.setCurrentWidget(settings)
        self.settings_heading.show()
        self._set_active_page("Settings")
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        settings.tabs.setFocus(Qt.OtherFocusReason)

    def _create_mac_menus(self):
        app_menu = self.menuBar().addMenu("Shrimply")
        for title, role, shortcut, callback in (
            ("About Shrimply", QAction.AboutRole, None, lambda: self.controller._show_about()),
            ("Settings…", QAction.PreferencesRole, QKeySequence.Preferences, self.controller._open_settings),
            ("Quit Shrimply", QAction.QuitRole, QKeySequence.Quit, lambda: self.controller._on_quit()),
        ):
            action = QAction(title, self)
            action.setMenuRole(role)
            if shortcut is not None:
                action.setShortcut(shortcut)
                action.setShortcutContext(Qt.ApplicationShortcut)
            action.triggered.connect(callback)
            app_menu.addAction(action)
        file_menu = self.menuBar().addMenu("File")
        close = file_menu.addAction("Close Window")
        close.setShortcut(QKeySequence.Close)
        close.triggered.connect(self.close)
        window_menu = self.menuBar().addMenu("Window")
        minimize = window_menu.addAction("Minimize")
        minimize.setShortcut("Ctrl+M")  # Qt maps Ctrl to Command on macOS.
        minimize.triggered.connect(self.showMinimized)

    def show_dashboard(self, settings):
        self.pages.setCurrentWidget(self.dashboard_page)
        self.pages.removeWidget(settings)
        self.settings_heading.hide()
        self._set_active_page("Dashboard")
        self.dashboard_button.setFocus(Qt.OtherFocusReason)
        self.refresh()
        self.progress.refresh()

    def apply_theme(self):
        settings = getattr(self.controller, "_settings_dlg", None)
        if settings is not None:
            settings.apply_theme()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange) and hasattr(self, "settings_button"):
            self._refresh_nav_icons()

    def refresh(self):
        today = date.today()
        if getattr(self, "_daily_line_date", None) != today:
            self._daily_line_date = today
            self.daily_line.setText(f"“{DAILY_LINES[today.toordinal() % len(DAILY_LINES)]}”")
        app = self.controller
        state = app.machine.state.value
        camera_issue = state == "camera_error" and not (app._suspended or app._idle_stopped or app._cal)
        needs_setup = (app.baseline is None or state == "uncalibrated") and not (app._suspended or app._cal)
        self.notice_card.setVisible(camera_issue or needs_setup)
        self.calibrate.setVisible(needs_setup and not camera_issue)
        self.camera_retry.setVisible(camera_issue)
        self.tracking_settings.setVisible(camera_issue)
        if camera_issue:
            _, detail = camera_status(app)
            self.notice_heading.setText("Camera unavailable")
            self.notice_card.setAccessibleName("Camera unavailable")
            self.notice_detail.setText(detail)
        elif needs_setup:
            self.notice_heading.setText("Set up posture tracking")
            self.notice_card.setAccessibleName("Set up posture tracking")
            self.notice_detail.setText("Calibrate in your usual working position to start tracking.")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        if self.pages.currentWidget() is self.dashboard_page:
            self.progress.refresh()
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        settings = getattr(self.controller, "_settings_dlg", None)
        if self.pages.currentWidget() is not self.dashboard_page and settings is not None:
            if not settings._finish_pending():
                event.ignore()
                return
        # Closing the home window must not quit the tray app or stop capture.
        self.hide()
        event.ignore()
