# Settings refinement — 18 October 2026

Layout superseded by the [restored boxed/single-column layout](../settings-restored-2026-10-18/README.md)
after user feedback. Behavioral changes below remain; the borderless/side-by-side
design is no longer current.

Implemented the [approved page plan](../../SETTINGS-REFINEMENT-PLAN.md).

- Automatic saving with Done; edited-field patches preserve newer runtime state.
  Slider drags preview locally and commit on release/focus departure/task actions.
  Failed saves restore controls and keep a visible inline error. Startup uses the
  existing OS/persistence rollback path. Suggestion edits commit individually.
- Camera and Calibration first, then Sensitivity and collapsed Advanced tracking.
  Posture alert delays are in Reminders. General has Startup, About and data folder.
- Motion belongs to Floating shrimp. Dedicated sample surfaces sit beside controls
  at wider sizes and below at compact widths. Secondary buttons remain compact.
- All displays creates one click-through shrimp per connected display, using the
  same posture value and preferences. Monitor geometry constrains art size;
  hotplug and fallback update overlays without adding camera workers. The meter
  remains single. Pause/calibration/break suppression reaches every shrimp.
- Reminders has isolated interactive samples and a real-size example with Close.
  Sample actions have no controller connections. Sound and OS notification tests
  require explicit activation and do not enable the corresponding routine flags.

## Checks

- **442 tests pass**; one existing QImage.mirrored deprecation warning remains.
- **93 Settings captures/layout checks pass**: 31 per scale at 100%, 150%, 200%.
  Widths 900, 760, 620; four tabs top/bottom; large/disabled appearance, save failure,
  disabled reminders, example break states and suggestions. No measured short
  buttons, wrapped-label clipping or horizontal scroll overflow. Selected renders
  were visually inspected; renders are synthetic and do not prove native behavior.
- Regression coverage includes save failure/control rollback, retained preferences,
  slider drag/keyboard/focus commits, numeric Enter, suggestion rollback, session
  tab memory, isolated sound/notification examples, and simulated monitor removal,
  fallback, size fitting and suppression. Existing controller tests cover startup
  rollback, patch merging and paused camera changes.
- Staged Windows executable passed the frozen-app smoke check: Qt image/icon
  support, both model loads and synthetic native inference. All five changed
  runtime modules were extracted from the package and matched the tested source.
- Installed to `dist/unshrimp`, refreshed `dist/unshrimp-win64.zip`, and launched
  PID 18328 at 13:08. Process reported Responding; startup log confirmed saved
  baseline present and system tray shown. Native UI interaction was not automated.

Reproduce layouts with QT_QPA_PLATFORM=offscreen, QT_QPA_FONTDIR=C:\Windows\Fonts,
QT_SCALE_FACTOR=1 (then 1.5 and 2), running `capture.py OUTPUT_DIRECTORY` with the
workspace virtual environment. Captures never use the camera or user settings.

## Remaining acceptance

Physical multi-monitor hotplug/mixed DPI, actual desktop overlay legibility,
keyboard-only/screen-reader traversal and OS notification/sound delivery need
native checks. Offscreen examples do not establish notification delivery, webcam
accuracy, sleep/wake, long-session resource use or clean-machine distribution.
