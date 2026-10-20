"""Local posture history with a daily activity calendar and weekly time mix."""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QEvent, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from . import theme
from .icons import refresh_icon
from .sections import section

_WEEKS = 26
_CELL = 20
_GAP = 4


def _duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    if seconds > 0 and minutes == 0:
        return "<1 min"
    if minutes < 60:
        return f"{minutes} min"
    hours, remainder = divmod(minutes, 60)
    return f"{hours} h {remainder} min" if remainder else f"{hours} h"


class _MixBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(22)
        self.values = (0., 0., 0.)

    def set_values(self, values):
        self.values = values
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = QRectF(0, 0, self.width(), self.height())
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.palette().mid().color())
        painter.drawRoundedRect(area, 4, 4)
        total = sum(self.values)
        if total:
            clip = QPainterPath()
            clip.addRoundedRect(area, 4, 4)
            painter.setClipPath(clip)
            left = 0.
            for value, color in zip(self.values, (theme.GOOD, theme.DRIFT, theme.BAD)):
                width = self.width() * value / total
                painter.fillRect(QRectF(left, 0, width, self.height()), QColor(color))
                left += width


class StatsTab(QWidget):
    def __init__(self, log):
        super().__init__()
        self.log = log
        self._selected = date.today()
        self._calendar_today = None
        self._weeks_shown = 0
        self._cells = {}
        self._cell_days = {}
        self._days = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(20)

        today, today_form = section("Today")
        self.today_lbl = QLabel()
        self.today_lbl.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.today_lbl.setWordWrap(True)
        today_form.addRow(self.today_lbl)
        lay.addWidget(today)

        week, week_form = section("This week")
        self.week_lbl = QLabel()
        self.week_lbl.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.week_lbl.setWordWrap(True)
        week_form.addRow(self.week_lbl)
        self.mix = _MixBar()
        self.mix.setAccessibleName("Weekly posture mix")
        week_form.addRow(self.mix)
        legend = QHBoxLayout()
        legend.setSpacing(12)
        self.mix_values = []
        for caption in ("Comfortable", "Drifting", "Adjust"):
            label = QLabel()
            label.setWordWrap(True)
            self.mix_values.append(label)
            legend.addWidget(label, 1)
        week_form.addRow(legend)
        self.mix_detail = QLabel()
        self.mix_detail.setWordWrap(True)
        week_form.addRow(self.mix_detail)
        lay.addWidget(week)

        calendar, calendar_form = section("Last 26 weeks")
        self.calendar_card = calendar
        self.calendar_heading = calendar.findChild(QLabel, "sectionTitle")
        calendar_form.setVerticalSpacing(18)
        summary = QHBoxLayout()
        summary.setSpacing(16)
        for caption, name in (("Tracked days", "tracked_days"),
                              ("Monitored time", "monitored_time"),
                              ("Time in range", "in_range")):
            column = QVBoxLayout()
            column.setSpacing(4)
            value = QLabel()
            value.setStyleSheet("font-size: 20px; font-weight: 600;")
            setattr(self, name, value)
            column.addWidget(value)
            column.addWidget(QLabel(caption))
            summary.addLayout(column, 1)
        calendar_form.addRow(summary)
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setContentsMargins(0, 0, 0, 0)
        self.calendar_grid.setHorizontalSpacing(_GAP)
        self.calendar_grid.setVerticalSpacing(_GAP)
        self.calendar_grid.setColumnMinimumWidth(0, 24)
        self.calendar_grid.setRowMinimumHeight(0, 26)
        self.calendar_grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        chart = QWidget()
        chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        chart_layout = QVBoxLayout(chart)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(5)
        chart_layout.addLayout(self.calendar_grid)
        chart_layout.addSpacing(8)
        self.selected_date = QLabel()
        self.selected_date.setStyleSheet("font-weight: 600;")
        chart_layout.addWidget(self.selected_date)
        self.day_detail = QLabel()
        self.day_detail.setWordWrap(True)
        refresh = self.refresh_button = QPushButton("Refresh")
        refresh.setIcon(refresh_icon(self.palette().text().color()))
        refresh.setToolTip("Refresh progress (Alt+R)")
        refresh.setAccessibleName("Refresh progress")
        refresh.setShortcut("Alt+R")
        refresh.setFocusPolicy(Qt.StrongFocus)
        refresh.clicked.connect(self._manual_refresh)
        actions = QHBoxLayout()
        actions.setSpacing(12)
        actions.addWidget(self.day_detail, 1)
        actions.addWidget(refresh)
        chart_layout.addLayout(actions)
        calendar_form.addRow(chart)
        calendar.setToolTip("Paused, away and unreadable time is excluded. Older sample-based estimates do not count toward timed totals.")
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._finish_manual_refresh)
        lay.addWidget(calendar)
        for card, form in ((today, today_form), (week, week_form), (calendar, calendar_form)):
            card.layout().setContentsMargins(18, 16, 18, 18)
            card.layout().setSpacing(16)
            form.setVerticalSpacing(14 if card is not calendar else 18)
        lay.addStretch(1)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange):
            if hasattr(self, "refresh_button"):
                self.refresh_button.setIcon(refresh_icon(self.palette().text().color()))
            if hasattr(self, "_cells"):
                self._refresh_cells()
            if hasattr(self, "mix"):
                self.mix.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._calendar_today is not None and self._week_count() != self._weeks_shown:
            QTimer.singleShot(0, self.refresh)

    def _week_count(self):
        return max(1, min(_WEEKS, (self.width() - 122) // (_CELL + _GAP)))

    def _build_calendar(self):
        today = date.today()
        weeks = self._week_count()
        if self._calendar_today == today and self._weeks_shown == weeks:
            return
        self._calendar_today = today
        self._weeks_shown = weeks
        title = f"Last {weeks} weeks"
        self.calendar_heading.setText(title)
        self.calendar_card.setAccessibleName(title)
        selected_button = self._cells.get(self._selected)
        had_focus = selected_button is not None and selected_button.hasFocus()
        self._cells.clear()
        self._cell_days.clear()
        while self.calendar_grid.count():
            item = self.calendar_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for row, day_name in enumerate(("M", "T", "W", "T", "F", "S", "S"), 1):
            label = QLabel(day_name)
            label.setAlignment(Qt.AlignCenter)
            self.calendar_grid.addWidget(label, row, 0)
        start = today - timedelta(days=today.weekday() + (weeks - 1) * 7)
        if self._selected < start:
            self._selected = today
        for week in range(weeks):
            monday = start + timedelta(weeks=week)
            month_start = next((monday + timedelta(days=offset) for offset in range(7)
                                if (monday + timedelta(days=offset)).day == 1), None)
            if week == 0 or month_start is not None:
                label = month_start or monday
                self.calendar_grid.addWidget(QLabel(label.strftime("%b")), 0, week + 1,
                                             1, min(2, weeks - week))
            for weekday in range(7):
                day = monday + timedelta(days=weekday)
                button = QToolButton()
                button.setFixedSize(_CELL, _CELL)
                button.setEnabled(day <= today)
                button.installEventFilter(self)
                button.clicked.connect(lambda _, selected=day: self._select_day(selected))
                self.calendar_grid.addWidget(button, weekday + 1, week + 1)
                self._cells[day] = button
                self._cell_days[button] = day
        if had_focus and self._selected in self._cells:
            self._cells[self._selected].setFocus()

    def eventFilter(self, watched, event):
        if watched in self._cell_days and event.type() == QEvent.KeyPress:
            step = {Qt.Key_Left: -7, Qt.Key_Right: 7, Qt.Key_Up: -1, Qt.Key_Down: 1}.get(event.key())
            if step is not None:
                target = self._cell_days[watched] + timedelta(days=step)
                if target in self._cells and self._cells[target].isEnabled():
                    self._select_day(target)
                    self._cells[target].setFocus()
                return True
        return super().eventFilter(watched, event)

    def _refresh_cells(self):
        for day, button in self._cells.items():
            summary = self._days.get(day)
            timed = summary and summary.get("measurement") == "time" and summary.get("seconds", 0) > 0
            legacy = summary and summary.get("measurement") == "legacy_samples"
            if timed:
                strength = min(1., max(.3, summary["seconds"] / 7200))
                base = self.palette().base().color()
                accent = QColor(theme.SHRIMP)
                color = QColor.fromRgbF(*(base.getRgbF()[i] * (1 - strength) +
                                         accent.getRgbF()[i] * strength for i in range(3)))
            else:
                color = self.palette().mid().color() if legacy else self.palette().midlight().color()
            border = "2px solid palette(text)" if day == self._selected else "1px solid palette(mid)"
            button.setFocusPolicy(Qt.StrongFocus if day == self._selected else Qt.ClickFocus)
            button.setStyleSheet(f"QToolButton {{ background: {color.name()}; border: {border}; border-radius: 4px; padding: 0; }}"
                                 "QToolButton:hover, QToolButton:focus { border-color: palette(text); }")
            button.setText("")
            detail = self._day_text(day, summary)
            description = f"{day:%A, %d %B %Y}: {detail}"
            button.setToolTip(description)
            button.setAccessibleName(description)

    def _day_text(self, day, summary):
        if not summary or summary.get("pct_good") is None:
            return "No observations"
        pct = summary["pct_good"]
        if summary["measurement"] == "legacy_samples":
            return f"{pct:.0f}% in calibrated range (older sample-based estimate)"
        seconds = summary.get("seconds", summary.get("minutes", 0) * 60)
        return f"{_duration(seconds)} monitored · {pct:.0f}% in calibrated range"

    def _select_day(self, day):
        self._selected = day
        self.selected_date.setText(day.strftime("%A, %d %B %Y"))
        self.day_detail.setText(self._day_text(day, self._days.get(day)))
        self._refresh_cells()

    def _manual_refresh(self):
        if self._refresh_timer.isActive():
            return
        self.refresh_button.setText("Refreshing…")
        self._refresh_timer.start(180)

    def _finish_manual_refresh(self):
        try:
            self.refresh()
        except Exception:
            self.refresh_button.setText("Retry")
        else:
            self.refresh_button.setText("Refresh")

    def refresh(self) -> None:
        self._build_calendar()
        days = [day for day in self.log.day_summaries(_WEEKS * 7)
                if "ts" in day and date.fromtimestamp(day["ts"]) in self._cells]
        self._days = {date.fromtimestamp(day["ts"]): day for day in days}
        self._refresh_cells()
        self.selected_date.setText(self._selected.strftime("%A, %d %B %Y"))
        self.day_detail.setText(self._day_text(self._selected, self._days.get(self._selected)))

        tracked = sum(day.get("pct_good") is not None for day in days)
        timed = [day for day in days if day.get("measurement") == "time"]
        total_s = sum(day.get("seconds", 0.) for day in timed)
        good_s = sum(day.get("good_s", 0.) for day in timed)
        self.tracked_days.setText(str(tracked))
        self.monitored_time.setText(_duration(total_s))
        self.in_range.setText(f"{good_s / total_s:.0%}" if total_s else "—")

        today = self._days.get(date.today())
        if today and today.get("pct_good") is not None:
            if today["measurement"] == "legacy_samples":
                self.today_lbl.setText(f"~{today['pct_good']:.0f}% in calibrated range (older sample-based estimate)")
            else:
                seconds = today.get("seconds", today.get("minutes", 0) * 60)
                self.today_lbl.setText(f"{_duration(seconds)} monitored · {today['pct_good']:.0f}% in calibrated range")
        else:
            self.today_lbl.setText(f"No observations in the last {self._weeks_shown} weeks. Start tracking to build your progress." if not any(
                day.get("pct_good") is not None for day in days) else "No monitored time today.")

        monday = date.today() - timedelta(days=date.today().weekday())
        week = [day for day in days if "ts" in day and date.fromtimestamp(day["ts"]) >= monday]
        good = sum(day.get("good_s", 0.) for day in week)
        drifting = sum(day.get("drifting_s", 0.) for day in week)
        bad = sum(day.get("bad_s", 0.) for day in week)
        total = good + drifting + bad
        self.mix.set_values((good, drifting, bad))
        self.mix.setAccessibleDescription(
            f"Comfortable {_duration(good)}, drifting {_duration(drifting)}, adjust {_duration(bad)}")
        for label, caption, seconds in zip(self.mix_values,
                                           ("Comfortable", "Drifting", "Adjust"),
                                           (good, drifting, bad)):
            label.setText(f"{caption}\n{_duration(seconds)}")
            label.setVisible(bool(total))
        if total:
            self.week_lbl.setText(f"{_duration(total)} monitored")
            self.mix_detail.setText("Older estimates excluded." if any(
                day.get("measurement") == "legacy_samples" for day in week) else "")
        else:
            self.week_lbl.setText("No monitored time yet")
            self.mix_detail.setText("Track posture to see this week's mix.")
        self.mix_detail.setVisible(bool(self.mix_detail.text()))
