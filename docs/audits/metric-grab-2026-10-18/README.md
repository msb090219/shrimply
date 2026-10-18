# Metric spacing and grab cursor — 18 October 2026

The hover-only grip, its 14 px widget, and its paint/hover state are removed.
The scale starts 12 px from the bar's left edge and has 12 px before the status
or control divider. Outer margins are consistent and the bar remains one row.

The draggable surface uses Qt's open-hand cursor. A left press changes it to a
closed hand; release restores the open hand. Pause and More retain their pointer
cursors. Existing dragging, menu access, compact preference, and scoring remain.

## Verification

- **415 tests pass**; one existing QImage.mirrored deprecation warning.
- Regression checks verify open → closed → open cursor changes, movement/release,
  independent button cursors, exact meter spacing, no grip widget, compact/error
  behavior, and one-row sizing.
- **69 real-widget layouts** at 100%, 150%, and 200% Qt scaling pass, including
  27 HUD states. Visually reviewed [normal](10-hud-middle.png) and
  [compact](15-hud-compact.png). [Layout report](layout-report.json).
  Larger-scale output is local under diagnostics/metric-grab-scale-150/-200.
- Packaged icon/model loading and native inference smoke pass. Bundled HUD
  bytecode matches source. Reports: diagnostics/metric-grab-package-smoke-2026-10-18.json
  and diagnostics/metric-grab-package-match-2026-10-18.json. After verifying that
  the old process exited, dist/unshrimp was replaced with this checked build;
  installed executable hash matches and the release ZIP is refreshed before launch.

Native Windows cursor appearance and live dragging still need desktop observation.
Camera/scoring hardware checks were not repeated for this layout-only change.
