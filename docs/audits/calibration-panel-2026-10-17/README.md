# Unified calibration panel

The camera mirror, named setup checks, phase progress, wrapping instructions,
and actions now share a standard desktop window. It uses the desktop theme
and coral progress accent. Default content size is 540 × 680 logical pixels.
The HUD no longer moves together with a separate frameless preview.

- [Camera setup](setup.png)
- [Capturing normal posture](capture.png)
- [Retry after an unsuccessful calibration](failure.png)

These are real Qt widget captures using a synthetic camera image, not live
camera evidence. Checks during capture are labelled as setup results.
Completion stops the preview and ignores late frames. Failure appears inline;
cancellation keeps the saved baseline and restores the previous paused state.
Reopening an active calibration raises its window without resetting the session.

Validation: 261 automated tests passed, including panel signals, wrapping,
frame cleanup, cancellation, and the setup-only override guard. This pass did
not change calibration scoring or capture timing, run live-camera calibration,
or rebuild the packaged executable. Preparation cues and tracking-loss guidance
were follow-up work at capture time; U02 is intentionally still open.

## Preparation and recovery follow-up

Each pose now starts with three seconds of preparation. No samples enter the
baseline during this cue. The window explicitly labels collection, or says
"Collection paused" with framing/head-direction guidance when a frame is
unusable. Preparation and capture time stop during loss; a camera-delivery
gap over two seconds is not counted when frames return. Valid samples already
collected are retained, and collection resumes automatically. Cancel remains
available throughout. Nominal capture durations and scoring formulas are
unchanged; total wall-clock duration can grow when tracking is interrupted.

268 tests pass, including preparation exclusion, every phase's paused clock,
delivery gaps, and complete prepared sessions interrupted during normal or
verification. These are simulated signals, not evidence of webcam accuracy.
Live-camera review of this updated flow is still pending.
