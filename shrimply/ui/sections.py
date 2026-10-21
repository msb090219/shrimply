"""Shared desktop sections with headings aligned inside their borders."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout


def section(title: str, icon=None):
    card = QGroupBox()
    card.setObjectName("sectionCard")
    card.setAccessibleName(title)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 14)
    layout.setSpacing(12)
    heading = QLabel(title)
    heading.setObjectName("sectionTitle")
    font = heading.font()
    font.setBold(True)
    heading.setFont(font)
    if icon is None:
        layout.addWidget(heading)
    else:
        row = QHBoxLayout()
        row.setSpacing(8)
        mark = QLabel()
        mark.setPixmap(icon.pixmap(18, 18))
        row.addWidget(mark)
        row.addWidget(heading)
        row.addStretch()
        layout.addLayout(row)
    form = QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.WrapLongRows)
    form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    form.setHorizontalSpacing(20)
    form.setVerticalSpacing(10)
    layout.addLayout(form)
    return card, form
