# Compact posture indicator implementation

Replaced the ten-shrimp severity meter with a plain-language state, small state
dot, visible six-dot drag grip, and equal-sized Open Unshrimp, Pause/Resume, and
More controls buttons. The same window size and button positions are retained
for live, paused, stopping, away, camera error, calibration, and uncalibrated
states. At the current font, logical size is 311 × 40; controls are 28 × 28.
The label width is derived once from font metrics and representative longest
labels, rather than changing with each reading. Extra-long custom text is elided
with its full value in a tooltip and accessible description.

Toolbar icons are small palette-aware drawings, cached per icon/colour/device
ratio. Native icon choices were rejected during visual review because one showed
Qt branding and the media icon lacked contrast on the dark surface. The bar uses
system surface/text colours, restrained coral focus, and independent posture
colours. No new dependency or continuous decorative timer.

Open and double-click route to the existing main window. Pause routes to the
controller's existing policy; More/right-click reuse the existing tray menu.
Keyboard focus and accessible control names are included. The indicator does
not claim good posture for a missing score. Zero-offset drag is now valid rather
than treating QPoint(0, 0) as no drag. Desktop buttons/inputs use consistent
padding and minimum content heights in the shared theme.

## Verification

254 tests passed after the functional changes. New checks cover stable size and
control positions across states, equal control dimensions, missing readings,
pause/resume accessibility text, zero-offset dragging/release, keyboard actions,
menu reuse, and actual HUD-to-controller wiring. Screenshot utility updated for
the removed decorative sweep.

[State comparison](hud-states.png) is an actual Qt render of ten synthetic states,
not a live camera capture. Additional [1.5×](hud-states-1.5x.png) and
[2×](hud-states-2x.png) captures were rendered in isolated processes. Every label
in the comparison fits without ellipsis, with constant logical size. The monitor
currently has a 1.75 device ratio: Qt scale multipliers 1/1.5/2 produced effective
ratios 1.75/2.625/3.5, not literal OS 100/150/200 percent settings. An attempted
screen-scale override did not change this. No Windows display setting changed.

The final base and largest-scale captures were visually inspected. First renders
exposed unreadable/platform-branded icons and clipped calibration progress; those
were corrected before the recorded captures. No webcam, user data, or settings
were used. The temporary renderer is in ignored diagnostics output.

## Remaining

Packaged desktop interaction, screen-reader operation, light palette, macOS, and
literal OS display-scale switching remain unverified. The running executable has
not been replaced. Settings/main-window size and layout polish is iterative;
these HUD captures do not certify every screen. Tray visual redesign, unified
camera/calibration panel, and tracked-time break reminders remain separate tasks.
