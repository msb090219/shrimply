# Camera modes and shrimp feedback — 17 October 2026

The subsequent [fixed-row correction](../shrimp-rows-2026-10-17/README.md)
replaces the compact rising shrimp with a gradient row and keeps twelve
calibration slots visible across stages. The captures below describe this earlier pass.

## Behavior

- Explicit preview can use the camera while normal posture tracking is paused.
  This is capture-only: no landmark models, posture scoring, history, or detected
  sitting time. Closing preview releases capture if tracking is paused or idle.
- One worker owns the camera. Switching between capture-only and inference waits
  for the old worker to finish. Opening/closing the mirror during normal tracking
  changes preview delivery without resetting scoring continuity.
- Calibration suspends the posture state machine and its alert clocks without
  changing the saved manual pause preference. Only calibration receives samples.
  Cancellation retains the prior baseline and restores prior tracking intent.
  Success saves both the baseline and paused preference, then offers Start tracking.
- Camera loss clears the mirror; Retry and sleep/wake follow the shared camera
  policy. Calibration, paused preview, and ordinary tracking have distinct status.
- Large pose text stays above the mirror. A stationary row of shrimp shows a blue
  preparation wave, then fades one shrimp per completed usable second. Text and
  numeric time remain visible. Tracking loss freezes progress. Extra tall-pose
  collection shows a quality-check state rather than false completion.
- The compact HUD replaces its dot with a small shrimp that rises with deviation.
  Its label and controls keep fixed positions. Missing readings and non-scoring
  states show a neutral shrimp. The separate desktop shrimp remains available.
- Appearance → Reduce motion disables the preparation wave and decorative bobbing,
  makes compact shrimp position changes immediate, and preserves static progress.
  Existing bobbing preferences are retained when reduced motion is switched off.

No new dependencies or scoring/validation thresholds were introduced.

## Captures and automated motion checks

- [Preparation](01-prepare.png), [capture](02-capture.png), [tracking loss](03-paused.png)
- [Twelve-second verification at compact size](04-verify-compact.png)
- [Extended quality collection](05-extra-quality.png), [camera error](06-camera-error.png)
- [Preview only](07-preview-only.png), [Main with paused preview](08-main-paused-preview.png)
- [Appearance](09-appearance.png), [low HUD](10-hud-low.png), [high HUD](11-hud-high.png),
  [unknown HUD](12-hud-unknown.png), [completion](13-complete.png)

Thirteen real-widget layouts at each of 100%, 150%, and 200% Qt scaling passed:
**39 measurements** with no undersized buttons, clipped wrapped labels, or hidden
horizontal overflow. Representative renders were visually inspected. Small
windows scroll details vertically while instructions/actions remain visible.
Motion assertions confirmed that preparation frames change without reducing the
observed-time countdown, reduced-motion frames stay static, the HUD shrimp moves
between readings, and hiding the HUD stops its animation.

- [100% layout/motion report](layout-report.json)
- [150% report](../../../diagnostics/shrimp-feedback-scale-150/layout-report.json)
- [200% report](../../../diagnostics/shrimp-feedback-scale-200/layout-report.json)

These renders use synthetic state in offscreen Qt, with no webcam or user-data
writes. Run `capture.py OUTPUT_DIRECTORY` from the repository root with the
existing Python environment; set `QT_QPA_PLATFORM=offscreen`,
`QT_QPA_FONTDIR=C:\Windows\Fonts`, and `QT_SCALE_FACTOR=1`, `1.5`, or `2`.

## Regression and hardware results

Full regression suite: **402 tests pass**. Coverage includes camera policy,
capture-only model exclusion, serialization, stale signals, cancelled reopen,
calibration sample routing, alert-clock exclusion, usable-time metadata,
interruption/extension, motion cleanup, HUD controls, and saved motion preference.

Real camera 0 verification used an isolated source Qt host and the bundled models.
All ten relevant source modules matched code extracted from the built executable.
The following passed:

- Preview delivered real images while paused, without emitting inference frames.
- Calibration received real inference while normal tracking stayed paused and
  history/sitting time remained empty. Cancelling restored the paused state.
- The tracking camera mode and shared camera status recovered after starting tracking.
- Closing active preview cleared its image while tracking continued.
- Unavailable camera 9999 exposed Retry; restoring camera 0 recovered capture.
- Two pauses with the mirror open switched to capture-only preview. Closing the
  mirror released capture in **264.4 ms** and **260.1 ms** respectively.

[Live camera report](../../../diagnostics/shrimp-feedback-camera-verification-2026-10-17.json)

Windows executable and ZIP were rebuilt. Packaged icon/image plugins, both models,
and synthetic native inference smoke checks passed.
[Packaged smoke result](../../../diagnostics/shrimp-feedback-package-smoke-2026-10-17.json)

The camera diagnostic saves counts/timings, not images or video. Its temporary
settings/history are removed afterward; it does not reset the user's calibration.
Those isolated settings contain no saved baseline, so resumed scored-history
accuracy is outside this hardware pass. Controller tests use a saved baseline to
check that calibration cannot enter normal scoring/history or count alert time.

## Still needs desktop observation

Complete calibration through every pose, countdown comprehension/readability,
physical camera-indicator timing, real sleep/wake with preview-only capture,
screen-reader behavior, and native mixed-monitor DPI transitions need a walkthrough.
The source-host test and packaged code comparison do not replace those checks.
