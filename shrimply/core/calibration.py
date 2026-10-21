"""Guided calibration pipeline (v3) — pure logic, no Qt.

Five phases: setup → tall → normal → hunch → verify → done|failed.
Feed one FrameSignals + timestamp per tick; StepResult drives the UI
(HUD text, toasts, the Continue-anyway escape hatch).

Design notes:
- The setup phase validates the *camera* before trusting any capture:
  level (roll), height vs. gaze (pitch at screen-center), framing
  distance (shoulder width), lighting, and person presence.
- Captures gate on yaw/roll so half-turned frames never enter a sample,
  and reject per-signal outliers with a MAD filter so one shrug doesn't
  skew the median.
- The "normal" phase measures everyday posture and becomes the scoring
  ANCHOR: green means "at least as good as your normal sitting", and the
  hunch sample sets the distance to red. This keeps users whose habit is
  already partway hunched (very common with FHP) from being told their
  slouch is good — and users with a mild hunch from being nagged at normal.
- The verify phase scores the fresh baseline against the user's normal
  sitting and self-tunes until normal reads green. This is the "prove it
  before you use it" step.
"""
from __future__ import annotations

import statistics
import math
from dataclasses import dataclass, field, replace

from ..vision.metrics import FrameSignals
from .baseline import (
    FLOOR_MIN,
    HUNCH_MIN_DELTA,
    SIGMA_MULT,
    SIGNALS,
    TOL_FLOOR,
    Baseline,
    SignalCal,
    fresh_timestamp,
)

# --- setup phase ----------------------------------------------------------
SETUP_PASS_S = 6.0  # all checks must pass this long, continuously
SETUP_STUCK_S = 15.0  # before this, failing checks are just guidance
MAX_ROLL_DEG = 8.0
MAX_PITCH_DEG = 10.0
MIN_SHOULDER_W = 0.08
LUM_MIN, LUM_MAX = 40.0, 220.0

# --- capture phases -------------------------------------------------------
GATE_YAW_DEG = 12.0
GATE_ROLL_DEG = 8.0
TALL_S, TALL_MAX_S = 10.0, 15.0  # nominal, with outlier-driven extension
NORMAL_S = 8.0
HUNCH_S = 6.0
VERIFY_S = 12.0
REJECT_RATIO_MAX = 0.30  # above this (and under TALL_MAX_S), keep collecting
MIN_CLEAN = 3  # per-signal minimum after outlier filtering
PREPARE_S = 3.0

# absolute floors for the MAD threshold, so a perfectly still capture
# (MAD=0) still tolerates measurement granularity
MAD_ABS = {"head_pitch": 1.5, "head_sink": 0.01, "lean_in": 0.005}

# --- verify phase ---------------------------------------------------------
VERIFY_TRIGGER = 0.5  # median deviation above this → auto-tune
VERIFY_TARGET = 0.3  # tune until normal reads ~this
TUNE_CAP = 2.5
VERIFY_FAIL = 1.0  # still above this after tuning → calibration rejected

# when anchored at normal, "red" (dev 1.75) sits at the measured hunch
HUNCH_DEV = 1.75

CHECK_ORDER = ("present", "level", "gaze", "framing", "light")


@dataclass
class StepResult:
    phase: str  # setup|tall|normal|hunch|verify|done|failed
    progress: str = ""  # HUD text
    hint: str | None = None  # longer guidance for the current failing check
    events: list[str] = field(default_factory=list)
    baseline: Baseline | None = None
    activity: str | None = None
    elapsed_s: float = 0.0
    duration_s: float = 0.0
    pose_duration_s: float = 0.0


def _mad_filter(values: list[float], abs_floor: float) -> list[float]:
    """Keep values within 2×MAD of the median (robust to spikes)."""
    if not values:
        return []
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values])
    thr = max(2.0 * mad, abs_floor)
    return [v for v in values if abs(v - med) <= thr]


class CalibrationSession:
    def __init__(self, *, prepare_s: float = PREPARE_S):
        self.phase = "setup"
        self.setup_report: dict = {c: False for c in CHECK_ORDER}
        self.degraded = False  # True if setup was skipped via Continue anyway

        self._t0 = 0.0  # phase start (set on first feed)
        self._streak_t0: float | None = None
        self._stuck_announced = False
        self._first = True
        self._prepare_s = prepare_s
        self._prepared = 0.0
        self._last_capture_tick: float | None = None
        self._last_setup_tick: float | None = None
        self._capture_clock = 0.0

        self._tall: dict[str, list[float]] = {k: [] for k in SIGNALS}
        self._tall_total = 0
        self._normal: dict[str, list[float]] = {k: [] for k in SIGNALS}
        self._hunch: dict[str, list[float]] = {k: [] for k in SIGNALS}
        self._verify_devs: list[float] = []
        self._verify_times: list[float] = []
        self._candidate: Baseline | None = None

    # ------------------------------------------------------------------
    def feed(self, sig: FrameSignals, now: float) -> StepResult:
        return self._with_timing(self._feed(sig, now))

    def _with_timing(self, result: StepResult) -> StepResult:
        durations = {"tall": TALL_S, "normal": NORMAL_S, "hunch": HUNCH_S, "verify": VERIFY_S}
        duration = durations.get(result.phase)
        if duration is None:
            return result
        preparing = self._prepared < self._prepare_s
        elapsed = self._prepared if preparing else max(0., self._capture_clock - self._t0)
        activity = ("paused" if result.progress == "Collection paused" else
                    "preparing" if preparing else
                    "checking" if elapsed >= duration else "capturing")
        return replace(result, activity=activity, elapsed_s=elapsed,
                       duration_s=self._prepare_s if preparing else duration,
                       pose_duration_s=duration)

    def _feed(self, sig: FrameSignals, now: float) -> StepResult:
        if self._first:
            self._t0 = now
            self._first = False
        if self.phase == "setup":
            return self._setup(sig, now)
        if self.phase in ("tall", "normal", "hunch", "verify"):
            previous = self._last_capture_tick
            self._last_capture_tick = now if self._gated(sig) else None
            if not self._gated(sig):
                hint = ("Keep your face and shoulders visible in the preview."
                        if not sig.ok else "Face the camera and keep your head level.")
                return StepResult(self.phase, "Collection paused", hint)
            # Never count an unseen interval, including stalled camera delivery.
            delta = now - previous if previous is not None else 0.0
            delta = delta if 0 <= delta <= 2.0 else 0.0
            if self._prepared < self._prepare_s:
                self._prepared = min(self._prepare_s, self._prepared + delta)
                return StepResult(self.phase,
                                  (f"Get ready · {math.ceil(self._prepare_s - self._prepared)}s"
                                   if self._prepared < self._prepare_s else "Ready to collect"),
                                  "Settle into this pose. No samples are being collected yet.")
            self._capture_clock += delta
            now = self._capture_clock
        if self.phase == "tall":
            return self._tall_step(sig, now)
        if self.phase == "normal":
            return self._normal_step(sig, now)
        if self.phase == "hunch":
            return self._hunch_step(sig, now)
        if self.phase == "verify":
            return self._verify_step(sig, now)
        return StepResult(self.phase, baseline=self._candidate)

    def force_continue(self, now: float) -> StepResult:
        """Escape hatch from a stuck setup: record warnings, move on."""
        if self.phase != "setup":
            return StepResult(self.phase)
        self.degraded = True
        self._enter("tall", now)
        return self._with_timing(StepResult("tall", self._ready_progress("TALL"), events=["enter_tall"]))

    def _ready_progress(self, label: str) -> str:
        return f"Get ready · {self._prepare_s:g}s" if self._prepare_s else f"{label} 0s"

    # ------------------------------------------------------------------
    def _enter(self, phase: str, now: float) -> None:
        self.phase = phase
        self._first = False
        self._t0 = now
        self._streak_t0 = None
        self._prepared = 0.0
        self._last_capture_tick = None
        self._capture_clock = now

    @staticmethod
    def _gated(sig: FrameSignals) -> bool:
        return (
            sig.ok
            and sig.head_yaw is not None
            and abs(sig.head_yaw) <= GATE_YAW_DEG
            and sig.head_roll is not None
            and abs(sig.head_roll) <= GATE_ROLL_DEG
        )

    # --- phase 0: setup ---------------------------------------------------
    def _checks(self, sig: FrameSignals) -> dict[str, bool]:
        c = {k: False for k in CHECK_ORDER}
        if sig.ok and sig.shoulder_w is not None:
            c["present"] = True
            if sig.head_roll is not None:
                c["level"] = abs(sig.head_roll) <= MAX_ROLL_DEG
            if sig.head_pitch is not None:
                c["gaze"] = abs(sig.head_pitch) <= MAX_PITCH_DEG
            c["framing"] = sig.shoulder_w >= MIN_SHOULDER_W
        if sig.luminance is not None:
            c["light"] = LUM_MIN <= sig.luminance <= LUM_MAX
        return c

    @staticmethod
    def _check_hint(failing: str, sig: FrameSignals) -> str:
        if failing == "present":
            return "can't see you — face the camera"
        if failing == "level":
            return f"tilted {sig.head_roll:+.0f}° — level the camera (or your head)"
        if failing == "gaze":
            if sig.head_pitch > 0:  # positive pitch = looking down
                return "you look DOWN at the camera — raise it toward eye level"
            return "you look UP at the camera — lower it toward eye level"
        if failing == "framing":
            return "sit closer — need more torso in frame"
        return "too dark — turn a light on" if (sig.luminance or 0) < LUM_MIN else "too bright"

    def _setup(self, sig: FrameSignals, now: float) -> StepResult:
        events: list[str] = []
        if self._last_setup_tick is not None and not 0 <= now - self._last_setup_tick <= 2.0:
            self._streak_t0 = None
        self._last_setup_tick = now
        checks = self._checks(sig)
        self.setup_report.update(checks)

        if all(checks.values()):
            if self._streak_t0 is None:
                self._streak_t0 = now
            if now - self._streak_t0 >= SETUP_PASS_S:
                self._enter("tall", now)
                return StepResult(
                    "tall", self._ready_progress("TALL"),
                    events=["enter_tall", "setup_ok"],
                )
        else:
            self._streak_t0 = None

        elapsed = now - self._t0
        if elapsed > SETUP_STUCK_S and not self._stuck_announced:
            self._stuck_announced = True
            events.append("setup_stuck")

        failing = [k for k in CHECK_ORDER if not checks[k]]
        if not failing:
            return StepResult("setup", f"all ✓ {max(0, SETUP_PASS_S - (now - (self._streak_t0 or now))):.0f}s",
                              events=events)
        hint = self._check_hint(failing[0], sig)
        return StepResult("setup", f"{len(CHECK_ORDER) - len(failing)}/{len(CHECK_ORDER)} · {failing[0]} ✗",
                          hint, events)

    # --- phase 1: tall ------------------------------------------------------
    def _tall_step(self, sig: FrameSignals, now: float) -> StepResult:
        elapsed = now - self._t0
        if self._gated(sig):
            self._tall_total += 1
            for k in SIGNALS:
                self._tall[k].append(getattr(sig, k))

        filtered = {k: _mad_filter(self._tall[k], MAD_ABS[k]) for k in SIGNALS}
        rejected = self._tall_total - min(len(v) for v in filtered.values())
        ratio = rejected / self._tall_total if self._tall_total else 0.0

        if elapsed >= TALL_S and (ratio <= REJECT_RATIO_MAX or elapsed >= TALL_MAX_S):
            if min(len(v) for v in filtered.values()) < MIN_CLEAN:
                return self._fail("too_few", "couldn't get a clean read — hold steadier")
            self._tall = filtered
            self._enter("normal", now)
            return StepResult("normal", self._ready_progress("NORMAL"), events=["enter_normal"])

        hint = "hold steady…" if ratio > REJECT_RATIO_MAX else None
        return StepResult("tall", f"TALL {min(int(elapsed), int(TALL_S))}/{int(TALL_S)}s", hint)

    # --- phase 2: normal ----------------------------------------------------
    def _normal_step(self, sig: FrameSignals, now: float) -> StepResult:
        if self._gated(sig):
            for k in SIGNALS:
                self._normal[k].append(getattr(sig, k))
        if now - self._t0 >= NORMAL_S:
            if min(len(v) for v in self._normal.values()) < MIN_CLEAN:
                return self._fail("too_few", "couldn't see you enough")
            self._enter("hunch", now)
            return StepResult("hunch", self._ready_progress("HUNCH"), events=["enter_hunch"])
        return StepResult("normal", f"NORMAL {int(now - self._t0)}/{int(NORMAL_S)}s")

    # --- phase 3: hunch + candidate build ------------------------------------
    def _hunch_step(self, sig: FrameSignals, now: float) -> StepResult:
        if self._gated(sig):
            for k in SIGNALS:
                self._hunch[k].append(getattr(sig, k))
        if now - self._t0 < HUNCH_S:
            return StepResult("hunch", f"HUNCH {int(now - self._t0)}/{int(HUNCH_S)}s")

        if min(len(v) for v in self._hunch.values()) < MIN_CLEAN:
            return self._fail("too_few", "couldn't see you enough")

        signals: dict[str, SignalCal] = {}
        anchors: dict[str, str] = {}
        for k in SIGNALS:
            t_med = statistics.median(self._tall[k])
            n_med = statistics.median(self._normal[k])
            h_med = statistics.median(self._hunch[k])
            sigma = statistics.stdev(self._tall[k]) if len(self._tall[k]) >= 2 else 0.0
            delta = h_med - t_med

            if abs(delta) < HUNCH_MIN_DELTA[k]:
                # hunch looked like tall — no direction to learn
                bad_dir, value, tol = 0, t_med, TOL_FLOOR[k]
                anchors[k] = "excluded"
            elif delta * (h_med - n_med) < 0:
                bad_dir, value, tol = 0, t_med, TOL_FLOOR[k]
                anchors[k] = "excluded"
            elif abs(h_med - n_med) >= HUNCH_MIN_DELTA[k]:
                # anchor at NORMAL: green = at least your everyday posture,
                # red = approaching your measured hunch
                bad_dir = 1 if delta > 0 else -1
                value = n_med
                tol = max(abs(h_med - n_med) / HUNCH_DEV, FLOOR_MIN[k])
                anchors[k] = "normal"
            else:
                # hunch ≈ normal on this signal (habit ≈ slouch) — anchor at
                # tall with the generous floor so everyday jitter stays green
                bad_dir = 1 if delta > 0 else -1
                value = t_med
                tol = max(TOL_FLOOR[k], SIGMA_MULT * sigma)
                anchors[k] = "tall"
            signals[k] = SignalCal(value=value, tol=tol, bad_dir=bad_dir)

        if all(c.bad_dir == 0 for c in signals.values()):
            return self._fail(
                "flat_hunch",
                "your hunch looked the same as your tall pose — exaggerate the slouch",
            )

        self._candidate = Baseline(
            signals=signals,
            created_at=fresh_timestamp(),
            report={
                "setup": dict(self.setup_report),
                "degraded": self.degraded,
                "anchor": anchors,
            },
        )
        self._enter("verify", now)
        return StepResult("verify", self._ready_progress("CHECK"), events=["enter_verify"])

    # --- phase 4: verify + auto-tune -----------------------------------------
    def _verify_step(self, sig: FrameSignals, now: float) -> StepResult:
        assert self._candidate is not None
        if self._gated(sig):
            dev = self._candidate.deviation(sig)
            if dev is not None:
                self._verify_devs.append(dev)
                self._verify_times.append(now)
        if now - self._t0 < VERIFY_S:
            return StepResult("verify", f"CHECK {int(now - self._t0)}/{int(VERIFY_S)}s")

        if (len(self._verify_devs) < MIN_CLEAN
                or self._verify_times[-1] - self._verify_times[0] < VERIFY_S * 0.75
                or self._verify_times[0] - self._t0 > 2.0
                or now - self._verify_times[-1] > 2.0
                or any(b - a > 2.0 for a, b in zip(self._verify_times, self._verify_times[1:]))):
            return self._fail("too_few", "couldn't see you enough")

        med = statistics.median(self._verify_devs)
        tune = 1.0
        if med > VERIFY_TRIGGER:
            tune = min(med / VERIFY_TARGET, TUNE_CAP)
        hunch = replace(sig, ok=True, **{
            k: statistics.median(self._hunch[k]) for k in SIGNALS
        })
        hunch_dev = self._candidate.deviation(hunch)
        if hunch_dev < 1.5:
            return self._fail(
                "separation", "normal and hunched posture are too similar; repeat calibration",
            )
        tune = min(tune, hunch_dev / 1.5)
        for cal in self._candidate.signals.values():
            cal.tol *= tune

        if med / tune > VERIFY_FAIL:
            return self._fail(
                "verify",
                "your normal sitting still reads hunched — check camera setup "
                "and recalibrate (sit honestly tall, not heroically)",
            )

        self._candidate.report = {
            **self._candidate.report,
            "tune": round(tune, 2),
            "verify_median": round(med, 2),
        }
        self.phase = "done"
        return StepResult("done", "done", events=["calibrated"], baseline=self._candidate)

    # ------------------------------------------------------------------
    def _fail(self, code: str, hint: str) -> StepResult:
        self.phase = "failed"
        return StepResult("failed", hint=hint, events=[f"failed:{code}"])
