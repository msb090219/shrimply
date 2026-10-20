# Changelog

## 1.3.0 — 20 October 2026

The Windows Dashboard now puts today's monitored time, the weekly posture mix,
and a square-cell activity calendar together. A collapsible sidebar opens
Settings in the same window. Setup and camera-recovery actions appear only when
needed.

Appearance now offers a vertical posture meter and a discreet text cue as
alternatives to the horizontal meter and large shrimp. The cue responds to
sustained poor posture, with adjustable appearance and recovery delays, entrance
style, size, position, transparency, and motion. Settings previews reflect the
current choices.

Startup settings and saved calibration are validated more carefully. Failed
calibration saves keep the previous baseline; pause and Quit remain usable after
storage errors. The Windows build checks dependencies and runs bundled icon,
model, and inference smoke tests. The README and website now show the current UI.
The welcome screen, README, and website now disclose MediaPipe SDK usage metrics,
and the Windows package includes the upstream MediaPipe and OpenCV notices.

Real-camera occlusion limits and remaining hardware checks are tracked in the
[work list](docs/TODO.md). Unshrimp is a habit reminder, not a medical device.

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
