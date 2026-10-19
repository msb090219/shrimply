# Unshrimp work list

Last reviewed: 19 October 2026.

This is the shared list of outstanding work from the tracking review and local
webcam checks. Completed tasks stay checked below so progress remains visible.
Keep task IDs unchanged; partially verified hardware tasks remain open.
Before application-code changes, follow the feature handoff rule in
[`AGENTS.md`](../AGENTS.md): review this list, add new feature tasks and linked
Mac checks before implementation, then record each platform's result separately.

**Evidence:** Confirmed means reproduced with a small logic check. Code review
means the behavior follows from the code but has not been exercised through the
full app. Hardware observations come from short tests on camera 0 on this Windows
machine; they do not establish reliability on other devices.

Implemented tracking fixes and first-pass results are recorded in [the 16 October report](audits/tracking-2026-10-16.md). Hardware verification follows [the Windows test procedure](TESTING.md).

## Current priorities — 19 October update

Settings now autosaves with Done, keeps break suggestions visible in **Alerts and
breaks**, and shows an isolated reminder preview. Main combines tracking, breaks,
and history in one Dashboard with a daily shrimp line. The native Windows suite
passes **460 tests**. Native monitor/DPI, notification delivery and accessibility
acceptance remain open. Earlier Settings captures are in [the Settings audit](audits/settings-refinement-2026-10-18/README.md).

Latest user direction: keep the original boxed sections and single-column Settings
layout. Borderless sections and side-by-side Appearance were reverted; make small
refinements within the familiar design. [Restored-layout checks](audits/settings-restored-2026-10-18/README.md).

Light, Dark, and device-matching themes are installed. The user confirmed the
floating meter's three-dot icon in Light mode. Broader theme review remains open;
see [the appearance audit](audits/light-dark-and-caption-2026-10-18/README.md).

This list separates completed implementation from unfinished acceptance checks.
A checked implementation subtask does not mean its whole feature is release-verified.
Historical reports describe the build tested then; later reports supersede UI details.
See the [progress audit](audits/progress-2026-10-18.md) for evidence and scope.

1. **U08 — review Dashboard history.** A 12-week monitored-time heatmap,
   selectable day details, and a weekly posture mix are implemented. Day details,
   keyboard arrow navigation, and the distinction between current, empty, and older
   history have had a focused code/UI pass. Check native layout, screen reader
   behavior, color contrast, and mixed-monitor scaling on the packaged app.
2. **U06 — verify Appearance.** Previews, placement, transparency, motion,
   defaults, meter presets, and the Large-window cropping fix are implemented.
   Check actual desktop sizing/placement and light/dark background legibility.
3. **U03 — verify refined Settings.** Grouping and autosave with Done are
   implemented; check native keyboard/accessibility and preference discoverability.
4. **One consolidated desktop walkthrough:** U01/U02/U04/U05/U07/R02 plus Settings
   first-click/dragging. Verify the latest UI together rather than repeating every
   old build's checks. Include calibration interruption, completion, and preview.
5. **U12 — make the large shrimp respond to sustained posture.** Keep the meter
   live, but let the mascot appear only after posture has stayed poor and fade
   away smoothly on recovery. Verify on Windows, then follow the linked Mac task
   M01 below.
6. **Before release:** resolve/characterize T08 occlusion, then finish H01–H06,
   clean-machine distribution P01, and W01. Earlier sleep/wake successes remain
   evidence; they do not close all lifecycle scenarios. Mac packaging and first-run
   checks are being worked on separately.

For cross-platform changes, implement shared behavior once, add a platform-neutral
regression test, and record Windows and Mac hands-on results under linked tasks.
The Mac task should name the Windows task and implementation commit once it exists.
CI runs the tests on both systems; it does not replace testing the packaged app,
its camera permissions, or its overlays on each desktop.

## Completed implementation milestones

- [x] One Dashboard for tracking, breaks and history; Settings contains configuration only.
- [x] Shared native dark title bars, real app icon, consistent sections and controls.
- [x] Modeless Settings/About/editor and consolidated tray/HUD menu.
- [x] Ten-shrimp bar with centred floating feedback, Pause/More, saved compact mode,
  balanced spacing, and open/closed grab cursors; no app button or grip.
- [x] Unified calibration panel, pinned pose guidance, fixed twelve-slot countdown,
  blue preparation wave, neutral optional details, retry/failure/completion flow.
- [x] Independent paused camera preview and calibration exclusion from scoring,
  history, posture alerts, and detected-sitting time.
- [x] Tracked-sitting break reminders, five-minute snooze, two-minute break state,
  early end, and editable suggestions.
- [x] Manual launch vs background login flow, duplicate activation, saved pause,
  camera recovery, time-based history, and reduced motion.
- [x] Appearance previews, shrimp placement/display/transparency, meter size presets,
  appearance defaults, Large mascot window fit, all-display overlays and autosave with Done.

## Completed code tasks and checks

- [x] **T01 — Resume tracking when the user returns from away.** Regression
  passes; controlled camera-0 return resumed scoring 2.490 seconds after the first
  usable detection. See the tracking report for the transient return classifications.
- [x] **T02 — Keep the camera off when changing devices while paused or idle.**
  Controller and rescan regression tests pass; resume uses the selected device.
- [x] **T03 — Make worker errors and shutdown safe.** Processing errors report
  failures and release resources. Replacement waits for worker completion;
  injected-failure and delayed-stop tests pass.
- [x] **T04 — Reject contradictory calibration samples.** Contradictory signals
  are excluded and tuning preserves separation from the demonstrated hunch.
- [x] **T05 — Require enough evidence to verify calibration.** Sparse and gapped
  verification is rejected. The controlled successful run used 24 verification samples.
- [x] **T06 — Measure posture history by time rather than frame count.** Timed
  state durations replace frame counts for new history. Tracking gaps and explicit
  pauses break continuity. Equal durations at 1/4 fps report 50%; legacy rows remain
  readable as labelled estimates. See the [history report](audits/history-time-accounting-2026-10-16.md).
- [x] **T07 — Announce recovery only after sustained good posture.** Drifting
  and missing evidence interrupt the recovery timer; regression tests pass.
- [x] **Calibration failure feedback.** Failure explicitly states that the new
  calibration was not saved and whether the previous one is retained.
- [x] **Single-instance protection.** A per-user startup lock prevents a second
  guarded source/packaged launch from accessing settings, history, or capture.
  Competing-process and stale-lock tests pass; user confirmed the expected
  already-running notice from a normal packaged launch. Older unguarded builds
  must be closed before upgrading.
- [x] **Wake-recovery fix and first hardware retest.** Windows power notifications
  stop capture on suspend and restore it on wake only when policy permits.
  One active retest resumed usable capture automatically; one paused retest
  on the updated handler stayed paused with no capture samples after waking.
  Broader lifecycle verification remains under H04.
- [x] **Local Windows build/resource smoke check.** The earlier tracking build
  loaded its icon/models and ran synthetic inference successfully. Release CI
  now runs that smoke check. A refreshed local lifecycle-test executable now
  includes T06 and T08 guards and passes frozen icon/model/native inference smoke.
  See the [packaged lifecycle record](audits/windows-lifecycle-2026-10-16.md).

## Correct scoring, history, and feedback

- [ ] **T08 — Reject unreliable required landmarks.**
  - Implemented: required ears/shoulders need visibility and presence >= 0.5;
    missing, nonfinite, or out-of-frame required geometry is unscorable.
    Rejected frames cannot enter scoring/calibration or draw landmark overlays.
  - Camera 0: normal sitting accepted 16/16 frames. Covering one ear also accepted
    16/16 with high confidence: physical occlusion remains unresolved. Raising
    the threshold would not reliably separate these two observations.
  - Preview-assisted shoulder-out-of-view run rejected 6/16 frames and accepted
    10/16, with high confidence throughout. Partial framing rejection is observed;
    consistent rejection of the obstructed interval is not established.
  - Remaining: investigate occlusion handling and validate more camera conditions.
    Confidence field flow and model checksum checked; no application conversion
    defect found. Diagnostics now record exact rejection reasons and named
    out-of-frame points. Same-frame IMAGE/VIDEO comparison shows high confidence
    for out-of-frame joints in both modes; tracking alone does not explain it.
  - Follow-up normal / shoulder / normal: 16/16, 15/16, 16/16 accepted.
    The single rejected shoulder frame named `out_of_frame:left_shoulder`.
    Each condition restarted the model. A later continuous pose-only comparison
    passed normal/return geometry and confidence in both modes (17/17 each).
    During shoulder-out, VIDEO rejected 11/17 by coordinates versus IMAGE 8/17;
    confidence rejected none. Switching to IMAGE is not supported as a fix.
    See the [confidence report](audits/landmark-confidence-2026-10-16.md).
  - Complete when: low-confidence or occluded required landmarks produce an
    unscorable frame, clean frames still work, and synthetic confidence tests
    plus a live occlusion check pass.
  - Files: `unshrimp/vision/metrics.py`, `unshrimp/vision/landmarks.py`,
    `tests/test_metrics.py`.

## Hardware and lifecycle follow-ups

- [ ] **H01 — Make camera shutdown status truthful.**
  - Implemented: the pending-stop message remains until the worker finishes;
    regression tests cover delayed completion. Measured stops took 0.75–1.17 s.
  - Remaining: physical camera-indicator confirmation, including slow shutdown.
    User confirmed light off/on and no freezing across six logged packaged-build
    cycles. Deliberately slow-stop indicator verification remains pending.
  - Complete when: manual pause/resume checks agree with the worker lifecycle
    and physical indicator, including a deliberately slow stop.
  - Files: `unshrimp/ui/app.py`, `unshrimp/vision/worker.py`.

- [ ] **H02 — Investigate occasional frame-delivery gaps.**
  - Observed: short 2 fps worker tests had delivery gaps up to about 1.8 seconds,
    despite median inference times of roughly 20–28 ms.
  - Recent short check: maximum delivery gap at 2 fps was 0.531 s; all four rates
    delivered frames and stopped cleanly. Longer-run buffering/staleness checks remain.
  - Work: measure capture, inference, and UI-delivery timing separately during
    a longer run. Check whether buffering delivers stale frames. Separate
    startup/recovery gaps from steady-state behavior before deciding on a fix.
  - Complete when: the gaps are explained, stale-frame latency is measured,
    and any identified defect is fixed and retested at 0.5, 1, 2, and 4 fps.

- [ ] **H03 — Verify physical disconnect and camera contention.**
  - Partly checked: user disabled access to the built-in camera, observed an
    unavailable-camera message, and restored access with automatic recovery.
    Unplug/reconnect (requires a USB device), privacy shutter, midstream driver
    failures, and another app taking the camera remain unverified. Invalid-device
    recovery is a simulation, not a substitute for those scenarios.
  - Complete when: each available scenario either recovers cleanly or shows a
    clear error, without freezing the UI or leaving an orphaned worker.

- [ ] **H04 — Verify lock, sleep/wake, idle-stop, and repeated pause/resume.**
  - Partly observed: a logged manual pause reduced activity, and a later resume
    restored capture. Controlled leave/return passed. Six refreshed packaged-build
    pause/resume cycles have user-confirmed camera light off/on and no freezing,
    with logged pause/resume and usable inference afterward. One user-confirmed
    paused sleep/wake cycle preserved pause, camera light off, and responsive tray;
    no vision samples followed the logged pause. Repeated sleep cycles,
    lock/unlock, idle-stop, and quick resume during shutdown remain incomplete.
  - Active sleep/wake failed: camera stayed off until manual Pause/Resume.
    Windows suspend/resume handling is now implemented and regression-tested;
    refreshed packaged active retest passed once: power resume logged 23:15:24,
    usable inference 23:15:27 without manual intervention. Paused retest on this
    handler also passed once: pause 23:28:41, suspend 23:28:49, resume 23:29:06,
    no later vision samples, and user confirmed pause preserved. Repeated cycles
    and the other lifecycle scenarios remain pending.
  - Automated active cycle on verified Settings-fix build passed: real sleep,
    logged resume 23:45:08, usable inference 23:45:14, same responsive process,
    no manual restart. Temporary wake timer requested 25 s; observed return was
    about 86 s. Duplicate native power events caused repeated restart requests;
    exact initialization count was not measured. See the lifecycle record.
  - Complete when: repeated cycles preserve the selected camera, manual pause,
    and calibration state; capture resumes when appropriate and remains off
    when paused. Check the camera indicator manually.

- [ ] **H05 — Measure long-session resource use.**
  - Completed: approximately ten minutes of source-process sampling, including
    a pause. Handles/threads fell after pause; paused CPU averaged 0.136% of one core.
  - Remaining: two-hour screening, a working-day run, and power/battery measurements.
  - Complete when: a representative extended session records CPU/memory across
    live, preview, away, and paused modes; memory does not continually grow,
    paused capture stops, and power-saving claims have measured support.

- [ ] **H06 — Validate tracking against controlled real movements.**
  - Completed on camera 0: successful calibration, a confirmed normal-sitting
    minute without bad states, deliberate slouch detection with a user-observed
    shrimp cue, return to good, and controlled leave/return.
  - Remaining: head turns, occlusion, lighting/seating changes, repeatability,
    and additional supported cameras. Posture-alert notification delivery remains
    unconfirmed; the user confirmed the shrimp cue and the separate break reminder.
  - Complete when: calibrated tall/normal/hunch, head turns, partial occlusion,
    lighting changes, and seating changes are checked with expected outcomes.
    Include additional supported webcams where available and record failures
    without saving identifiable camera frames.

## Desktop UI

The current UI is implemented across Main, Settings, tray, calibration, preview,
About, onboarding, and the metric. The items left open below name remaining
implementation or acceptance work, not a request to rebuild those surfaces.

- [ ] **Settings first-click opening and blocked HUD dragging.**
  - [x] Found the invisible modal Settings window; implemented modeless reuse,
    foreground handling, deferred tray opening, and no camera probing on open.
    Parent/input-block and window-reuse regressions pass.
  - [ ] Confirm first-click opening and uninterrupted dragging in the latest build,
    including after sleep and with the HUD hidden. Earlier successful user feedback
    was followed by another freeze, so it does not establish the final fix.
  - [Evidence](audits/settings-input-block-2026-10-16.md),
    [interaction checks](audits/interaction-ux-2026-10-17/README.md).

- [ ] **U01 — Make the posture HUD understandable and operable.**
  - [x] Fixed-width bar with Small/Medium/Large presets (36/40/48 px high): ten
    green-to-red shrimp, Pause/Resume, and More. Feedback floats centred below,
    outside the bar background, with a small readability shadow. No app button or
    grip; Open Unshrimp remains in More. Captions do not change bar width.
  - [x] Saved compact mode; critical camera/calibration/missing-reading text stays
    explicit. Unknown/non-scoring readings are gray. Meter direction is available
    in accessibility text; two buttons have names, tooltips, focus, and keyboard access.
  - [x] Medium uses twelve-pixel spacing around the scale; open hand on draggable surfaces,
    closed hand during dragging, pointer over buttons. Expansion stays on-screen.
    Width stays fixed for each size; caption visibility changes total height only.
  - [ ] Latest-build desktop drag/cursor and compact-restart check; first-user
    understanding and screen-reader review. User preferred single-row spacing
    over the rejected two-row design; latest grip removal is not yet confirmed.
  - [Current caption checks](audits/metric-caption-2026-10-18/README.md),
    [sizes and Settings](audits/appearance-save-2026-10-18/README.md).

- [ ] **U02 — Unify camera setup and calibration into a guided panel.**
  - [x] One mirror/guidance/checks window with Cancel, Retry, override explanation,
    completion/failure, and preservation of the old baseline on cancel/failure.
  - [x] Large pose and supporting instruction together above the timing panel.
    Small step label; optional neutral Camera details disclosure scrolls into view.
  - [x] Twelve stationary slots at all stages, blue preparation, usable-time
    capture countdown, gray unused/consumed slots, tracking-loss pause, and truthful
    extra-quality collection. Calibration suspends normal scoring/alerts/history.
  - [ ] Complete the latest UI from setup through verification and Start tracking,
    including tracking loss, camera error/retry, and cancellation. Check pose/timing
    comprehension. Earlier successful calibrations predate these visual revisions;
    broader repeatability/effectiveness belongs with H06/T08.
  - [Hierarchy captures](audits/calibration-hierarchy-2026-10-18/README.md),
    [camera/timing results](audits/shrimp-feedback-2026-10-17/README.md).

- [ ] **U03 — Reorganize preferences around user tasks.**
  - [x] Autosave and Done, labelled previews, alert timings in Alerts and breaks,
    and collapsed Advanced tracking.
  - [x] Tracking, Alerts and breaks, Appearance, General; shared section styling,
    aligned controls and an inline multiline suggestion editor with immediate
    Add/Update/Remove commits.
  - [x] Automatic saving and Done replace Save/Cancel. Slider edits flush on release,
    focus departure and task actions; failed writes restore controls with inline errors.
    Patches preserve newer baseline, pause and unrelated meter changes. Appearance
    samples are camera-free; reminder examples do not affect live timers/history.
    Test sound/notification are explicit actions. General exposes About/data folder.
    Rescan skips the current camera; camera changes obey paused capture policy.
  - [x] Main has one Dashboard with tracking, breaks and history. Its shortcuts
    select the relevant Settings page and reuse its window.
  - [x] Tracking-loss delay under Advanced; posture timings in Alerts and breaks; last-tab
    session memory; numeric Enter does not close Settings. Layouts pass at three scales.
  - [ ] Native keyboard/accessibility and discoverability walkthrough.
  - [Settings evidence](audits/settings-polish-2026-10-17/README.md),
    [Main/Settings roles](audits/main-settings-ux-2026-10-17/README.md).

- [ ] **U04 — Make camera and calibration status visible and trustworthy.**
  - [x] Shared lifecycle/baseline/date status, stale-image clearing, inline errors,
    Retry, explicit preview, and reset separate from recalibration.
  - [x] Preview while paused uses the single worker without inference/history;
    closing it releases capture. Calibration uses inference with normal scoring
    suspended. Source-host webcam tests and packaged module comparisons passed.
    Mirror-close releases measured 264/260 ms in the later preview-only checks.
  - [x] User observed unavailable-camera feedback when access was disabled and
    automatic recovery after restoring access; controls were readable/reachable.
  - [ ] Friendly device names; explicit latest packaged preview/Retry walkthrough,
    midstream driver/contention failures, preview-only wake, and native mixed DPI.
  - [Camera verification](audits/camera-status-2026-10-17/VERIFICATION.md),
    [updated preview policy](audits/shrimp-feedback-2026-10-17/README.md).

- [ ] **U05 — Apply consistent typography, layouts, and accessibility.**
  - [x] Shared typography/sections, compact controls, coral accents, utility icons,
    wrapping/scrolling, pointer/hover/pressed/disabled feedback, keyboard focus,
    shortcuts/tooltips/names, and neutral calibration disclosures.
  - [x] Shared softer button surfaces/corners and primary Done styling; restrained
    Appearance heading/reset icons. Latest Settings batch passes 93 layout checks;
    the preceding broader UI batch passed 102.
  - [x] Automated interaction checks and offscreen layouts at 100%/150%/200%; latest
    earlier metric render batch passed 69 checks, including 27 metric states. User reported no
    app-specific clipping at 100%; small text in other apps was also harder to read.
  - [ ] Full keyboard-only and screen-reader pass, measured contrast, native
    Windows scaling and mixed-monitor transitions. Offscreen renders cannot close these.
  - [Interaction evidence](audits/interaction-ux-2026-10-17/README.md),
    [latest calibration](audits/calibration-hierarchy-2026-10-18/README.md).

- [ ] **U06 — Polish the mascot and provide appearance previews.**
  - [x] Motion controls inside Floating shrimp, labelled samples, and
    All displays with one synchronized shrimp per connected display. Simulated
    hotplug, missing-display fallback, per-screen fit and suppression pass.
  - [x] Saved visibility/size/opacity/bobbing and Reduce motion; suppression during
    calibration/breaks/non-scoring states. Reduced-motion regression checks pass.
  - [x] Camera-free shrimp/meter previews reflect visibility, sizes,
    transparency, position, compact mode, and motion. Preview timers stop when
    hidden or reduced. Saved placement supports bottom left/centre/right and display.
  - [x] Restore appearance defaults and reset meter position apply and save immediately.
    Window bounds now contain every mascot size at maximum rise/bob; regression
    checks and Large captures pass. Meter presets preserve all ten segments.
  - [ ] Verify native display selection/fallback, all sizes/rise/bob on the desktop,
    light/dark background legibility, and mixed-monitor DPI. Widget fit tests are
    not physical monitor acceptance. [Evidence](audits/appearance-save-2026-10-18/README.md).

- [ ] **U07 — Improve onboarding and calibration completion.**
  - [x] Welcome explains framing, pose purpose, duration, privacy, and Later.
    Later leaves the camera off; success saves then pauses, offering Start tracking
    or Later. Optional How it works explains indicator, shrimp cue, and breaks.
  - [x] Save/start guards, cancellation/failure preservation, pause persistence,
    keyboard actions, and compact result layouts are tested.
  - [ ] New-user walkthrough of latest setup-to-start flow, physical camera light
    after completion, instruction comprehension, and assistive technology/native DPI.
  - [Onboarding evidence](audits/onboarding-2026-10-17/README.md).

- [ ] **U08 — Make progress useful and honest.**
  - [x] Existing view shows today's monitored minutes/percentage, seven-day bars,
    no-history guidance, excluded-time explanation, and labelled legacy estimates.
    Time-based accounting and legacy distinctions have regression coverage (T06).
  - [x] Replace seven-day bars with a centred 12-week monitored-time heatmap;
    selectable cells and accessible names give full dates and values. Add a
    weekly timed good/drifting/adjust mix. No-data and zero-in-range days differ;
    dashed cells mark old sample-based estimates, excluded from timed weekly mix.
    Heatmap color represents monitored time rather than a health judgement.
  - [x] Correct Today's summary when the latest observation is from an older day;
    give the selected date its own line, keep empty cells uncolored, show ~ on
    older estimates, and navigate the calendar with arrow keys and one Tab stop.
  - [ ] Native layout, keyboard/screen-reader, light/dark contrast, and mixed
    history acceptance remain. Focused Progress and Settings modules pass separately
    (25 and 26 checks); their combined invocation reports 51 passes but exits 1
    during teardown. Native desktop and screen-reader acceptance remain open.
  - Files: unshrimp/ui/stats.py, unshrimp/storage/db.py, tests/test_settings.py,
    tests/test_history.py, tests/test_db.py.

- [x] **U09 — Simplify the tray popup and share it with the HUD.**
  - Implemented plain state/break summaries, ordered Open/Pause/Calibrate/Settings,
    Compact indicator, visibility submenu, setup override, and Quit. HUD More uses
    the same menu. Icon caching and silent action synchronization are tested.
  - Remaining acceptance: native left/right clicks, context menu/keyboard behavior,
    and macOS status menu. [Evidence](audits/tray-polish-2026-10-17/README.md).

- [x] **U10 — Unify secondary windows and simplify the app header.**
  - Current design uses native Windows title bars with consistent dark active and
    inactive colors and the real shrimp app icon. Earlier custom header strips
    were removed. Other platforms retain native decorations.
  - Main/Settings/calibration/About/welcome/editor share styling; Settings is
    modeless and positioned relative to Main. About reuses its window. Keyboard
    focus remains visible without persistent mouse-focus borders on utility icons.
  - Remaining acceptance: native focus/title-bar transitions, placement, drag/resize/
    Snap, keyboard walkthrough, macOS. [Latest header design](audits/header-review-2026-10-17/README.md).

- [x] **U11 — Coordinate manual launch, login startup, and the tray.**
  - Manual launch opens/restores Main; login uses --background. Duplicate manual
    launches activate the existing app, background duplicates stay silent. Close
    hides, Quit exits; saved manual pause survives restart. Enabled legacy login
    entries migrate to the background flag without enabling disabled startup.
  - Remaining acceptance: real Windows login and foreground activation checks.
    [Evidence](audits/startup-flow-2026-10-17/README.md).

- [ ] **U12 — Make the large shrimp respond to sustained posture.**
  - Feedback from 19 October: the large shrimp appears too directly from the
    meter score. Keep the meter responsive, but require several seconds of
    sustained poor posture before the mascot fades in; let it fade away on
    recovery. Brief score fluctuations should not make it pop in and out.
  - Keep immediate suppression for pause, away, camera loss, calibration, and
    breaks. The existing 45-second alert grace period remains independent.
  - [ ] Add a shared timing regression covering sustained posture, recovery,
    interrupted tracking, and Reduce motion.
  - [ ] Verify the packaged Windows app with a live camera.
  - Mac handoff: M01 below. Add the implementation commit to M01 when U12 lands.

## Break reminders

- [x] **R01 — Replace wall-clock stretch reminders with detected sitting time.**
  - Adjustable 5–180 minute interval using existing saved settings; usable
    presence only, no bridging gaps over 2.5 seconds. Manual pause, calibration,
    idle camera stop, suspend, and camera errors break continuity.
  - Compact modeless prompt beside the HUD, clamped to the available screen;
    fallback positioning when the HUD is hidden. Main window also provides
    Take a break and Later actions. Snooze counts five more observed minutes.
  - Take a break starts a two-minute countdown, suppressing posture alerts and
    the shrimp while freezing the sitting timer. End break finishes early;
    completion starts a fresh sitting interval. Camera tracking continues.
    Physical activity is not verified. Progress is session-local.
  - Existing exercise suggestions are retained; an empty list falls back to
    a short walk/stretch suggestion. No person identity is inferred.
  - [Widget captures and validation](audits/break-reminders-2026-10-17/README.md).
- [ ] **R02 — Verify reminder interaction on the live desktop.**
  - [x] User confirmed the reminder notification appears correctly and gave
    positive feedback after the two-minute break update.
  - [ ] Record explicit active-countdown/early-end and repeated-snooze results,
    focus behavior while working in another app, and multiple-monitor placement.
    The broad positive feedback does not document each of these scenarios.

## Windows distribution

- [ ] **P01 — Validate the release delivery on a clean Windows machine.**
  - [x] Portable executable/ZIP builds, embedded icon/models, synthetic native
    inference smoke, and a draft-release CI workflow exist. Latest local build
    matches the checked HUD source; no release was published in this audit.
  - [ ] Choose portable ZIP versus installer for the first release; decide signing
    and update expectations. Test the downloaded artifact without a development
    environment, camera permissions, startup, data preservation on upgrade, and
    clean removal. Confirm bundled notices/model licensing before distribution.
  - This is a newly explicit release gap, not a claim that an installer is required.
    macOS CI packaging remains deliberately paused pending its own human verification.

## New features to check on Mac

Queue Windows features here for Mac follow-up. Once the Windows implementation
lands, pull its referenced commit on the Mac. Shared Python code
should normally work on both systems; change platform-specific code only if the
Mac check reveals a difference. Keep the Windows and Mac results separate.

- [ ] **M01 — Sustained large-shrimp appearance (from U12).**
  - Windows reference: U12 above; implementation commit **pending**. The behavior
    has been proposed but has not yet been changed or verified on Windows.
  - [ ] Pull the U12 implementation commit and run its timing test on Mac.
  - [ ] In the packaged Mac app, check delayed appearance during sustained poor
    posture, smooth recovery, brief score fluctuations, Reduce motion, and
    immediate hiding on pause, away, camera loss, calibration, and breaks.
  - [ ] Record any Mac-only overlay or permission issue here, along with the fix
    commit and a final live-camera result. Check M01 only after that result passes.

## Landing page

- [ ] **W01 — Finish landing-page interaction and device verification.**
  - Desktop/mobile layout, copy, contrast, and motion were refined using
    apple-design and emil-design-eng. See the [change notes and captures](audits/landing-2026-10-16/CHANGES.md).
  - Passed: 320/390/768/1440 px overflow checks, images, internal anchors,
    reduced motion, JavaScript-disabled rendering, and reveal-script self-checks.
  - Remaining: physical-phone checks, complete keyboard/screen-reader interaction,
    and the live GitHub release/download flow. Refresh app screenshots when the
    desktop UI redesign ships.
  - Complete when: those remaining interaction/device checks pass and the page
    accurately represents the shipped desktop UI.
  - Files: `docs/index.html`, `docs/styles.css`, `docs/script.js`.

## Verification baseline

These checks already passed; they are context, not outstanding tasks:

- Current native Windows automated suite: **460 tests pass**, including compact HUD visibility/error expansion and saved menu choice, neutral keyboard-accessible disclosures and compact calibration details visibility, first-run deferral and keyboard actions, explicit calibration completion/start handoff, shared camera lifecycle/calibration status, standalone preview pause preservation and cleanup, worker replacement and stale-frame rejection, pointer feedback, named/keyboard-accessible utility icons, main/Settings navigation and Dashboard refresh, tray state/timing summaries, visibility synchronization, setup override routing, inline suggestion editing, break countdown/early end, observed-time reminder/snooze, prompt positioning and lifecycle guards, preparation/sample exclusion, paused capture clocks, recovery through verification, calibration-panel actions/cancellation, HUD sizing/interaction, main-window/tray integration, modeless Settings, single-instance locking, Windows power notifications, same-frame mode comparison, landmark confidence/geometry, preview cleanup, timing, gap exclusion,
  legacy-database preservation, additive writes, and daylight-saving regressions.
- The original 60 tests passed before fixes; they did not cover those integration bugs.
- Camera 0 opened at 640 × 480 through DirectShow on this Windows machine.
- All 31 paced inference samples returned frames with face and pose detections.
- Median inference times were roughly 20–28 ms across the tested rates.
- Preview frames were delivered. All tested workers stopped within four seconds.
- An invalid camera index reported an error; switching the test worker to
  camera 0 recovered and delivered frames.
- Camera 0 reopened successfully after the tests. Test camera handles were
  released; no images, video, or posture history were saved by those tests.
- After directory cleanup, JavaScript syntax, ten local website asset references,
  page anchors, and the moved camera diagnostic tool's help command passed.

This list is based on the reviewed paths and short local checks, not an exhaustive
audit of every app feature, operating system, or device.
