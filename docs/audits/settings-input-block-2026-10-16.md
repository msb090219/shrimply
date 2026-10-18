# Hidden Settings dialog blocked HUD dragging

User reported Settings often needed a second tray click, followed by another
incident where the posture metric could no longer be dragged. The running app
was still responsive and paused; no crash was logged.

Read-only native window inspection of PID 18860 found the visible `Unshrimp`
window disabled, and an enabled `Unshrimp — Settings` window invisible. This
identifies a modal input block: `_open_settings()` used `QDialog.exec()` with
the HUD as parent. A hidden modal dialog can leave that parent disabled. The
specific Windows focus/hiding sequence was not independently reconstructed.
Do not attribute this incident to the mouse-drag implementation or sleep without
additional evidence.

## Fix

- Settings opens modelessly with `show()`, `raise_()`, and `activateWindow()`.
- Repeated Settings requests reuse the existing dialog, bringing it forward.
- Closing clears the reference and schedules deletion; reopening builds from
  current settings. Calibration still closes Settings before starting its flow.
- Tray requests defer opening until the next event-loop turn so the menu can close.
- Initial camera selection contains the current configured device; only an
  explicit Rescan probes other devices. Settings construction no longer probes
  cameras synchronously before displaying the window.

238 automated tests pass. The real-widget regression constructs Settings, hides
it, checks that its parent remains enabled and the dialog is non-modal, and
verifies camera probing was not called. Controller checks cover reuse, foreground
requests, reference cleanup, and deferred deletion. Existing Rescan selection
tests pass. Automated tests do not establish Windows tray/focus behavior after
sleep on the user's actual desktop.

User confirmed old instance quit. Refreshed package built successfully at
`dist/settings-fix/unshrimp/unshrimp.exe`; SHA-256
`3612d5299fea338886b571b591b701a7de18e34f43840b30031904ca2d189dc4`.
Packaged smoke passed (exit 0, frozen true, icon/models/native inference), report
`diagnostics/packaged-settings-fix-smoke.json`. Launched with diagnostics, PID
34372. An initial user confirmation was incorrectly attributed to the new build.
On recurrence, process inspection showed older PID 18860 was still running from
`dist/lifecycle-single-instance` and owned the lock. PID 34372 exposed only an
invisible already-running notice; it never became the primary app. The old HUD
was disabled and its modal Settings dialog invisible again. Retract the initial
packaged Settings-fix pass; it was not testing the fixed code.

Requested normal close of the verified old Settings window, cleared only blocked
replacement PID 34372, and asked user to Quit again. Verified old PID exited,
`app: exit 0` logged at 23:40:17, and lock removed. Then launched the fixed build
as PID 37816. Verified it is the only Unshrimp process, its executable path is
`dist/settings-fix/unshrimp/unshrimp.exe`, and the lock owner is 37816. Its log
`diagnostics-1792147237729437400.log` contains usable inference. Actual fixed-build
first-click/dragging verification is pending again. No new code change was needed
for this recurrence: the intended replacement had not run.

The verified Settings-fix process subsequently passed a real automated active
sleep/wake cycle, resuming usable inference and remaining responsive. This does
not replace direct first-click Settings and physical HUD dragging verification.
The user requested fewer manual tests; do not treat further scripted unit checks
as evidence that the exact desktop dragging sequence was exercised.
