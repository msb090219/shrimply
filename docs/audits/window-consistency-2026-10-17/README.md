# Shared window styling — 17 October 2026

Main, Settings, Calibration, About, Welcome, and the suggestion editor now use a
compact shared shrimp header and consistent section styling. Main omits the
repeated app-name heading. Settings and Refresh retain keyboard focus indicators
without a border after mouse clicks. About is modeless and reused.

Windows uses Qt extended client areas with native caption controls. Other
platforms retain their standard decorations. No new dependency was added.

## Evidence

- 321 automated tests pass, including caption flags, metadata/icon, modeless About,
  welcome actions, keyboard focus, and existing calibration/settings lifecycle.
- Camera-free Windows probe verified native control flags and maximize/restore.
- `main-native-frame.png` includes Windows caption controls; `main-client.png`
  captures only the Qt widget content.
- `calibration.png` and `calibration-compact.png` use synthetic camera content.
  The compact 480 × 500 layout scrolls vertically with its footer visible and
  no horizontal overflow. `calibration-result.png` captures an inline result.
- `settings.png`, `suggestions.png`, `about.png`, and `welcome.png` show the
  matching secondary windows. Widget-only captures omit native caption overlays.

Still to check: live caption-button clicks, dragging/resizing/Snap, complete
keyboard interaction, and macOS. These captures do not verify webcam accuracy.

Packaged verification: dist/window-consistency/unshrimp/unshrimp.exe built successfully. Its --smoke-test exited 0 and passed Qt image/icon loading, both model loads, and native inference (packaged-smoke.json). This camera-free check does not verify live window interaction.
