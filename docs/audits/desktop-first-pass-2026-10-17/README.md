# First desktop implementation

Implemented a standard PySide6 main window with Today and Progress, live state
descriptions, Pause/Resume, calibration and Settings actions, camera lifecycle
status, saved-baseline date, and an honest description of existing stretch reminders.
Closing hides the main window and leaves tracking in the tray; Open Unshrimp in
the tray restores it. The main window refresh timer stops while it is hidden.

Settings now has Tracking, Reminders, Appearance, General, and Stats pages.
Existing controls and live-save handlers are reused. Standard Qt groups, spacing,
and system palette replace the forced dark settings stylesheet. Camera scanning
remains explicit. Settings stays modeless and reuses its existing window.
Appearance controls wrap into separate rows. Empty Progress now explains that no
history exists instead of leaving an ellipsis. Camera restart clears the displayed
score so the new main window does not present a previous score as a fresh result.

## Captures

These are actual Qt widget renders using the Windows Qt platform and current
system palette, not image-generated designs. They use synthetic state and stub
history; the baseline date is sample content. Native window borders are outside
the captured widget. No webcam, user settings, startup registration, or real
history was changed to produce them.

- [Main window](main-window.png)
- [Tracking settings](settings-tracking.png)
- [Reminder settings](settings-reminders.png)
- [Appearance settings](settings-appearance.png)
- [General settings](settings-general.png)
- [Empty Progress](progress-empty.png)

250 automated tests pass, including actual controller/tray/main-window wiring,
live state/freshness labels, hide/reopen behavior without stopping capture, pause
routing, calibration gating, grouped settings and preserved live saving. Six
rendered views were visually reviewed; layout corrections were applied and
captures refreshed. No dependency added.

## Boundaries

This is the first functional UI pass, not the complete redesign. HUD, calibration
preview, tray styling, tracked-time break reminders, walk prompts, and reminder
snooze remain future work. Current reminders still use their existing wall-clock
timer; the main window says so. macOS, real display scaling, screen reader use,
and packaged/live desktop operation of this UI pass have not been verified.
The running packaged app remains the previous version until rebuilt and replaced.
