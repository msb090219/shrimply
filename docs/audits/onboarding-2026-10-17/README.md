# First-run onboarding and calibration handoff

The later [shrimp feedback update](../shrimp-feedback-2026-10-17/README.md)
adds visual countdowns and revises preview-only camera behavior.

The welcome window now explains camera framing, setup duration, the purpose of
each pose, and local camera processing. Later (including Escape or the title-bar
close button) leaves tracking paused. The calibration window stays in front when
setup starts instead of being covered by the main window.

Tall measures the upright range; normal is the everyday reference; a comfortable
slouch provides the contrast. Guidance explains this without changing capture
durations, calibration validation, or scoring formulas.

After the first desktop walkthrough, the user reported that instructions were
too small and competed with technical details. The revision places a 24 px pose
title and 16 px preparation/capture status above the scrolling mirror. Short
pose guidance stays visible there too. Camera setup details are collapsed by
default and revealed automatically if setup gets stuck. Clicking Calibrate still
starts the automatic flow; there are no extra readiness buttons between poses.

After a successful save, the mirror is cleared and hidden, tracking is paused,
and the normal worker shutdown releases the camera asynchronously. The result
offers optional How it works content explaining the posture indicator, an example
shrimp cue, and existing break actions. Start tracking resumes capture and opens
the main window.
Later or closing the result leaves tracking paused, including across restarts.
Existing users can recalibrate to see this result; their welcome preference and
saved baseline are not reset to force onboarding to repeat.

Failed calibration retains the existing Retry/Close flow and previous baseline.
Cancellation still restores the pre-calibration pause state. Settings remain the
place to change reminder and appearance options; onboarding adds no preferences.

## Captures

- [Welcome](01-welcome.png), [compact welcome](02-welcome-compact.png)
- [Tall](03-tall.png), [normal](03-normal.png), [comfortable slouch](03-hunch.png)
- [Camera setup](03-setup.png), [optional setup details](03-setup-details.png)
- [Ready to track](04-ready.png), [compact result](05-ready-compact.png)
- [Optional explanation](04-how-it-works.png)
- [Retry](06-retry-compact.png), [camera error](06-camera-error-compact.png), [About](07-about.png)

## Verification

- Full suite: **376 tests pass**. New checks cover the saved-baseline/pause/start
  handoff, guarded Start action, deferred setup, startup focus routing, result
  actions, failure state, and Enter/Escape in the welcome dialog. The simplified
  screen also checks optional details, pinned instructions during scrolling,
  readable countdowns, and preservation of actionable interruption/error guidance.
- Thirteen real-widget layouts at each of 100%, 150%, and 200% Qt scaling:
  **39 checks pass** for minimum button sizes, wrapped label heights, and hidden
  horizontal overflow. Representative welcome, pose, and result renders were
  visually inspected. Compact layouts use vertical scrolling.
- [100% layout report](layout-report.json),
  [150% report](../../../diagnostics/onboarding-scale-1.5/layout-report.json),
  [200% report](../../../diagnostics/onboarding-scale-2/layout-report.json).
- Windows executable and ZIP rebuilt. Packaged icon/image plugins, both models,
  and native inference smoke checks passed:
  [result](../../../diagnostics/calibration-simplified-package-smoke-2026-10-17.json).

Capture uses Qt offscreen with synthetic states, no camera, and no user settings
or history writes. These checks do not establish live calibration success,
camera-indicator timing after completion, first-user comprehension, screen-reader
behavior, or native Windows/mixed-monitor DPI transitions. Those need a desktop
walkthrough.

Reproduce screenshots from the repository root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
$env:QT_QPA_FONTDIR = 'C:\Windows\Fonts'
$env:QT_SCALE_FACTOR = '1'
.\.venv\Scripts\python.exe docs/audits/onboarding-2026-10-17/capture.py
```
