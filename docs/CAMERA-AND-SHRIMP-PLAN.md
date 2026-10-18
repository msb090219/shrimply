# Camera modes and shrimp feedback implementation plan

Status: implemented, 17 October 2026. Regression, scaling/motion, source-host
webcam, and packaged resource checks passed. See
[results and desktop verification limits](audits/shrimp-feedback-2026-10-17/README.md).

User clarification: the subsequent [fixed-row correction](audits/shrimp-rows-2026-10-17/README.md)
supersedes the compact rising-shrimp design with a ten-segment gradient row and
keeps twelve calibration slots visible, including unused gray slots and setup.

## Intended experience

Preview works while posture tracking is paused. Calibration uses the camera but
suspends normal posture scoring, history, alerts, and sitting-time accumulation.
Large pose instructions remain visible. Calibration starts automatically after
Calibrate is clicked; no additional readiness buttons are introduced.

Preparation is a gentle blue wave across a stationary row of shrimp. Capture
uses the shrimp accent, fading out one shrimp per completed second of usable
observation. A numeric countdown and explicit state label remain visible. The
compact posture indicator uses a fixed ten-shrimp gradient scale beside its text.
The existing larger desktop shrimp remains separately configurable.

## 1. Separate camera use from posture tracking

Keep one controller and one camera worker. Derive the required camera mode in
one controller helper rather than teaching each window to open a camera.

| Situation | Camera | Normal posture scoring/history/reminders |
| --- | --- | --- |
| Tracking paused, preview closed | Off | Suspended |
| Tracking paused, preview open | Preview only | Suspended |
| Tracking active, preview closed | Tracking | Active |
| Tracking active, preview open | Tracking with mirror | Active |
| Calibration active | Calibration with mirror | Suspended |
| Computer suspended or app quitting | Off | Suspended |

Manual preview opening is an explicit camera request, including while idle.
Closing it removes that request. Normal tracking still follows the existing idle
policy; merely closing preview must not resume a paused or idle tracker. Sleep
overrides every camera request. On wake, restore the mode justified by the current
tracking preference, calibration session, and visible preview.

- Extend the existing worker to support capture-only preview without loading or
  running landmark models. Use actual successful capture for preview readiness;
  tracking/calibration readiness still requires successful inference.
- Change model mode on the worker thread. Preserve serialized shutdown/restart,
  camera selection, reconnect handling, and rejection of stale worker signals.
  Mode changes must wake a paced worker promptly and clear stale landmark overlays.
- Keep the persisted manual pause preference separate from temporary calibration
  suspension. Calibration frames must be routed before the normal pause guard.
- Opening preview while paused must not change the saved pause setting. Pausing
  tracking with a mirror open leaves it in clearly labelled preview-only mode;
  closing the mirror then releases capture. Main, Settings, tray, and HUD must not
  claim the camera is off while that mirror is using it.
- Camera errors during preview-only use belong to the preview/camera status;
  they must not turn posture tracking on or corrupt its paused state.
- Cancellation keeps the previous baseline and restores the pre-calibration
  tracking intent. Successful calibration retains the explicit Start tracking
  handoff. Closing/defering that result leaves tracking paused.
- Keep Pause, Resume, device switching, Retry, reset, sleep/wake, and Quit using
  the same camera-mode decision. No second capture thread or camera handle.

Main files: `unshrimp/ui/app.py`, `unshrimp/vision/worker.py`,
`unshrimp/ui/status.py`, `unshrimp/ui/preview.py`, and the status/action presentation
in Main, Settings, tray, and HUD. Configuration needs no new camera preference.

## 2. Add the visual calibration countdown

Add optional structured timing fields to `StepResult`: activity, elapsed usable
seconds, and target seconds. Populate them from the calibration clock for phase
entry, preparation, capture, and interruptions. Keep existing text/events for
other callers. Do not parse strings such as `NORMAL 2/8s` to drive animation.

Render one small Qt widget beneath the pose instruction using existing shrimp
art and theme colors. Its width and the positions of its icon slots stay fixed.
All twelve slots remain visible: an eight-second pose uses eight, leaving four gray.
The numeric label distinguishes preparation's three seconds from capture time.

| Activity | Row | Text example |
| --- | --- | --- |
| Preparation | Blue highlight moves gently back and forth | Get ready · 3s |
| Capture | Accent-colored shrimp fade out as usable seconds complete | Hold still · 8s remaining |
| Tracking lost | Row and countdown freeze; preparation motion stops | Collection paused · Face the camera |
| Extra quality collection | No false completion or negative countdown | Keep holding · Checking sample quality |
| Done/cancelled | Animation stops; all twelve slots remain neutral | Existing result/cancel flow |

The tall phase can extend beyond its nominal ten seconds for sample quality.
Its initial countdown must therefore lead to a truthful quality-check state
when needed, rather than declaring success or restarting the countdown. No
capture duration, validation threshold, or scoring formula changes are planned.

Use a lightweight Qt repaint timer only while preparation motion or a short fade
is visible. The visual timer never advances calibration. Loss of tracking, hidden
windows, cancellation, sleep, completion, and shutdown stop the relevant motion.
Keep state and remaining time accessible as text; color is supplementary.

Main files: `unshrimp/core/calibration.py`, `unshrimp/ui/preview.py`,
`unshrimp/ui/app.py`, and a small `unshrimp/ui/countdown.py` widget.

## 3. Compact indicator (supersedes the initial moving-shrimp proposal)

Use ten stationary shrimp, lighting in a green-to-red gradient from fresh smoothed
deviation. The final red segment corresponds to the existing Adjust posture
threshold; no new score or thresholds are introduced. Unknown, paused, away,
calibrating, and failed-camera states leave the scale neutral.

The accepted 18 October layout is a fixed-width bar with Pause/Resume and More,
with plain centred feedback floating underneath. No dedicated app launcher or
drag grip remains. Main is available in
More. Compact mode hides routine text and saves the choice, while critical
camera/calibration explanations remain visible. Grab cursors and 12 px scale
spacing replace the old grip. See audits/metric-grab-2026-10-18/README.md.

Reuse cached shrimp art; meter updates are immediate. The separately configurable
large desktop mascot retains its rise/fade behavior and remains hidden during
calibration, breaks, and other non-scoring states.

Main files: unshrimp/ui/hud.py and controller render/menu routing.

## 4. Motion preference and verification

Provide one saved Reduce motion control in Appearance. It stops the blue wave
and decorative bobbing, makes posture position updates immediate, and retains
static shrimp counts and numeric progress. Respect the existing bobbing setting
when reduced motion is off. No new dependencies or web UI stack.

Implement and verify in this order:

1. Camera modes and status consistency. Test the entire table above, plus rapid
   open/close, pause with preview open, selected-camera changes, failed capture,
   reconnect, stale signals, slow worker shutdown, and wake while preview-only.
   Verify preview-only avoids model construction and never records posture time.
2. Structured calibration timing and countdown. Test preparation/capture entry,
   valid observation time, missing frames, head turns, extension, cancellation,
   retry, and completion. A visual animation clock must never collect samples.
3. HUD shrimp and Reduce motion. Test state/segment mapping, missing readings,
   fixed row height, drag/keyboard actions, preference persistence, and timer
   cleanup. Check the existing large shrimp still responds normally.
4. Render default and compact layouts at 100%, 150%, and 200% Qt scaling, including
   twelve-second verification and the extended tall pose. Inspect motion at normal
   size as well as still captures; check readable numbers and fixed icon spacing.
5. Run the full regression suite, package Windows, and run the resource/inference
   smoke check with a fresh report filename. Then do one short live walkthrough:
   paused preview open/close, calibration with no ordinary tracking, visual
   preparation/capture/interruptions, explicit Start tracking, and shrimp response.

Update `docs/TODO.md` with implementation and observed results. Keep physical
camera release, wake behavior, screen-reader use, and native mixed-DPI transitions
marked unverified until actually checked on the new behavior.
