# Restore the familiar Settings layout

The user preferred the previous layout and requested small changes instead of a
redesign. Restored the shared bordered sections on all four pages and removed the
responsive two-column Appearance component. Floating shrimp and Posture meter are
stacked sections again, with their controls followed by a quiet Preview label and
divider. Motion remains with the shrimp; automatic saving with Done remains.

No tracking, calibration, history, configuration format or overlay behavior changed
in this correction. Existing appearance preferences are preserved.

- All **442 tests pass**, with the existing QImage.mirrored deprecation warning.
- **93 layout checks pass** at 100%, 150%, 200%, including compact widths, large
  samples, disabled controls, save failure and reminder examples. Selected renders
  were visually inspected. These use synthetic data and never open the camera or
  save user settings.
- The former side-by-side component was removed; shared section styling is used
  again. No dependency or new setting was added.
- Windows build is staged at `diagnostics/settings-restored-build/unshrimp`.
  Frozen-app icon/model/synthetic inference smoke passes. After the user quit the
  old process, installation hash matched the staged executable and
  `dist/unshrimp-win64.zip` was refreshed. Launched PID 24656; it reported
  Responding and the startup log confirmed the saved baseline and tray.

Native desktop interaction, monitor/DPI behavior and accessibility remain subject
to hands-on checks. This supersedes the layout direction in the earlier refinement
report, whose behavioral changes and tests still apply.
