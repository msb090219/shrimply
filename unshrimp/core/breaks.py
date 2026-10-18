"""Session-local break reminders measured in observed presence, not wall time."""
from __future__ import annotations


class BreakReminder:
    MAX_GAP_S = 2.5
    SNOOZE_S = 5 * 60
    BREAK_S = 2 * 60

    def __init__(self, enabled: bool, interval_s: float, break_s: float = BREAK_S):
        self.enabled = enabled
        self.interval_s = interval_s
        self.break_s = break_s
        self.elapsed = 0.0
        self.target = interval_s
        self.pending = False
        self.snoozed = False
        self._last: float | None = None
        self._break_until: float | None = None

    @property
    def in_break(self) -> bool:
        return self._break_until is not None

    def break_remaining(self, now: float) -> float:
        return max(0.0, self._break_until - now) if self.in_break else 0.0

    def tick(self, now: float) -> None:
        if self.in_break and now >= self._break_until:
            self.end_break()

    @property
    def remaining(self) -> float:
        return max(0.0, self.target - self.elapsed)

    def pause(self) -> None:
        """Break continuity without discarding already observed sitting time."""
        self._last = None

    def recently_present(self, now: float) -> bool:
        return self._last is not None and 0 <= now - self._last <= self.MAX_GAP_S

    def configure(self, enabled: bool, interval_s: float, break_s: float | None = None) -> None:
        if break_s is not None:
            self.break_s = break_s
        if (enabled, interval_s) == (self.enabled, self.interval_s):
            return
        self.enabled, self.interval_s = enabled, interval_s
        self.pending = self.snoozed = False
        self.target = interval_s
        self.pause()
        if not enabled:
            self.elapsed = 0.0
            self._break_until = None

    def observe(self, present: bool, now: float) -> bool:
        """Return True only when a new reminder becomes due."""
        self.tick(now)
        if self.in_break:
            self.pause()
            return False
        if not self.enabled or not present:
            self.pause()
            return False
        previous, self._last = self._last, now
        if not self.pending and previous is not None:
            delta = now - previous
            if 0 < delta <= self.MAX_GAP_S:
                self.elapsed += delta
        if not self.pending and self.elapsed >= self.target:
            self.pending = True
            return True
        return False

    def take_break(self, now: float) -> None:
        if not self.enabled or self.in_break:
            return
        self._break_until = now + self.break_s
        self.pending = self.snoozed = False
        self.pause()

    def end_break(self) -> None:
        self._break_until = None
        self.elapsed = 0.0
        self.target = self.interval_s
        self.pending = self.snoozed = False
        self.pause()

    def snooze(self, delay_s: float = SNOOZE_S) -> None:
        if self.in_break:
            return
        self.pending = False
        self.snoozed = True
        self.target = self.elapsed + delay_s
        self.pause()

    def skip(self) -> None:
        if self.in_break:
            return
        self.elapsed = 0.0
        self.target = self.interval_s
        self.pending = self.snoozed = False
        self.pause()
