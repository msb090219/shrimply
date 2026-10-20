"""Elapsed observed posture time, split at wall-clock minute boundaries."""
from __future__ import annotations


class HistoryAccumulator:
    def __init__(self):
        self.minutes: dict[int, dict[str, float]] = {}
        self._last: tuple[str, float, float] | None = None

    def reset(self) -> None:
        """Break continuity without discarding already observed time."""
        self._last = None

    def push(self, state: str | None, now: float, wall: float) -> None:
        if state not in ("good", "drifting", "bad"):
            self.reset()
            return
        previous = self._last
        self._last = (state, now, wall)
        if previous is None:
            return
        old_state, old_now, old_wall = previous
        elapsed, wall_elapsed = now - old_now, wall - old_wall
        # Never bridge tracking loss, suspend, or a wall-clock adjustment.
        if not (0 < elapsed <= 2.5 and wall_elapsed > 0
                and abs(wall_elapsed - elapsed) < 1.0):
            return
        cursor = old_wall
        while cursor < wall:
            minute = int(cursor // 60) * 60
            end = min(wall, minute + 60)
            seconds = (end - cursor) * elapsed / wall_elapsed
            bucket = self.minutes.setdefault(minute, {"good": 0., "drifting": 0., "bad": 0.})
            # Each bounded interval belongs to the last observed state.
            bucket[old_state] += seconds
            cursor = end
