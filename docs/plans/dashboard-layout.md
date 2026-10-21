# Dashboard layout

Status: implemented locally on 19 October 2026; packaged-app checks pending.
Windows task **U15** and Mac handoff **M04** are in [`TODO.md`](../TODO.md).

## Layout

The normal main window is a progress Dashboard. It shows the Dashboard heading
beside a collapsible navigation rail with Settings at the bottom, followed by
the daily shrimp quote, Today's result, this week's
posture mix, and the activity calendar. The calendar retains fixed square cells,
neutral empty days, selected-day details, and keyboard navigation. There is no
persistent tracking/break status card or close-to-tray instruction.

The tray and posture meter remain the quick tracking surfaces. The tray exposes
Pause/Resume and Calibrate. Settings exposes camera status, Preview, Retry, and
break configuration. The break prompt provides Start break, Later, and End break
when a reminder is due or a break is active.

## Action-needed states

One small card appears before the quote only when the main window can help the
user recover:

| Condition | Card action |
| --- | --- |
| No saved calibration, including a paused first run | Explain setup and offer Calibrate. |
| Camera failure | Show the camera's useful error detail; offer Retry camera and Camera settings. |
| Both conditions | Show camera recovery first; show calibration after the camera recovers. |

The card hides during calibration, system sleep, idle camera stop, normal
tracking, normal pause, and breaks. It must clear when the condition resolves.
Use the existing boxed section style, theme palette, keyboard focus treatment,
and action routes. Keep the quote and progress visible beneath it.

## Acceptance

- Normal, paused, away, due-break, and active-break states show the quote and
  progress without a persistent control card.
- Missing calibration and camera failure show the correct action and clear on
  recovery. A camera failure takes priority when both conditions exist.
- No horizontal scroll or clipped actions at 620 px; check 840 px and wide
  windows in Light and Dark modes.
- Focused Dashboard and full Python suites pass. Check the packaged Windows app
  at native 100% and 150% scaling, then perform the M04 Mac checks separately.

No new graphs, status model, settings, or title bar are part of this change.
