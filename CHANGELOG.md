# Changelog

## 1.2.1 — 18 October 2026

The Windows executable and website favicon now use the same realistic shrimp
as the app window. The color-changing tray shrimp is unchanged.

## 1.2.0 — 18 October 2026

The Windows app now has a single Dashboard for tracking, break reminders and
history, plus a daily shrimp-themed line. Settings has Light, Dark and device
themes, compact Appearance controls, inline break suggestions and a reminder
preview. The posture meter uses a fixed ten-shrimp scale, and the break card
matches its width.

Calibration and camera preview have clearer guidance and separate capture
policies: preview can run while tracking is paused, while calibration suspends
ordinary scoring. Break reminders count detected sitting, offer 5/10-minute
snooze and configurable break length, and keep the camera policy explicit.

Tracking now records observed time rather than frame counts. The app also
includes camera recovery, sleep/wake handling, single-instance protection and
a quieter background launch at login. Windows title bars use the Unshrimp icon.

The native Windows regression suite passes 460 tests; the frozen executable
passes bundled icon, model and inference smoke tests. Live occlusion accuracy,
long-session resource use, mixed-monitor scaling and clean-machine installation
remain open in [the work list](docs/TODO.md). This is a habit reminder, not a
medical device.
