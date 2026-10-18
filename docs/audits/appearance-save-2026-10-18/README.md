# Appearance and explicit Settings save — 18 October 2026

## Delivered

- Appearance groups Floating shrimp, Posture meter, and Motion. Camera-free
  sample previews show the draft's size, transparency, placement, compact mode,
  visibility, and motion. Preview animation stops when hidden or reduced.
- Floating shrimp supports Small/Medium/Large, transparency with a numeric value,
  bottom-left/centre/right placement, and a display choice when multiple displays
  are connected. Missing saved displays fall back to the default display.
- Meter presets are 36/40/48 px high, scaling shrimp, text, controls, and padding
  together. All ten segments and the one-row design remain. Visibility, compact
  mode, and reset position are available here as well as existing tray controls.
- Restore appearance defaults affects the draft's appearance and meter position,
  never calibration/history. Reset position is applied on Save.
- Large mascot artwork now fits its window, with room for maximum rise and bob.
  Window width/height and placement use the actual selected size instead of the
  original fixed bounds. Tests cover every size and a Large render is retained.
- Shared buttons use flatter neutral surfaces, modest rounded corners, and clear
  hover/pressed/disabled/focus states. Save is the coral primary action. Appearance
  headings and reset actions use a small number of existing icons.

## Save behavior

Settings owns a deep-copied draft. Changes update samples, not runtime preferences.
Save changes commits a patch and closes; Cancel discards it. Window close, Escape,
and app Quit resolve unsaved edits through Save/Discard/Cancel. Cancelling Quit
keeps the worker/app running. Calibration from Settings resolves pending edits
before launching; a failed save prevents that launch.

Only edited fields are merged into current live configuration, including individual
meter fields. A newer baseline, pause preference, or unrelated meter position is
preserved. The candidate is written atomically before runtime hooks apply. Failed
writes keep the draft open and runtime unchanged. If login startup was changed
before a failed write, its earlier OS setting is restored; OS errors are reported.
Camera selection and reminder changes apply on Save. Rescan protects the live
camera even if a different device is selected in the draft.

Camera Preview, Retry, and confirmed Reset baseline are explicit immediate actions,
with copy explaining their separation from preferences. Reset baseline cannot be
undone by Settings Cancel. Suggestion Add/Update edits the draft; Settings Save
commits those changes. Existing tray shortcuts continue to save immediately.

## Verification

- **434 tests passed**, with one existing QImage.mirrored deprecation warning.
- New/updated checks cover private draft/cancel, saved field patches, preservation
  of newer state, write failure, login rollback, real close choices, unsaved Quit,
  calibration gating, pending-camera rescan, preview timers/defaults, all meter
  sizes, and every mascot size fitting at maximum rise/bob.
- **102 real-widget layout checks** passed: 34 layouts at each of 100%, 150%,
  and 200% Qt scaling, using Windows fonts. Captures cover shared-button surfaces,
  calibration/error/completion states, normal/compact Settings, suggestion editor,
  Appearance, all meter presets, and mascot sizes. No camera frames were saved.
- Visually reviewed [Appearance](09-appearance.png),
  [meter and motion](22-appearance-large-bottom.png),
  [Large mascot](23-mascot-large.png), and [Main](08-main-paused-preview.png).
  [Layout report](layout-report.json); larger-scale records are local under
  diagnostics/appearance-save-scale-150/-200.
- The packaged build passes icon decoding, both-model loading, and native
  synthetic inference. All eight changed source modules match bundled bytecode.
  Reports: diagnostics/appearance-save-package-smoke-2026-10-18.json and
  diagnostics/appearance-save-package-match-2026-10-18.json.
- After user Quit confirmation and process-absence verification, dist/unshrimp
  was replaced with the checked build; executable hashes match. Release ZIP is
  refreshed before the updated app is launched.

## Remaining observation

Native display placement/fallback, mixed-monitor DPI, overlay legibility on light
and dark desktop content, and real Settings Save/Cancel interaction still need
desktop observation. Widget bounds prove the Large-artwork window fix, not every
physical monitor configuration. Camera accuracy and long-session/sleep behavior
were not retested for this preference/UI change. No new dependencies were added.
