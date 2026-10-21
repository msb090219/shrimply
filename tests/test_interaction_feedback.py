from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QSlider, QSpinBox, QTabWidget,
    QPushButton, QWidget,
)

from shrimply.ui import theme


def test_pointer_feedback_covers_desktop_controls_but_not_disabled_or_passive_widgets():
    app = QApplication.instance() or QApplication([])
    window = QWidget()
    theme.apply_desktop_theme(window)
    button = QPushButton("Action", window)
    checkbox = QCheckBox("Option", window)
    combo = QComboBox(window)
    slider = QSlider(Qt.Horizontal, window)
    spinbox = QSpinBox(window)
    tabs = QTabWidget(window)
    tabs.addTab(QWidget(), "Page")
    controls = (button, checkbox, combo, slider, spinbox, tabs.tabBar())
    for control in controls:
        control.setCursor(Qt.ArrowCursor)
        app.sendEvent(control, QEvent(QEvent.Enter))
        assert control.cursor().shape() == Qt.PointingHandCursor

    button.setEnabled(False)
    assert button.cursor().shape() == Qt.ArrowCursor
    assert window.cursor().shape() == Qt.ArrowCursor
    window.deleteLater()
    app.processEvents()
