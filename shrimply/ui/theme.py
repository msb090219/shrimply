"""Design tokens — the single source of truth for Shrimply's look.

Every window (HUD, preview, mascot, dialogs, tray) draws from here, so
the brand can be retuned by editing one file. Palette, radii, typography.
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QColor, QPalette, QIcon
from PySide6.QtWidgets import (
    QApplication, QAbstractButton, QAbstractSpinBox, QComboBox, QSlider, QTabBar,
    QWidget,
)

# --- palette ---------------------------------------------------------------
PLATE = QColor(18, 20, 24, 235)  # dark panel behind everything
PLATE_HUD = QColor(18, 20, 24, 232)
WELL = QColor(0, 0, 0)  # video well
TEXT = "#e5e8ec"
TEXT_MUTED = "#9ca3af"
TEXT_DIM = "#d1d5d9"
_MODE = "dark"
_CHOICE = "dark"
_system_theme_connected = False

GOOD = "#22c55e"
DRIFT = "#f59e0b"
BAD = "#ef4444"
INFO = "#3b82f6"
MUTED = "#6b7280"
SHRIMP = "#ec8f6b"  # cooked-shrimp salmon, from the app's founding reference
DARK_TITLEBAR = 0x242424

SEGMENT_OFF = QColor(255, 255, 255, 36)

# state -> hex used by tray/spine tinting (kept name for compatibility)
STATE_COLORS = {
    "good": GOOD,
    "drifting": DRIFT,
    "bad": BAD,
    "away": MUTED,
    "paused": "#9ca3af",
    "camera_error": INFO,
    "uncalibrated": SHRIMP,  # uncalibrated = brand moment
}

# --- shape -----------------------------------------------------------------
R_PLATE = 12  # standalone boxes
R_HUD = 10  # the bar
R_INNER = 8  # video well

# --- type ------------------------------------------------------------------
FONT = "Segoe UI"
COMPACT_CONTROL_HEIGHT = 28
HUD_HEIGHT = 40


def set_mode(mode: str) -> None:
    """Apply the selected palette to existing and future windows."""
    global _MODE, _CHOICE, _system_theme_connected
    global PLATE, PLATE_HUD, WELL, TEXT, TEXT_MUTED, TEXT_DIM, MUTED
    from PySide6.QtWidgets import QApplication

    _CHOICE = mode if mode in ("dark", "light", "system") else "dark"
    app = QApplication.instance()
    if app is not None and not _system_theme_connected:
        app.styleHints().colorSchemeChanged.connect(_on_system_theme_changed)
        _system_theme_connected = True
    _MODE = ("dark" if _CHOICE == "system" and (app is None or
             app.styleHints().colorScheme() != Qt.ColorScheme.Light) else
             "light" if _CHOICE == "system" else _CHOICE)
    if _MODE == "dark":
        colors = {"window": "#1e1e1e", "window_text": "#f3f4f6", "base": "#181818",
                  "alternate": "#242424", "text": "#f3f4f6", "button": "#2b2b2b",
                  "button_text": "#f3f4f6", "mid": "#393939", "midlight": "#343434",
                  "dark": "#121212", "muted": "#9ca3af", "well": "#101010"}
        PLATE, PLATE_HUD = QColor(18, 20, 24, 235), QColor(18, 20, 24, 232)
    else:
        colors = {"window": "#f4f2ef", "window_text": "#252525", "base": "#ffffff",
                  "alternate": "#f0eeeb", "text": "#252525", "button": "#e8e5e1",
                  "button_text": "#252525", "mid": "#d5d1cc", "midlight": "#e4e1dc",
                  "dark": "#c5c1bc", "muted": "#727272", "well": "#171717"}
        PLATE, PLATE_HUD = QColor(246, 244, 241, 242), QColor(246, 244, 241, 238)
    WELL = QColor(colors["well"])
    TEXT, TEXT_MUTED, TEXT_DIM, MUTED = (colors["text"], colors["muted"],
                                         colors["text"], colors["muted"])
    if app is None:
        return
    palette = app.palette()
    for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        for role, key in ((QPalette.Window, "window"), (QPalette.WindowText, "window_text"),
                          (QPalette.Base, "base"), (QPalette.AlternateBase, "alternate"),
                          (QPalette.Text, "text"), (QPalette.Button, "button"),
                          (QPalette.ButtonText, "button_text"), (QPalette.Mid, "mid"),
                          (QPalette.Midlight, "midlight"), (QPalette.Dark, "dark"),
                          (QPalette.PlaceholderText, "muted")):
            color = QColor(colors[key])
            if group == QPalette.Disabled and role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
                color.setAlpha(145)
            palette.setColor(group, role, color)
        palette.setColor(group, QPalette.Highlight, QColor(SHRIMP))
        palette.setColor(group, QPalette.HighlightedText, QColor("#181b20"))
        palette.setColor(group, QPalette.Accent, QColor(SHRIMP))
        palette.setColor(group, QPalette.ToolTipBase, QColor(colors["base"]))
        palette.setColor(group, QPalette.ToolTipText, QColor(colors["text"]))
    app.setPalette(palette)
    for window in app.topLevelWidgets():
        window.setPalette(palette)
        if window.styleSheet():
            window.setStyleSheet(window.styleSheet())
        apply_titlebar_theme(window)
        if hasattr(window, "apply_theme"):
            window.apply_theme()


def _on_system_theme_changed(_scheme) -> None:
    if _CHOICE == "system":
        QTimer.singleShot(0, lambda: set_mode("system"))


def mode() -> str:
    return _MODE


def caption_colors():
    if _MODE == "light":
        return QColor(255, 255, 255, 235), QColor(20, 20, 20, 34)
    return QColor(18, 20, 24, 225), QColor(255, 255, 255, 34)

# Keep system surfaces; use the brand accent for interactive selection.
DESKTOP_QSS = """
QMainWindow, QDialog, QWidget#calibrationWindow { font-size: 13px; }
QGroupBox { font-weight: 600; margin-top: 12px; padding: 16px 10px 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton { min-height: 18px; padding: 6px 12px;
    background: palette(button); color: palette(button-text);
    border: 1px solid transparent; border-radius: 6px; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit, QListWidget {
    min-height: 18px; padding: 4px 6px; color: palette(text);
    background: palette(base); border: 1px solid palette(mid); border-radius: 5px;
}
QComboBox QAbstractItemView { color: palette(text); background: palette(base);
    selection-background-color: palette(highlight); selection-color: palette(highlighted-text); }
QScrollBar:vertical { background: palette(window); width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: palette(mid); min-height: 24px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QGroupBox#sectionCard {
    border: 1px solid palette(mid); border-radius: 6px;
    margin-top: 0; padding: 0; font-weight: normal;
}
QTabWidget::pane { border: 0; border-top: 1px solid palette(mid); padding: 0; }
QTabWidget#settingsTabs::pane { border: 0; }
QTabBar::tab { padding: 8px 14px; background: palette(window); color: palette(text); }
QTabBar::tab:hover { color: palette(text); }
QTabBar::tab:selected { background: palette(base); }
QTabBar#settingsTabBar::tab { background: transparent; padding: 9px 12px; }
QTabBar#settingsTabBar::tab:selected { background: transparent; font-weight: 600; }
QPushButton:hover { background: palette(midlight); }
QPushButton:pressed { background: palette(dark); }
QCheckBox:hover::indicator { border-color: palette(highlight); }
QToolButton#settingsButton, QToolButton#refreshButton { border: 1px solid transparent; border-radius: 4px; padding: 0; }
QToolButton#settingsButton:hover, QToolButton#refreshButton:hover { background: palette(midlight); }
QFrame#navigationRail { background: palette(alternate-base); border-right: 1px solid palette(mid); }
QToolButton#navButton, QToolButton#sidebarToggle {
    background: transparent; color: palette(text); border: 1px solid transparent;
    border-radius: 6px; padding: 4px 8px; text-align: left;
}
QToolButton#navButton:hover, QToolButton#sidebarToggle:hover { background: palette(button); }
"""
_CHECK_ICON = (Path(__file__).resolve().parents[2] / "assets/icons/check.svg").as_posix().replace('"', '\\"')
DESKTOP_QSS += f"""
QPushButton:default, QPushButton:focus {{ border-color: {SHRIMP}; }}
QPushButton[primary="true"] {{ background: {SHRIMP}; color: #181b20; font-weight: 600; }}
QPushButton[primary="true"]:hover {{ background: #f3a482; }}
QPushButton[primary="true"]:pressed {{ background: #d77f5d; }}
QPushButton:disabled {{ color: palette(mid); background: palette(base); border-color: transparent; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid palette(mid); border-radius: 3px; background: palette(base); }}
QCheckBox::indicator:checked {{ background: {SHRIMP}; border-color: {SHRIMP}; image: url("{_CHECK_ICON}"); }}
QCheckBox::indicator:disabled {{ background: palette(mid); border-color: palette(mid); }}
QCheckBox:focus {{ outline: 1px dotted {SHRIMP}; }}
QToolButton#settingsButton[keyboardFocus="true"], QToolButton#refreshButton[keyboardFocus="true"] {{ border-color: {SHRIMP}; }}
QToolButton#navButton:checked {{ background: palette(midlight); }}
QToolButton#navButton:checked:hover {{ background: palette(mid); }}
QToolButton#navButton[keyboardFocus="true"], QToolButton#sidebarToggle[keyboardFocus="true"] {{ border-color: {SHRIMP}; }}
QTabBar::tab {{ border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ border-bottom-color: {SHRIMP}; }}
QSlider::groove:horizontal {{ height: 4px; background: palette(mid); border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {SHRIMP}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {SHRIMP}; width: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::handle:horizontal:focus {{ border: 2px solid palette(text); }}
QSlider::sub-page:horizontal:disabled, QSlider::handle:horizontal:disabled {{ background: palette(mid); }}
"""


def apply_desktop_theme(widget) -> None:
    _install_pointer_feedback()
    _install_windows_titlebar_theme()
    widget.setWindowIcon(app_icon())
    palette = widget.palette()
    for group in (QPalette.Active, QPalette.Inactive):
        palette.setColor(group, QPalette.Highlight, QColor(SHRIMP))
        palette.setColor(group, QPalette.HighlightedText, QColor("#181b20"))
        palette.setColor(group, QPalette.Accent, QColor(SHRIMP))
    widget.setPalette(palette)
    widget.setStyleSheet(DESKTOP_QSS)


class _PointerFeedback(QObject):
    def eventFilter(self, obj, event):
        if (isinstance(obj, (QAbstractButton, QAbstractSpinBox, QComboBox, QSlider, QTabBar))
                and event.type() in (QEvent.Enter, QEvent.EnabledChange)):
            obj.setCursor(Qt.PointingHandCursor if obj.isEnabled() else Qt.ArrowCursor)
        return False


_pointer_feedback = None


def _install_pointer_feedback() -> None:
    global _pointer_feedback
    app = QApplication.instance()
    if app is not None and _pointer_feedback is None:
        _pointer_feedback = _PointerFeedback(app)
        app.installEventFilter(_pointer_feedback)


class _WindowsTitlebarTheme(QObject):
    def eventFilter(self, obj, event):
        if (isinstance(obj, QWidget) and obj.isWindow()
                and not obj.windowFlags() & Qt.FramelessWindowHint
                and event.type() in (QEvent.Show, QEvent.WindowActivate, QEvent.WindowDeactivate)):
            try:
                hwnd = ctypes.c_void_p(int(obj.winId()))
                color = ctypes.c_uint(0xF4F2EF if _MODE == "light" else DARK_TITLEBAR)
                text = ctypes.c_uint(0x252525 if _MODE == "light" else 0xFFFFFF)
                dwm = ctypes.windll.dwmapi
                # Windows 11 supports explicit caption colors; older versions retain their defaults.
                for attribute, value in ((35, color), (36, text)):
                    dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
            except (AttributeError, OSError):
                pass
        return False


_windows_titlebar_filter = None


def _install_windows_titlebar_theme() -> None:
    global _windows_titlebar_filter
    app = QApplication.instance()
    if sys.platform == "win32" and app is not None and _windows_titlebar_filter is None:
        _windows_titlebar_filter = _WindowsTitlebarTheme(app)
        app.installEventFilter(_windows_titlebar_filter)


def apply_titlebar_theme(widget) -> None:
    if sys.platform == "win32" and widget.isVisible() and not widget.windowFlags() & Qt.FramelessWindowHint:
        try:
            hwnd = ctypes.c_void_p(int(widget.winId()))
            caption = ctypes.c_uint(0xF4F2EF if _MODE == "light" else DARK_TITLEBAR)
            text = ctypes.c_uint(0x252525 if _MODE == "light" else 0xFFFFFF)
            dwm = ctypes.windll.dwmapi
            for attribute, value in ((35, caption), (36, text)):
                dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
        except (AttributeError, OSError):
            pass


def app_icon():
    return QIcon(str(Path(__file__).resolve().parents[2] / "assets" / "shrimply.png"))


def font(pt: int, bold: bool = False):
    from PySide6.QtGui import QFont

    return QFont(FONT, pt, QFont.Bold if bold else QFont.Normal)


# --- tray menu ----------------------------------------------------------------
MENU_QSS = f"""
QMenu {{
    background: palette(window); color: palette(text);
    border: 1px solid palette(mid);
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 3px;
    margin: 1px 2px;
}}
QMenu::item:selected {{ background: palette(midlight); }}
QMenu::separator {{ height: 1px; background: palette(mid); margin: 5px 10px; }}
QMenu::item:disabled {{ color: palette(mid); }}
QLabel {{ color: palette(text); }}
"""
