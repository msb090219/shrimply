"""Posture history — SQLite at %APPDATA%\\Unshrimp\\log.db. Numbers only.

Timed rows store observed seconds per state. The original frame-based rows are
preserved separately as legacy estimates. Local days use calendar boundaries.
"""
from __future__ import annotations

import sqlite3
import math
import threading
import time
from datetime import date, timedelta
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at REAL NOT NULL,
    ended_at REAL
);
CREATE TABLE IF NOT EXISTS minute_rollup (
    minute_ts REAL PRIMARY KEY,   -- unix ts, floored to the minute
    scorable INTEGER NOT NULL,
    good INTEGER NOT NULL,
    drifting INTEGER NOT NULL,
    bad INTEGER NOT NULL,
    avg_dev REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS duration_rollup (
    minute_ts REAL PRIMARY KEY,
    good_s REAL NOT NULL,
    drifting_s REAL NOT NULL,
    bad_s REAL NOT NULL
);
"""


class PostureLog:
    def __init__(self, path: Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    # -- writes -----------------------------------------------------------
    def start_session(self, now: float | None = None) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO sessions (started_at) VALUES (?)",
                (now if now is not None else time.time(),),
            )
            return int(cur.lastrowid)

    def end_session(self, sid: int, now: float | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?",
                (now if now is not None else time.time(), sid),
            )

    def record_minute(
        self, minute_ts: float, scorable: int, good: int, drifting: int, bad: int, avg_dev: float
    ) -> None:
        if scorable <= 0:
            return
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO minute_rollup "
                "(minute_ts, scorable, good, drifting, bad, avg_dev) "
                "VALUES (?,?,?,?,?,?)",
                (minute_ts, scorable, good, drifting, bad, avg_dev),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def record_duration(self, minute_ts: float, good_s: float, drifting_s: float, bad_s: float) -> None:
        values = (good_s, drifting_s, bad_s)
        if not math.isfinite(minute_ts) or minute_ts % 60 != 0:
            raise ValueError("History timestamp must be a finite minute boundary")
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError("Observed durations must be finite and nonnegative")
        if sum(values) == 0:
            return
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO duration_rollup VALUES (?,?,?,?) "
                "ON CONFLICT(minute_ts) DO UPDATE SET "
                "good_s=good_s+excluded.good_s, "
                "drifting_s=drifting_s+excluded.drifting_s, "
                "bad_s=bad_s+excluded.bad_s",
                (minute_ts, *values),
            )

    # -- reads ------------------------------------------------------------
    def _rows_since(self, ts: float) -> list[tuple]:
        with self._lock:
            return self._conn.execute(
                "SELECT minute_ts, scorable, good, drifting, bad, avg_dev "
                "FROM minute_rollup WHERE minute_ts >= ? ORDER BY minute_ts",
                (ts,),
            ).fetchall()

    @staticmethod
    def _day_start(ts: float) -> float:
        lt = time.localtime(ts)
        return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))

    def day_summaries(self, days: int = 7) -> list[dict]:
        """Most recent `days` local days, oldest first (incl. empty days)."""
        today = date.fromtimestamp(time.time())
        buckets: dict[float, dict] = {}
        for i in range(days):
            day = today - timedelta(days=i)
            d0 = time.mktime((day.year, day.month, day.day, 0, 0, 0, 0, 0, -1))
            buckets[d0] = {"scorable": 0, "good": 0, "legacy_minutes": 0,
                           "seconds": 0., "good_s": 0., "drifting_s": 0., "bad_s": 0.}
        if not buckets:
            return []

        for minute_ts, scorable, good, _drift, _bad, avg_dev in self._rows_since(
            min(buckets)
        ):
            d0 = self._day_start(minute_ts)
            b = buckets.get(d0)
            if b is None or scorable <= 0:
                continue
            b["scorable"] += scorable
            b["good"] += good
            b["legacy_minutes"] += 1

        with self._lock:
            rows = self._conn.execute(
                "SELECT minute_ts, good_s, drifting_s, bad_s FROM duration_rollup "
                "WHERE minute_ts >= ? ORDER BY minute_ts", (min(buckets),),
            ).fetchall()
        for minute_ts, good_s, drifting_s, bad_s in rows:
            b = buckets.get(self._day_start(minute_ts))
            if b is not None:
                b["seconds"] += good_s + drifting_s + bad_s
                b["good_s"] += good_s
                b["drifting_s"] += drifting_s
                b["bad_s"] += bad_s

        out = []
        for d0 in sorted(buckets):
            b = buckets[d0]
            out.append(
                {
                    "date": time.strftime("%a", time.localtime(d0 + 3600)),
                    "ts": d0,
                    "minutes": b["seconds"] / 60 if b["seconds"] else b["legacy_minutes"],
                    "seconds": b["seconds"],
                    "good_s": b["good_s"],
                    "drifting_s": b["drifting_s"],
                    "bad_s": b["bad_s"],
                    "legacy_minutes": b["legacy_minutes"],
                    "measurement": "time" if b["seconds"] else "legacy_samples" if b["scorable"] else "none",
                    "pct_good": (100 * b["good_s"] / b["seconds"] if b["seconds"] else
                                 100 * b["good"] / b["scorable"] if b["scorable"] else None),
                }
            )
        return out

    def today(self) -> dict:
        return self.day_summaries(1)[0]
