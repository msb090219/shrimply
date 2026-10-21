"""Tests for shrimply.storage.db — minute rollups + day summaries."""
from __future__ import annotations

import time
import sqlite3

import pytest

from shrimply.storage.db import PostureLog


def mklog(tmp_path):
    return PostureLog(tmp_path / "log.db")


def test_minute_roundtrip(tmp_path):
    log = mklog(tmp_path)
    log.record_minute(1000 * 60, scorable=100, good=80, drifting=10, bad=10, avg_dev=0.9)
    # replace (same minute) rather than duplicate
    log.record_minute(1000 * 60, scorable=120, good=100, drifting=10, bad=10, avg_dev=0.8)
    log.record_minute(2000 * 60, scorable=0, good=0, drifting=0, bad=0, avg_dev=0.0)  # dropped
    rows = log._rows_since(0)
    assert len(rows) == 1
    assert rows[0][1] == 120 and rows[0][2] == 100
    log.close()


def test_today_and_week_summaries(tmp_path):
    log = mklog(tmp_path)
    now = time.time()
    # 20 minutes ago: 75% good
    for i in range(1, 4):
        m = int((now - i * 60) // 60)
        log.record_minute(m * 60, scorable=120, good=90, drifting=15, bad=15, avg_dev=1.0)
    # yesterday: 100% good for 5 minutes
    y0 = PostureLog._day_start(now) - 86400
    for i in range(5):
        log.record_minute(y0 + (i + 1) * 60, scorable=120, good=120, drifting=0, bad=0, avg_dev=0.2)

    today = log.today()
    assert today["pct_good"] == 75.0
    assert today["minutes"] == 3

    week = log.day_summaries(7)
    assert len(week) == 7
    assert week[-1]["pct_good"] == 75.0      # today is last
    assert week[-2]["pct_good"] == 100.0     # yesterday
    assert week[-2]["minutes"] == 5
    assert week[0]["pct_good"] is None       # empty days report None, not 0
    log.close()


def test_session_lifecycle(tmp_path):
    log = mklog(tmp_path)
    sid = log.start_session(100.0)
    log.end_session(sid, 200.0)
    with log._lock:
        row = log._conn.execute(
            "SELECT started_at, ended_at FROM sessions WHERE id=?", (sid,)
        ).fetchone()
    assert row == (100.0, 200.0)
    log.close()


def test_timed_records_are_additive_and_do_not_mix_with_legacy(tmp_path):
    path = tmp_path / "log.db"
    minute = int(time.time() // 60) * 60
    # Start with the original database layout, then open it using the new version.
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE minute_rollup (minute_ts REAL PRIMARY KEY, scorable INTEGER, "
                     "good INTEGER, drifting INTEGER, bad INTEGER, avg_dev REAL)")
        conn.execute("INSERT INTO minute_rollup VALUES (?,?,?,?,?,?)", (minute, 100, 100, 0, 0, 0.))
    log = PostureLog(path)
    assert log.today()["measurement"] == "legacy_samples"
    assert log.today()["pct_good"] == 100.
    log.record_duration(minute, 15., 0., 0.)
    log.close()
    log = PostureLog(path)
    log.record_duration(minute, 0., 0., 15.)
    day = log.today()
    assert day["measurement"] == "time"
    assert day["pct_good"] == 50.
    assert day["minutes"] == .5
    assert day["seconds"] == 30.
    assert (day["good_s"], day["drifting_s"], day["bad_s"]) == (15., 0., 15.)
    assert day["legacy_minutes"] == 1
    assert log._rows_since(0)[0][1:3] == (100, 100)
    log.close()


@pytest.mark.parametrize("seconds", [-1., float("nan"), float("inf")])
def test_invalid_durations_are_rejected(tmp_path, seconds):
    log = mklog(tmp_path)
    with pytest.raises(ValueError):
        log.record_duration(6000., seconds, 0., 0.)
    log.close()


def test_local_calendar_days_survive_a_23_hour_day(tmp_path, monkeypatch):
    """Simulate NZ's spring clock change without changing the machine timezone."""
    from datetime import date, datetime, timezone
    import shrimply.storage.db as db_module

    class LocalDate(date):
        @classmethod
        def fromtimestamp(cls, _):
            return cls(2026, 9, 29)

    def midnight(parts):
        year, month, day = parts[:3]
        offset = 13 if (year, month, day) >= (2026, 9, 28) else 12
        return datetime(year, month, day, tzinfo=timezone.utc).timestamp() - offset * 3600

    boundaries = [midnight((2026, 9, day)) for day in (27, 28, 29)]
    assert boundaries[1] - boundaries[0] == 23 * 3600
    monkeypatch.setattr(db_module, "date", LocalDate)
    monkeypatch.setattr(db_module.time, "mktime", midnight)
    monkeypatch.setattr(PostureLog, "_day_start", staticmethod(
        lambda stamp: max(boundary for boundary in boundaries if boundary <= stamp)))
    log = mklog(tmp_path)
    for boundary in boundaries:
        log.record_duration(boundary + 60, 30., 0., 0.)
    days = log.day_summaries(3)
    assert [day["ts"] for day in days] == boundaries
    assert [day["seconds"] for day in days] == [30., 30., 30.]
    log.close()
