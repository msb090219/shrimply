# Unshrimp desktop redesign plan

Status: progressively implemented, with current scope in TODO.md. The accepted
direction is compact native Qt windows with shared section styling, a main window
for Today/Progress, and a separate modeless Settings window for configuration.
The larger layout sketches below are earlier explorations, not shipped screens.
Existing tracking fixes and the release checklist remain separate work.

## Direction

A quiet, friendly Windows utility with a distinctive shrimp identity. Clear status
comes first; personal progress and break reminders are secondary. Use standard
window behavior, restrained surfaces, readable text, and deliberate coral accents.
Keep technical scores out of everyday UI. Do not imply clinical accuracy or turn
deviation into an invented percentage. No identity recognition is proposed.

Initial visual target: dark desktop surfaces, coral actions, a small shrimp brand
mark, and illustrations mainly in onboarding and reminder moments. Compare light
and dark versions before finalizing the visual direction. Avoid applying accent
colour to every heading or making the mascot the main navigation mechanism.

Suggested starting tokens, subject to visual and contrast review:

| Role | Starting value |
|---|---|
| Window background | #181B20 |
| Raised surface | #22262D |
| Separator | #383E48 |
| Primary text | #F3F4F6 |
| Secondary text | #B6BEC9 |
| Brand coral | #EC8F6B |

Reserve green/amber/red for meaningful posture states, always paired with text.
Use Segoe UI with a system fallback, sentence-case labels, a clear heading/body
hierarchy, and tabular numerals for changing time values. Use 8/12/16/24/32 logical
pixel spacing and 6–12 pixel corner radii according to component size. These are
starting constraints, not a requirement to make every section a rounded card.

## Main window

One normal, resizable window with a standard Windows title bar. Current initial
size is 760 × 620 logical pixels, capped to the available screen, with a 620 × 480
minimum and scrolling content. Closing the main window leaves tracking in the tray and explains
that behavior on first use. Quit is an explicit tray/application action.

Two tabs: Today owns current tracking/break state and actions; Progress owns all
history. Settings is configuration only: Tracking, Reminders, Appearance, General.
Today links directly to the relevant Settings page. Calibration opens a guided
view from Today or Settings → Tracking. Keep the selected tab when reopening.
The legacy duplicate Stats tab has been removed from Settings.

Earlier Today layout exploration (current implementation uses two compact sections):

```
Unshrimp                                      Standard window controls
──────────────────────────────────────────────────────────────────────
Today       Tracking                          Pause
Progress    Sitting comfortably
Reminders   Quiet posture illustration / clearly labelled indicator
Settings
            Monitored today                   Next break
            Observed time + short summary     Tracked-time countdown
                                              Snooze / Take a break

            Camera and calibration
            Camera status · calibration date
            Preview camera                    Calibrate
```

Lead with a plain state and one useful next action. Camera errors replace the
normal summary with clear recovery guidance. First-run and empty-history views
explain what to do next instead of displaying fake data or a perfect score.
Camera preview is explicitly opened; opening Today or Settings does not itself
start paused capture. Explicit preview can use the camera while posture tracking
stays paused; closing preview releases it. Calibration suspends normal scoring.
History reports observed time and labels legacy estimates honestly.

## Floating posture indicator (the metric)

Current accepted layout (18 October): one row with Small/Medium/Large presets
(36/40/48 px high) contains ten fixed
shrimp lighting from green through amber to red, Pause/Resume, and More. Feedback
floats centred beneath the bar on a transparent area with a small text shadow.
There is no separate app icon/button or drag grip. More shares the tray
menu, including Open Unshrimp and a saved Compact indicator toggle.

The scale has 12 px spacing on each side. The surface uses an open-hand cursor,
changing to a closed hand during dragging; buttons keep their pointer cursors.
Compact mode hides routine text, while camera errors, missing readings, required
calibration, and active calibration remain explicit. The row height and segment
positions and bar width stay fixed; caption visibility changes total height only.
Full progress/details remain available through tooltips and accessible descriptions.

Earlier rising-shrimp, app-launch-button, and two-row HUD treatments were replaced
after user feedback. See audits/metric-grab-2026-10-18/README.md for the latest
captures and the desktop verification still outstanding.

Design these states explicitly: sitting comfortably, posture drifting, adjust
posture, away, paused, stopping camera, camera error, and calibration required.
When evidence is missing, avoid presenting an old good state as a fresh reading.

## Settings

Use a modeless Settings window with the same sections, spacing and controls as
the main window. Group rows by user task. Today shortcuts select the appropriate
preference tab. Progress belongs only in the main window. Settings saves discrete
changes immediately and slider edits on release, keyboard change, or focus departure.
Done closes; failed persistence restores the saved control and shows an inline error.
Edited-field patches preserve newer calibration, pause, and unrelated meter state.
Suggestion Add/Update/Remove commits each edit in its separate modeless editor.

The [page-by-page Settings plan](SETTINGS-REFINEMENT-PLAN.md) is implemented:
labelled samples, motion inside Floating shrimp, all-display overlays,
isolated break examples and explicit notification/sound tests. Tracking-loss delay
is under collapsed Advanced tracking; posture alert timing belongs to Reminders.
General contains Startup, About and local data/support actions. Native multi-monitor
and accessibility acceptance remain open; see the latest Settings audit.

The user subsequently rejected the borderless/side-by-side redesign. Preserve the
original boxed sections and single-column layout. Appearance previews sit beneath
their related controls, distinguished by a quiet label/divider. Make future visual
changes incrementally within this established layout.

| Page | Content |
|---|---|
| Tracking | Camera/status/preview, calibration, sensitivity; collapsed Advanced tracking-loss delay |
| Reminders | Posture alert timing, notification/chime tests, observed-sitting breaks, suggestions and isolated examples |
| Appearance | Floating shrimp size/transparency/placement/display/motion and single meter options; separated samples |
| General | Start with Windows, app version, local-data explanation, diagnostic/support actions |

Keep reset calibration visually separate from routine recalibration, with a clear
confirmation. Keep exercise editing out of the main preferences form. Device
scanning is an explicit action with feedback; never block opening Settings while
probing cameras. Repeated open requests bring the existing window forward.

## Camera preview and calibration

One guided panel contains the camera, step progress, complete wrapping instruction,
capture countdown, named quality checks, and Cancel/Retry actions. Do not split
essential instructions between a floating HUD, camera window, and tray menu.

Proposed flow: Camera setup → Tall → Normal → Hunch → Verification → Ready.
This is a design hypothesis based on the existing algorithm, not a conclusion
that those captures are optimal. Review calibration math and sample validity
before finalizing the stages or timing.

Each capture starts with a brief preparation cue. Lost usable tracking visibly
pauses collection; insufficient samples lead to a specific retry explanation.
Failure clearly states the new baseline was not saved and whether the previous
one remains. Success includes a short demonstration of the indicator/shrimp and
an explicit Start tracking action. Quality overrides must state their effect.

Preview labels, margins, and error states use the same visual language as Today.
Show required shoulder/ear markers selectively and explain framing in ordinary
language. A marker or high confidence must not be labelled proof of visibility.

## Tray popup

Keep this short: current state, camera status, Pause/Resume, Open Unshrimp,
Calibrate, Settings, floating-indicator visibility, and Quit. Show the next break
only if reminders are enabled and its timing is meaningful. Remove raw deviation,
exercise editing, and long instructional text from this surface.

The popup shares typography, icons, labels, and state meaning with the main app.
Initial implementation should retain Qt menu keyboard/focus behavior and screen
edge placement. Design a richer tray panel only if the selected mockup needs it;
do not trade reliable dismissal or focus for decorative effects. Settings/open
actions run after menu dismissal and raise the existing destination.

## Break reminder experience

Start with stretch and walk reminder types, an interval, and snooze. The existing
40-minute setting can seed the mockup; it is not a health recommendation. Proposed
reminders accumulate usable tracked time, excluding manual pause and away time.
The implementation must define brief tracking gaps and when a break resets the
timer. Do not claim that the app identified the same person or verified exercise.

Use a small non-modal prompt with the activity, short instruction, and Take a
break / Snooze / Dismiss. An acknowledgement alone is not proof of a completed
break. Respect disabled reminders, sound choices, Windows notification delivery,
and interrupted sessions. The next-break display explains what time it measures.

## Shared interaction and accessibility requirements

- One meaning for each state across the tray, main window, preview, and HUD.
- Visible focus, logical tab order, accessible names, and keyboard actions.
- Text and controls must fit at 100%, 150%, and 200% Windows scaling without
  horizontal scrolling through settings or truncation of essential instructions.
- State indicators use text as well as colour. Contrast must be measured.
- Feedback is quick and restrained; reduced motion suppresses decorative movement.
- No hidden modal dialogs, duplicate settings windows, or unexpected camera starts.
- Start with existing Qt components and theme tokens. Evaluate the PySide6
  Fluent Widgets library only after choosing the mockup and reviewing fit and
  licensing; no framework rewrite or dependency installation is approved by this plan.

## Current work order

The initial shell, Settings, tray, guided calibration, camera modes, and break
reminder implementation phases are delivered. See TODO.md for checked milestones
and remaining acceptance work; earlier visual explorations are historical.

1. Finish Progress (U08), building on the existing time-based history view.
2. Finish Appearance previews and mascot fit/legibility checks (U06).
3. Group advanced Settings timings and finish preference discoverability (U03).
4. Do one consolidated desktop/accessibility walkthrough of the accepted UI.
5. Resolve remaining tracking/reliability and Windows distribution checks before
   release. macOS requires its own permissions/startup/UI verification and is deferred.

The existing PySide6 application remains the implementation reference. No
framework change or replacement web app is planned. Preserve settings/history.

Current shell (18 October audit): native dark Windows title bars and the real
shrimp app icon are shared across windows. The earlier extra custom header strips
were removed. Other platforms retain native decorations. See
[audits/header-review-2026-10-17/README.md](audits/header-review-2026-10-17/README.md).
