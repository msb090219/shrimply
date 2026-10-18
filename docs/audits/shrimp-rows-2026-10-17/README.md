# Fixed shrimp rows — 17 October 2026

This replaces the preceding compact rising-shrimp design with the user's intended
segmented meter, and keeps the calibration row consistent across every stage.

## Behavior

- The draggable HUD has ten stationary shrimp. Their fixed colors run from green
  through amber to red. More segments light up as the existing deviation rises;
  the final red segment lights at the existing Adjust posture threshold (1.5).
  A usable zero reading lights the first green shrimp. Unknown or non-scoring
  states leave all ten gray. The text and controls retain fixed positions.
  Startup clamps a saved edge position to the monitor so the wider row does not
  leave its controls off-screen.
- Calibration always displays twelve slots, including setup and completion.
  An eight-second capture starts with eight colored and four gray shrimp; a
  twelve-second capture uses all twelve. Consumed seconds return their slots to
  gray rather than removing the shrimp. Every slot keeps the same position.
- Preparation retains the blue wave over the slots used for that pose. The numeric
  preparation countdown remains separate. Unused trailing slots stay gray.
- Capture remains driven by usable observation time, with interruption/extension
  behavior preserved. Reduce motion disables the wave/fades. The compact meter
  changes instantly and has no animation timer; the separate desktop shrimp is
  unaffected by this display correction.

No calibration/scoring formulas, camera policy, or saved baseline were changed.

## Verification and captures

Full suite: **406 tests pass**. Updated checks cover ordered gradient fill,
unknown/paused states, fixed twelve-slot preparation/capture/setup, all nominal
durations, unchanged dimensions, stopped cosmetic timers after clearing, and
saved HUD positions overlapping the right, left, and bottom screen edges.

Sixteen real-widget layouts at 100%, 150%, and 200% Qt scaling passed:
**48 layout checks**, with no undersized controls, clipped wrapped labels, or hidden
horizontal overflow. Representative meter/setup/eight-second/twelve-second renders
were visually inspected. The HUD remains 40 logical pixels tall; its width is
479 logical pixels with the test font, fixed across states.

- [Meter low](10-hud-low.png), [middle](10-hud-middle.png), [high](11-hud-high.png),
  [unknown](12-hud-unknown.png)
- [Neutral setup](00-setup-neutral.png), [preparation](01-prepare.png)
- [Eight seconds](02-eight-start.png), [five seconds remaining](02-capture.png)
- [Twelve seconds](04-verify-compact.png), [completion](13-complete.png)
- [100% report](layout-report.json),
  [150% report](../../../diagnostics/shrimp-rows-scale-150/layout-report.json),
  [200% report](../../../diagnostics/shrimp-rows-scale-200/layout-report.json)

Renders use synthetic state in offscreen Qt and save no webcam images. Reproduce
using `docs/audits/shrimp-feedback-2026-10-17/capture.py OUTPUT_DIRECTORY` with the
existing Python environment and offscreen Qt settings.

The Windows executable and ZIP were rebuilt. The packaged icon/image plugins,
both models, and native inference smoke checks passed. The packaged HUD,
countdown, and controller modules match the tested source, including placement.

- [Packaged resource check](../../../diagnostics/shrimp-rows-package-smoke-2026-10-17.json)
- [Packaged source match](../../../diagnostics/shrimp-rows-package-match-2026-10-17.json)

Live readability and native mixed-monitor DPI behavior still need observation.
Camera lifecycle was not retested for this visual correction; its prior results
are in the [camera/motion report](../shrimp-feedback-2026-10-17/README.md).
