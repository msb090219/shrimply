# Mac camera investigation — 19 October 2026

Status: resolution reconfiguration isolated as a reproducible trigger; Mac fix
passes repeated full UI transition tests. Longer normal-use acceptance remains.
Final automated suite: **505 passed, 1 skipped** (Windows native delivery test).
User reports the camera light flickering while capture tries to activate.
The installed app was quit for isolated live tests and has not been replaced.
No captured images were saved; reports contain counts/timings only.

## Culprit isolated in the follow-up

`tools/probe_macos_camera.py` opens the raw OpenCV AVFoundation capture on a
QThread, reads before resolution setup, optionally requests 640 × 480, and reads
three more frames. No posture models or Unshrimp windows are involved.

- [Resolution setup enabled](camera-probe-sized.json): all 12 opens supplied a
  valid 1280 × 720 frame before setup. Cycle 1 then failed all three reads after
  the width/height request (about one second per read). Other cycles succeeded.
- [Native resolution retained](camera-probe-native-size.json): all 16 opens and
  all 64 requested reads succeeded, including immediate thread replacement.
- The previous matching-size guard could not prevent this: the camera starts
  at 1280 × 720, so every requested 640 × 480 session still changed its settings.

The failure boundary is the live output-size change in OpenCV's AVFoundation
path. This identifies a trigger independently of model loading, UI policy or
permissions; it does not establish which Apple/OpenCV internal defect causes it.

On Mac, `open_camera` now leaves native output settings intact and returns a
small capture adapter that resizes frames to the requested dimensions in memory.
Windows still configures capture dimensions through its existing backend.
Frame readiness checks and visible persistent-error handling remain intact.
The adapter preserves failed reads, frame dimensions and underlying release;
an automated regression check exercises those behaviours.

The first full UI test passed without unexpected camera errors or hidden startup
retries. Repeat opens delivered previews in about 0.81–0.82 seconds and scored
frames in about 2.49 seconds; scoring retains its exposure warmup. The repeated
full UI report is recorded alongside the first. Both exercise preview, real
inference/calibration cancellation, pause/resume, closing/reopening preview,
intentional invalid-device error and recovery. No real settings/history changed.

The rebuilt Mac candidate also passed its Qt/model/inference smoke check. A third
full live UI sequence passed after checking all 11 relevant bundled modules
against source and using bundled models. That checker still hosts the UI in a
source Cocoa process; it does not replace normal use of the packaged executable.
All three fixed UI runs recorded zero unexpected camera errors and no power
events. The separate candidate is `dist/macos-parity/Unshrimp.app`; the installed
copy and existing Windows release artifacts were not replaced.

## Earlier investigation (before the resolution fix)

## Observations

- Original preview-only first frames: 4.33, 3.35, 3.33 seconds. Skipping the
  exposure-settling delay for preview-only: 2.31, 1.82, 1.80 seconds. Tracking
  and calibration retain exposure settling before scoring. These are short
  local measurements, not a general hardware performance guarantee.
- Three basic tracking opens delivered first scored frames in 4.19, 3.54,
  3.61 seconds. Model setup contributed only about 0.20–0.25 seconds.
- Mixed calibration/preview/tracking/pause/retry transitions reproduce sessions
  that OpenCV considers open but supply no frames. Holding the display awake
  still reproduces the issue, with no production power-monitor events recorded.
- One full transition run passed after first-frame validation. Its repeat and
  the subsequent size-guard run failed the strict no-unexpected-errors assertion:
  two consecutive empty starts triggered visible error, then recovered. A pass
  must not hide an error just because a later retry delivered frames.

## Changes and limits

`open_camera` now requires a real first frame before loading models. An empty
session is released after a two-second readiness window (a native read may run
past that deadline). The worker retries startup readiness failures after 0.5s;
one initial retry stays in the starting state, persistent failures remain visible.
Established stream outages retain their existing error handling. A small sleep
avoids busy-spinning on backends whose failed reads return immediately.

Worker replacement waits nonblockingly for complete native thread teardown and
ignores stale finished signals. Matching capture dimensions avoid redundant
stream configuration. Neither guard established a cure for the native failure.

Packaged startup now retains Matplotlib's font cache by bundle location instead
of rescanning system fonts every launch. Two smoke runs before the final camera
guard rebuild took 24.68s (cache creation) and 2.25s (cache reuse), respectively.
Both passed Qt/model/inference smoke checks; these do not exercise live capture.

The [OpenCV backend](https://github.com/opencv/opencv/blob/4.11.0/modules/videoio/src/cap_avfoundation_mac.mm)
marks sessions opened without requiring a successfully retrieved frame.
[Upstream reinitialization issue](https://github.com/opencv/opencv/issues/27294)
describes another Mac false-open case involving physical reconnects; it does
not prove the same cause here. [Qt documents](https://doc.qt.io/qt-6/qthread.html#isFinished)
that thread cleanup can outlast the finished signal.

The follow-up above supersedes the unresolved diagnosis in these earlier runs.
Longer use, physical disconnect and packaged normal-use acceptance remain
outstanding; short repeated passes cannot prove all camera hardware reliable.
