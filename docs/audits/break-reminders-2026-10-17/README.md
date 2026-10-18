# Detected-time break reminders

- [Prompt beside the compact posture indicator](prompt.png)
- [Main-window countdown](main-countdown.png)
- [Main-window actions when due](main-due.png)
- [Reminder preferences](settings.png)
- [Active break countdown](break-in-progress.png)

These are real Qt widget renders with synthetic state, not live camera evidence.
The prompt is 340 × 126 logical pixels for the captured suggestion. It opens
without requesting activation, is modeless, and follows the HUD within the
screen's available area. Hidden-HUD reminders use the screen corner instead.

Only consecutive usable presence observations add time, with a maximum 2.5-second
gap. Pauses, calibration, sleep, idle capture stops, and camera errors break
continuity without losing already accumulated sitting time. A due reminder
remains pending while away and reappears on return, without rotating suggestions
or repeatedly notifying. A stale-camera timer hides the prompt after freshness
expires. Presence is not identity recognition.

Later waits for five more minutes of detected sitting. Take a break starts a
two-minute countdown with an End break action in the card and main window.
The sitting timer freezes and posture alerts/the shrimp are quiet. Camera
tracking continues; the countdown does not verify physical activity. It runs
while away or manually paused and is reconciled after sleep. Finishing it,
automatically or early, starts a fresh sitting interval without counting the
break itself. Disabling reminders cancels the break and clears progress. Interval
changes retain sitting time and recalculate the target; unrelated preference
changes preserve snooze. Reminder progress is deliberately session-local.

297 tests passed, including due-once behavior, absence/stalls, pause continuity,
snooze, acknowledgement, enable/interval changes, controller lifecycle guards,
main-window actions, placement at screen edges, countdown expiry without frames,
early ending, duplicate clicks, and alert suppression. The user confirmed initial
reminder delivery. Countdown interaction, live focus and multiple monitors still
need desktop verification. The original Settings capture predates countdown copy.
