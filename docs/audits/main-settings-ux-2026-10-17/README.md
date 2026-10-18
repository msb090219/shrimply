# Main window and Settings roles

| Place | Purpose |
| --- | --- |
| Today | Current tracking/camera state, saved-baseline status, pause/calibrate, break timing and actions |
| Progress | Today's monitored summary and seven-day history; the sole stats view |
| Settings | Tracking, reminder, appearance and startup preferences; suggestion editing and baseline reset |

The Settings Stats tab was a legacy duplicate reading the same history as
Progress. It has been removed, without changing storage or measurements.
Camera settings and Reminder settings on Today open the existing modeless
Settings window at the relevant tab. Calibration entry points launch the same
guided flow; these are shortcuts, not duplicate implementations.

Main, Settings and Progress now share a single section component and theme rule:
inset headings, equal content insets, restrained borders and compact controls.
Today and Progress scroll vertically when space is tight; initial dimensions
respect available screen space. Progress refreshes on selection and when the
main window reopens with that tab selected. Settings no longer queries history.

- [Today](today.png)
- [Break due](break-due.png)
- [Progress](progress.png)
- [Empty progress](progress-empty.png)
- [Minimum-size Today](compact-0.png)
- [Minimum-size Progress](compact-1.png)
- [Configuration-only Settings](settings.png)
- [Minimum Today at Qt scale factor 1.5](today-scale-1.5.png)
- [Minimum Today at Qt scale factor 2](today-scale-2.png)

These are real Qt renders with synthetic settings/state/history. 315 tests pass,
including correct preference-page shortcuts, removal of duplicate stats, and
fresh progress on reopen. Minimum 620 × 480 logical content fits horizontally,
including both pages at Qt scale factors 1.5 and 2 (reported DPR 1.5 and 3.5
respectively in these renders; these are not literal OS scaling percentages).
Live desktop navigation, full accessibility, and physical display checks remain
pending. No real history or camera frames were used for these captures.
