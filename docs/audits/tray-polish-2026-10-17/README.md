# Tray popup polish

- [Tracking and next break](tracking.png)
- [Active break countdown](break.png)
- [Paused tracking](paused.png)
- [Calibration and setup override](calibration.png)
- [Visibility submenu](visibility.png)

These are real Qt menus rendered with synthetic state. Normal, paused and break
states are 248 × 323 logical pixels on this system; calibration with its optional
override action is 248 × 334. State labels use ordinary wording; numeric posture
deviations are omitted. The optional timing line collapses when unused.

Open, Pause/Resume, Calibrate and Settings lead the menu. Visibility toggles live
in a submenu, followed by About and a separated Quit action. HUD context-menu and
tray entry points share this same menu. Existing left/right activation behavior
is retained. About is deferred until the menu closes, matching Settings/Open.

The controller refreshes availability on menu opening and through its existing
one-second reminder tick. The header distinguishes pause, calibration, idle,
sleep, camera failure and missing readings. Break timing says "min of sitting"
for the observed-time timer, or a clock countdown for an active break. Disabled
break reminders have no timing line. Icon art is cached by state. Synchronizing
visibility checks does not emit user commands or save settings.

The old Continue anyway action existed but was not attached to the menu. It is
now available when setup gets stuck, retaining the controller's setup-only guard.

Validation: 312 tests passed, covering state priorities, sitting/countdown
summaries, visibility signals, pause routing, the setup override, optional header
collapse and repeated icon reuse. Rendered menus were visually inspected.
Live tray/HUD clicks, full keyboard navigation and native macOS behavior remain
unverified; the screenshots are not proof of those desktop interactions.
