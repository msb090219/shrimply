# Windows verification

This procedure checks behavior before the UI redesign. Automated tests use fake
cameras; hardware checks must be recorded separately. No tool here saves camera
images or video. Diagnostic logs contain numerical scores, timing, and errors.

## Automated baseline

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The regression suite covers returning from Away using the real rate policy,
camera selection while paused/idle, waiting for worker shutdown before replacing
it, processing failures and cleanup, calibration sample ordering and verification
coverage, tuning that preserves the demonstrated hunch, and recovery notifications.

## Short camera check

Close Shrimply and other camera apps first. This opens camera 0 four times, at
0.5, 1, 2, and 4 fps. Each rate runs for eight seconds, including startup.

```powershell
.\.venv\Scripts\python.exe tools/check_camera.py
```

Use `--camera 1` for another device or `--seconds 15` to allow slower startup.
Reports are written under `diagnostics/`, which Git ignores. A passing report
means frames arrived without reported worker errors, each worker stopped within
four seconds, and the next cycle could open the camera. It does not prove posture
accuracy, physical camera-light behavior, or long-session stability. Inspect
delivery gaps as well as the pass flag; a delivered frame may still be stale.

If a native driver blocks indefinitely, the check waits instead of destroying a
running thread. Record this as a failure; do not unplug devices during this short
baseline check. Disconnect/reconnect is a separate supervised test below.

## Camera status and framing preview

After rebuilding the executable, quit the ordinary app and run:

```powershell
.\.venv\Scripts\python.exe tools\verify_camera_ui.py --camera 0
```

This uses the real webcam and bundled models in an isolated Qt test host. It
checks that the packaged camera/UI modules match source, then exercises paused
preview, resume, preview closure, an unavailable device, Retry, and repeated
pause/reopen. It saves only counters/timings and results under `diagnostics/`;
settings and test history are temporary. It does not record frames or measure
posture accuracy. A built-in camera cannot be physically unplugged; a missing
camera index is an open-failure simulation, not a physical/driver failure test.
Interactive executable behavior and native Windows DPI still need desktop checks.

## Guided posture session

Launch the real app with additional diagnostics:

```powershell
.\.venv\Scripts\python.exe main.py --diagnostics
```

For a packaged build use `shrimply.exe --diagnostics`. The log path is printed
at startup; Windows logs are in `%APPDATA%\Shrimply\diagnostics-*.log`. Each run
gets its own file. Normal launches retain the existing, less detailed logging.
Detailed logs grow throughout the run: use them for testing, then quit the app.

1. Record the camera, lighting, display setup, sensitivity, and alert delay.
   Keep camera position fixed and complete a fresh calibration.
2. Sit normally for 60 seconds. Record unexpected drifting/bad states and alerts.
3. Demonstrate the calibrated hunch for the configured alert delay plus 15 seconds.
   Record when the movement started, when the state changed, and when the alert arrived.
4. Return to normal for 20 seconds. Record the recovery delay and any contradictory messages.
5. Turn your head left and right, then face forward. Check that turned-head frames
   are not scored as a slouch and that tracking resumes afterward.
6. Leave the chair for at least 20 seconds, then return. Away should appear and
   scoring should resume after a few usable frames. Record timing rather than
   assuming every machine has the same detection delay.
7. Cover the camera, partially obscure shoulders, and change lighting separately.
   Record false scores, tracking loss, and recovery. Required-landmark confidence
   gating is implemented, but a covered ear remained highly confident in the
   local test; confidence alone does not establish that a landmark is visible.
8. Repeat the sequence three times. Repeat on other supported cameras when available.

Use this record format (manual timestamps can be matched to the diagnostic log):

| Time | Action / expected result | Observed state / alert | Delay | Pass / fail / notes |
|---|---|---|---|---|
| | | | | |

Report missed sustained hunches, unexpected alerts while sitting normally, and
detection/recovery delay. Successful face/pose detection is not classification
accuracy. New history uses bounded elapsed observed time. Older sample-based
percentages are marked `~` and must not be treated as elapsed-time measurements.
Use the updated source version for T06; earlier packaged builds retain the old logic.

## Windows lifecycle session

For a short numeric landmark check, pause Shrimply and close its preview to release the camera, then run:

```powershell
.\.venv\Scripts\python.exe tools/vision_demo.py --seconds 8 --camera 0 --preview --report diagnostics/landmark-check.json
```

Use a fresh report path for each condition. No images/video are saved.
In the preview, confirm framing,
then press Space to start measuring; Escape cancels. Without `--preview`,
measurement starts immediately. Exit 0
means at least one frame was accepted; exit 2 means none were accepted, which can
be the expected result for an occlusion test. Inspect counts and confidence in
the report rather than treating the exit code as an accuracy verdict. Compare
the `rejection_reason` for rejected frames; coordinate/framing failures name
the required point. Older reports lack this field. Compare
normal sitting, a single controlled obstruction, and normal sitting again.
The app remains paused until the user resumes it.

To compare pose tracking with independent detection on identical frames:

```powershell
.\.venv\Scripts\python.exe tools/compare_pose_modes.py --camera 0 --seconds 8 --report diagnostics/pose-mode-comparison.json
```

Keep Shrimply paused. In the preview, press Space separately for `normal`,
`shoulder_out`, and `normal_return`. Each stage lasts eight seconds and both
models remain alive across stages, including preparation. Green markers show
VIDEO predictions; blue markers show IMAGE predictions. Escape cancels and saves
the completed/partial measurements. Exit 0 requires all three stages; exit 2
means cancellation/incomplete stages. Reports save required ears/shoulders' x/y,
visibility, and presence for both modes, with no frames. These are pose-only
predictions, not full posture classification or accuracy measurements. Camera or
model failures release resources and propagate an error; a report is not promised
for a failed run. Use the point coordinates to check framing independently of
confidence, and compare each mode's normal baseline and obstructed stage.

Save work in other applications before manually sleeping or locking Windows.
Keep one diagnostic run open and note each action's time. Do not change Windows
privacy or startup settings solely to pass a test.

| Scenario | Expected result |
|---|---|
| Pause with preview closed, then select/rescan cameras | No new capture starts. HUD may say stopping camera briefly. Once stopped, the camera light turns off. |
| Open preview while paused, then close it | Preview-only capture works without posture inference/history/sitting time. Closing it releases capture and preserves pause. |
| Pause with preview open | Normal tracking stops; the mirror continues in labelled preview-only mode. |
| Resume after selecting another device | Only the selected device opens; tracking resumes. |
| Pause/resume five times, including a quick resume during shutdown | No overlapping workers, freezes, or lost controls. |
| Start calibration while paused | The live preview and calibration inference work, while ordinary scoring/reminders stay suspended and the saved pause preference is retained. |
| No input for five minutes, then move the mouse | Camera stops for inactivity and reopens after input; check the physical indicator. |
| Idle-stop, then manually pause before returning | Input must not override manual pause. |
| Lock/unlock and sleep/wake while tracking | App remains usable; record camera behavior during lock and recovery after wake. |
| Lock/unlock and sleep/wake while paused | With preview closed, capture stays off. With preview open, sleep stops capture and wake restores preview only, preserving the tracking pause. |
| Privacy shutter or unplug/reconnect | Loss is reported and recovery does not freeze or overlap capture. |
| Teams/Zoom opens the same camera | Either sharing works or Shrimply reports a recoverable failure. Check again after the other app releases it. |
| Quit during active capture or retry | Process exits after resource cleanup; camera becomes available to another app. |

Repeat sleep/wake and device-loss scenarios three times. Native drivers vary;
automated mocks cannot establish these outcomes. Lock alone is not currently a
dedicated camera-off policy, so record its behavior rather than asserting one.

## Resource screening and full-day run

Start one app instance, then find its process ID in Task Manager's Details view.
For a source launch, select the Python process running `main.py`, not another
Python application. In a second PowerShell window:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/monitor_process.ps1 -ProcessId 12345 -Seconds 7200
```

Replace `12345` with that ID. The execution-policy override applies to this
PowerShell process only. No machine policy is changed. The sampler writes CPU,
working-set/private memory, handle count, and thread count every five seconds.
It refuses to overwrite an existing report; specify a new `-OutputPath` when
repeating a run against the same process ID.

For the two-hour screening run, include normal tracking, deliberate Away,
calibration preview, manual pause, and resume; note the transition times. Follow
with a representative working day (`-Seconds 28800`) after the screening passes.

CPU is expressed relative to one fully occupied core: values can exceed 100%.
Memory can rise during startup and model loading. Compare repeated equivalent
states after warmup; investigate sustained memory/handle/thread growth rather
than demanding identical readings. Preview and inference have different loads.
The sampler does not measure battery drain or prove that a leak cannot occur.

## Source and packaged smoke checks

The smoke mode skips normal app startup, config migration, history, and camera
capture. It decodes the icon, loads both real models, runs inference on a synthetic
black frame, closes the models, writes JSON, and exits with a success/failure code.
Use a fresh output filename for each run.

```powershell
.\.venv\Scripts\python.exe main.py --smoke-test diagnostics/source-smoke.json
.\.venv\Scripts\python.exe -m PyInstaller shrimply.spec --noconfirm --clean
Start-Process -FilePath .\dist\shrimply\shrimply.exe -ArgumentList '--smoke-test diagnostics/packaged-smoke.json' -Wait -PassThru -WindowStyle Hidden
```

Inspect the report: `ok` must be true, and `frozen` must be true for the executable.
The child exit code must also be zero. A source smoke pass cannot substitute for
the executable check. Run the packaged executable again on a clean Windows
account or machine without Python, including a path containing spaces.

After smoke checks, manually verify first-run onboarding, calibration, pause,
history persistence, relaunch, and startup registration on that clean machine.
Test duplicate launch too: the second launch should show an already-running
message, then exit when acknowledged without opening capture or changing the
first instance. The per-user lock precedes config/log/history startup. After a
clean quit, relaunch should work; stale locks from dead processes are reclaimed
by Qt. Older builds without this guard must be closed before these tests.
Do not rename or delete the user's real model/config/history files to simulate
damage; use a disposable copy and a separate Windows account.

## Completion record

Keep exact commands, report paths, app revision, Windows/camera details, and failed
cases. Mark hardware cases as pending until physically exercised. A clean-machine
pass and a working-day run remain required before declaring release readiness.
