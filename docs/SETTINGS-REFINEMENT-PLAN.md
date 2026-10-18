# Settings refinement plan

18 October 2026. Implemented from the user's feedback. Automatic saving with Done
replaces the previous Save/Cancel interaction. Historical audit records still
describe the builds tested then. See [implementation and checks](audits/settings-refinement-2026-10-18/README.md).
Native multi-monitor/DPI and accessibility acceptance remain open.

## Latest direction — preserve the existing layout

The user prefers the original boxed sections and asked for small modifications,
not a redesign. This supersedes the borderless and side-by-side preview proposals
below. Settings now keeps the shared section boxes and a single stacked column.
Appearance controls stay together inside Floating shrimp / Posture meter; a quiet
Preview label and divider distinguish each sample beneath its controls. Keep motion
with the shrimp and automatic saving with Done. Future changes should refine this
layout incrementally, without another structural redesign.

18 October follow-up: add a persistent Light/Dark choice under Appearance. Keep
the coral accent and segment colors; update palettes across all application
windows and the floating posture meter. The feedback caption uses a small
theme-aware translucent backing so it stays legible on either desktop background.

## Shared layout and behavior

- Keep Tracking, Reminders, Appearance, and General tabs, the native dark header,
  coral accents, and modeless window reuse. Keep Progress in Main only.
- Remember the last Settings tab during the app session; Today shortcuts still
  select their requested page. Preserve keyboard focus and per-page scroll position
  while moving between tabs. Enter commits numeric edits without an accidental close.
- Use aligned rows: a concise label and optional one-line explanation on the
  left, a consistently sized control on the right. Keep long help as wrapping
  text or a tooltip; essential meaning must remain visible.
- Use section headings and spacing instead of enclosing every group in another
  heavy box. Retain one quiet surface where it helps separate a preview or topic.
  Avoid nested cards and full-width secondary buttons.
- Reuse the softer shared button treatment. Primary task actions are clear;
  examples/reset/support actions are quieter. Use icons mainly in section headings
  and recognizable actions, with text labels retained.
- Start with the existing 13 px body type, compact controls around 28–32 px high,
  12–16 px section spacing, and restrained corners. Sliders have a bounded width
  and visible value; selectors do not stretch across the entire window.
- Previews have their own labelled area and a subtly different background.
  They must not resemble clickable controls or live tracking. At comfortable
  widths, place controls beside previews; at narrow widths, stack the preview
  after the controls. Keep related controls visible together where practical.
- Preserve vertical scrolling and the persistent footer. Support the current
  compact window size and 100%/150%/200% Qt scaling without horizontal scrolling.
- Disabled features retain their saved preferences; dependent controls are visibly
  disabled with a short reason. Turning a feature back on restores its options.

## Saving: automatic changes with Done

- Remove Save changes, Cancel, the draft model, and routine unsaved-close prompts.
  Done, Escape, and the title-bar close button close Settings; they do not revert
  successful edits. Keep suggestion Add/Update as explicit editing actions.
- Discrete controls commit immediately. Slider samples/value labels update while
  dragging; save/apply the selected value on release, keyboard change, or focus
  departure. Flush pending slider edits before Done/close or another task action.
  Avoid writing configuration on every animation or pointer movement.
- Footer feedback: a quiet Changes saved status after successful persistence.
  A failed change restores the last saved control/runtime value and shows an
  inline error; never claim it was saved. Allow the user to retry the control.
  Errors must not disappear solely because a success timer elapsed.
- Reuse the controller's edited-field patch/atomic-write path, preserving newer
  calibration, pause, and unrelated HUD changes. Keep persistence before runtime
  side effects and preserve login-startup failure/rollback handling.
- Camera selection applies when changed, following the existing paused/preview/
  tracking camera policy. Rescan still skips the live device. Opening Settings or
  viewing an appearance/reminder sample never opens the camera.
- Reset baseline still requires confirmation. Reset appearance affects appearance
  only, never calibration/history. Do not add a global reset-all action.

## Tracking page

Order: Camera, Calibration, Detection, Advanced tracking.

| Section | Exact contents and changes |
| --- | --- |
| Camera | Device selector and Rescan on one row; truthful lifecycle status beneath; Preview camera and conditional Retry beside each other. Remove the obsolete applies-on-Save note. Keep errors close to these actions. |
| Calibration | Saved/not calibrated status and date, Calibrate action, brief framing/recalibration guidance. Reset baseline is a separate quiet action with its existing confirmation, not equal emphasis beside Calibrate. |
| Detection | Sensitivity slider with visible multiplier and Higher is stricter explanation. Keep scoring formulas and the baseline unchanged. |
| Advanced tracking | Collapsed by default. Put tracking-loss delay here, explained as time before marking the user away. Keep existing ranges. Do not introduce new technical settings just to fill this section. |

Move posture alert delay and repeat delay out of Tracking into Reminders, where
users configure the alerts they affect. Do not duplicate the same preference.
Calibration remains its own flow; leaving Settings for it no longer requires a
Save/Discard question once autosave is implemented.

Acceptance: device changes while paused do not start tracking; rescan cannot
disturb the live device; baseline status stays current; failed saves do not restart
the camera or alter detection thresholds; common tasks are visible before Advanced.

## Reminders page

Order: Posture alerts, Break reminders, a clearly separated reminder example.

| Section | Exact contents and changes |
| --- | --- |
| Posture alerts | System notifications, chime, alert delay, and quieter repeat-delay option. Explain that the existing system-notification switch also covers camera/calibration notices; break cards have a separate enable switch. Add an explicit Send test notification action; preserve the flag's meaning. |
| Sound | Test sound beside the chime control. Sound plays only on explicit activation, including when demonstrating an otherwise disabled chime. Changing a preference or opening the page stays silent. |
| Break reminders | Enable switch, interval plus of detected sitting, short explanation of excluded time and two-minute breaks, and Edit suggestions. Disable interval/editor controls when reminders are off while retaining their values. |
| Example | Labelled Example area, with the same content/style as the actual break card. Show the suggestion and Take a break/Later actions as a clearly marked sample. Show example opens a real-size demonstration with its own close action. |

Reuse the break-card presentation, but isolate sample actions from the real
controller. Clicking the sample, closing it, or testing sound must not start/end
a real break, snooze reminders, change sitting time, write history, or open capture.
The example may demonstrate the break-in-progress appearance using sample data;
it must not present a sample countdown as a live session. Only an explicit test
should produce an OS notification; do not dispatch one when opening this page.
Mark test content as an example and report only that delivery was requested,
not that Windows displayed it. Tests do not enable routine notifications or chimes.

Keep suggestion editing in its modeless editor. Add/Update/Remove commits that
explicit edit immediately; close the editor with Done. Update the old draft/save
instructions. Do not duplicate the full editor inside Reminders.

Acceptance: examples leave all live timer/history/camera state untouched; reminder
enablement/interval changes retain observed-time accounting; disabling reminders
does not erase preferences; sound and native notification delivery are tested
separately from a rendered example.

## Appearance page

Two principal sections: Floating shrimp and Posture meter. No separate Motion card.

### Floating shrimp

Controls: Show floating shrimp, Small/Medium/Large, Transparency plus percentage,
Position (bottom left/centre/right), Display, and Gentle bobbing. Group motion
directly with these shrimp controls.

The dedicated Preview area shows an explicitly labelled sample using these
preferences. Keep it compact enough that its controls are not pushed far below
the fold. Changes also apply to the real overlay through normal posture policy;
do not force the live shrimp to appear while paused, away, calibrating, or on a break.
The sample remains available without slouching or starting the camera.

Display choices: Default display, each connected display, All displays. Keep the
selector visible, with friendly labels such as Display 1 (main) rather than raw
device paths. One shrimp
per display in All displays mode, sharing the same appearance preferences. The
selected anchor is relative to each display's available area. Adding/removing a
display creates/removes the appropriate overlay without affecting tracking.
A missing specifically selected display falls back to the default. Maintain
click-through behavior and suppression/cleanup on every overlay, with no extra
camera or inference worker. Fit each overlay to its screen at supported DPI.

Put Reduce motion beside the shrimp motion controls, with the visible explanation
Also reduces calibration animation. Keep it as the existing app-wide preference;
it disables gentle bobbing without erasing that saved choice. No second conflicting
motion switch in General or another section.

### Posture meter

Controls: Show posture meter, Small/Medium/Large, Compact mode, Reset position.
Place the controls together, then a visually separated Preview area beside/below
them. Do not mix the preview's fake Pause/More controls with the real settings.
Label it Preview; sample controls must not operate the real app.

Preview and real meter use the accepted fixed-width shrimp/control bar with plain
centred feedback underneath. Compact mode hides routine captions, preserving
critical camera/calibration explanations. Keep one draggable meter even when the
large shrimp uses All displays. No meter duplication feature in this pass.

Restore appearance defaults is a quiet action at the bottom of Appearance. Reset
meter position remains next to meter controls. Both give immediate visible feedback
under autosave. Keep placement recovery and existing saved defaults compatible.

Acceptance: samples and live appearance match sizes/colors/motion; every mascot
size fits; all-display overlays clean up and respect pause/calibration/breaks;
disabled controls retain preferences; caption width stays stable; meter dragging
and visibility work after changing size and monitors.

## General page

Order: Startup, About, Data and support. Keep this page short.

| Section | Exact contents and changes |
| --- | --- |
| Startup | Start at login, with Starts quietly in the tray. Keep the existing Windows-only capability and background launch behavior. Show actual OS failures rather than a silently successful switch. |
| Window behavior | Short informational text explaining Close keeps tracking in the tray and Quit exits. No extra close-behavior preference in this pass. |
| About | Current version and Open About. Use the existing About content/window; avoid another duplicate information screen. |
| Data and support | Plain local-processing/history statement and Open data folder, identifying where settings/history/logs live. The current log and data folders are the same, so use one action. Do not imply logs are sent anywhere. |

Defer Clear history, exports, updater controls, per-display appearance profiles,
quiet hours, and theme systems. They were optional ideas, not requirements for
this Settings cleanup. Add them separately if they solve a demonstrated need.

## Implementation order and files

1. Shared setting rows/section presentation and autosave-with-Done, including
   slider flushing, errors, startup behavior, and regression migration.
2. Appearance regrouping/preview separation and all-display mascot lifecycle.
3. Reminders layout, timing relocation, isolated examples, and explicit sound test.
4. Tracking ordering/Advanced and General information/support actions.
5. Render all pages and relevant disabled/error/example states at three scales;
   package once the coherent pass is complete, then do a consolidated desktop check.

Primary scope: ui/settings.py, ui/sections.py, ui/appearance.py, ui/app.py,
ui/mascot.py, ui/break_prompt.py, and their existing tests. Reuse the config format,
theme, art, atomic persistence, and menu/window behavior. Add only the saved
all-display choice needed for the new behavior, preserving existing single-display
preferences. No framework replacement or dependency is planned.

Done means: four consistent pages; no routine Save/Cancel ambiguity; no false saved
feedback; no example affecting tracking; multi-display overlays behaving correctly;
no regressions in pause, calibration, history, startup, dragging, or saved settings.
Native multi-monitor/DPI, keyboard-only navigation, and screen-reader checks remain
explicit acceptance tasks rather than being inferred from offscreen screenshots.
