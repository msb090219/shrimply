# Floating metric feedback — 18 October 2026

Feedback now sits centred directly beneath the bar, on a transparent area with
no enclosing box. A small text shadow improves separation from desktop content.
Only the top bar paints a rounded background. The bar contains ten shrimp,
Pause/Resume, and More; it has a fixed width within each size preset.

Small/Medium/Large retain 36/40/48 px bar heights. The feedback adds a short caption
area beneath that height. Compact mode hides routine captions, while camera,
calibration, and missing-reading explanations remain visible. Toggling captions
or changing status never changes width. Long captions elide within the fixed
width, with full details retained in the tooltip/accessibility description.

The existing grab behavior, Settings sample, screen clamping, and break-prompt
positioning follow the whole widget, including its caption height. Tests verify
drag press/release through the top bar container. Preset spacing is symmetric
around the scale. No new setting, dependency, or scoring change was introduced.

## Verification

- **435 tests passed**, one existing QImage.mirrored deprecation warning.
- Updated checks cover constant width across states/compact mode, centered
  caption below the bar, transparent pixels outside caption glyphs, full tooltip
  detail, critical-state caption visibility, all presets, and bottom-edge clamping.
- **102 layout checks** passed at 100%, 150%, and 200% Qt scaling, including
  Settings previews and compact layouts. [Normal](10-hud-middle.png),
  [compact](15-hud-compact.png), [Settings](09-appearance.png),
  [layout report](layout-report.json). Larger-scale output is local under
  diagnostics/metric-caption-scale-150/-200.
- Normal/compact HUD and Settings renders were visually reviewed. These are
  synthetic offscreen states; no camera frames or user preferences were saved.
- Packaged icon/model loading and native inference smoke pass; the bundled HUD
  matches tested source. Reports: diagnostics/metric-caption-package-smoke-2026-10-18.json
  and diagnostics/metric-caption-package-match-2026-10-18.json. User confirmed Quit;
  process absence was verified before replacing dist/unshrimp. Installed executable
  hash matches the checked build and the release ZIP is refreshed before launch.

Caption legibility over actual light/dark desktop content and native mixed-monitor
DPI still need observation. Existing camera and lifecycle checks were not repeated.
