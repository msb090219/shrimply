# Windows packaged lifecycle verification

16 October 2026, Windows 11 build 26200, camera 0. Current working source includes
T01–T07, T08 confidence/geometry guards and diagnostic rejection reasons. T08
physical occlusion rejection remains unresolved. This is an uncommitted working
tree build, not a tagged release or clean-machine installation.

## Build and smoke

```
.\.venv\Scripts\python.exe -m PyInstaller unshrimp.spec --noconfirm --clean --distpath dist/lifecycle-check --workpath build/lifecycle-check
```

Build exited zero. Executable: `dist/lifecycle-check/unshrimp/unshrimp.exe`.
SHA-256: `b2d9a5f6f03480eedba4b9eb921df8c1766a7b18bfc531e6d8fe40d33caf49a7`.
This separate output preserves the older `dist/unshrimp` build.

Packaged `--smoke-test` exited zero. Report:
`diagnostics/packaged-lifecycle-smoke.json`: version 1.1.4, `frozen: true`,
`ok: true`, icon decoding, both models loaded, native synthetic inference passed.
The build warned about optional `cv2.typing` import (`GMat` unavailable); runtime
smoke inference passed despite that warning. This does not exercise every OpenCV
feature. No camera was opened by smoke mode.

User confirmed previous Unshrimp fully closed. Launched this executable with
`--diagnostics` at 22:49:23 local, PID 20660. Log:
`%APPDATA%/Unshrimp/diagnostics-1792144163345753400.log`.
Saved baseline loaded; tray available and vision samples observed. Initial
samples had missing detection, so startup alone is not an accuracy pass.

## Manual checks

- First pause/resume cycle: user confirmed physical light off/on as expected.
  Log records pause at 22:50:44 and resume at 22:50:48; usable inference resumed.
  No camera error was found in this cycle.
- Repeated cycles: user confirmed five additional successful cycles with the
  camera light following pause/resume and no freezing. Log records five pairs
  from 22:51:32–22:51:57, plus the first pair above (six total). Usable inference
  observed afterward; no logged camera error. Last observed state is active,
  so explicit pause is still needed before the paused sleep test.
- Quick resume during pending shutdown: pending.
- Sleep/wake while paused: one user-confirmed cycle passed. User reports pause
  preserved, camera light off after waking, and responsive tray menu. Pause logged
  at 22:56:22; log ends there with no subsequent vision samples or resume event
  at inspection. Same PID 20660 remains responsive. Sleep itself is user-reported;
  Windows power-event timestamps were not independently collected.
- Sleep/wake while tracking: pending. User reported being unable to move the
  posture metric and then closed the app. Log ends with clean `app: exit 0` at
  22:59:35; original process no longer present. No crash inferred. Timing relative
  to sleep/wake and reproduction of the movement issue need clarification.
- Lock/unlock, idle-stop, repeated sleep cycles: pending.
- Active sleep/wake on the reopened original build failed: user reported camera
  stayed off after wake while tray responded; manual Pause/Resume restored it.
  PID 39964, log `diagnostics-1792144838656097200.log` contains manual pause/resume
  at 23:06:43/23:06:46 and usable inference afterward; no earlier camera error.
  Quit logged at 23:09:03. The exact driver behavior is not established by logs.

No images or video are saved by diagnostics. This short session cannot establish
long-session stability, battery use, clean-machine compatibility, or release readiness.

## Wake recovery fix (hardware retest pending)

Source now registers Windows suspend/resume notifications on the HUD native
window via Qt's native event filter. Suspend requests asynchronous worker stop,
clears pending restart and stale smoothing/history continuity. Resume requests
replacement through the existing worker-finished path. Manual pause and idle-stop
still prevent capture. The follow-up RESUMESUSPEND notification is ignored;
repeated RESUMEAUTOMATIC messages can still request another serialized restart.
The old worker must finish before a replacement starts; a permanently blocked
native driver read is not forcibly terminated by this change.

References: [Windows registration](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registersuspendresumenotification),
[Qt native filtering](https://doc.qt.io/qt-6/qabstractnativeeventfilter.html).

233 tests pass, including real Windows registration and synthetic native message
delivery, active versus paused/idle policy, suspended-frame exclusion, delayed
worker completion, and quitting. Synthetic messages do not establish actual
driver recovery after sleep. Rebuild and repeat active and paused sleep/wake
before calling the hardware defect fixed.

Updated executable built successfully at `dist/lifecycle-wake-fix/unshrimp/unshrimp.exe`.
SHA-256: `d1541278bb3e7b5d4270abd28448500ed7ec877628dea9e04dd298d286318839`.
Packaged smoke passed (exit 0, frozen true, icon/models/native inference), report
`diagnostics/packaged-wake-fix-smoke.json`. User confirmed previous instance quit;
new build launched with diagnostics, PID 16504. Actual sleep/wake retest pending.

Active sleep/wake retest passed once on the wake-fix build: user confirmed camera
returned automatically. Log `diagnostics-1792145469513363600.log` records suspend
23:14:42, resume 23:15:24, first usable vision measurement 23:15:27. No manual
Pause/Resume was logged between these events. This is one successful physical
cycle; paused behavior on the new handler and repeated sleep cycles still need
verification. The earlier paused pass predates this handler.

## Single-instance protection

Startup now takes a per-user `instance.lock` in the app data directory before
config migration, log creation, controller construction, or camera access. A
second normal launch shows an already-running message and exits. Permission and
other lock errors stop startup with an error. The owner holds the lock until
shutdown; age-based expiry is disabled for long sessions. Qt can reclaim a lock
left by a dead process. Smoke mode remains separate, without camera/config access.
Source and packaged builds use the same path; older builds lacking the guard
cannot be prevented from launching and must be closed before upgrading.

236 tests pass, including actual competing processes, duplicate startup before
shared-state access, old timestamp on a live lock, dead-owner recovery, and lock
permission errors. Packaged duplicate-launch verification pending.

Protected build: `dist/lifecycle-single-instance/unshrimp/unshrimp.exe`;
SHA-256 `587a8ae4fe41b9531121b0bb5a717fb5b7c2e4d89da65fec71c7ae7853f9bfb4`.
Build and packaged smoke passed (exit 0, frozen true, icon/models/native inference),
report `diagnostics/packaged-single-instance-smoke.json`. Primary PID 13648 owns
the per-user lock and produces usable inference in
`diagnostics-1792145953117657000.log`. Attempted second launch PID 14264;
user confirmation of message and acknowledgment is pending.

Duplicate test limitation: primary 13648 quit cleanly at 23:21:10 and released
its lock. Duplicate 14264 remained waiting; user saw only one app and no message.
The test used `Start-Process -WindowStyle Hidden`, so the modal notice may have
been hidden by the test launch. Do not count visible feedback/acknowledgment as
passed. The duplicate did not acquire the lock, start a diagnostic log, or take
over when the primary quit. Verified its executable path and stopped only that
test process, then relaunched the primary. A user-initiated Explorer launch is
needed to verify normal foreground notification behavior.

User then launched the protected executable normally through Windows and confirmed
the expected message ("Use the shrimp icon in the system tray..."). Visible
duplicate-launch feedback is verified. The original continued running and was
subsequently used for the paused sleep test below. Explicit second-process exit
after clicking OK was not separately measured in that manual launch.

Paused sleep/wake on the updated handler passed once: user reports "Still paused".
Primary PID 18860 remains responsive and owns the lock. Log
`diagnostics-1792146112591542800.log` records pause at 23:28:41, suspend at
23:28:49, and resume at 23:29:06. No vision samples or manual resume follow the
pause through inspection. The handler therefore preserved pause without restarting
capture. Physical camera-light behavior after this specific wake was not separately
confirmed beyond the earlier explicit paused test. Active and paused wake paths
have each passed once; repeated cycles, lock/unlock, idle-stop, and longer use remain.

## Automated real sleep/wake on the verified Settings-fix build

User requested automation instead of further manual cycles. Verified only PID
37816 was running from `dist/settings-fix`, owned the lock, and had active usable
inference. `powercfg /a` reports S0 Low Power Idle (network connected), not S3.
Machine was on AC power; existing AC wake timers enabled, DC disabled. No power
plan setting changed.

Armed a temporary resumable waitable timer for 25 seconds, then called
`SetSuspendState(False, False, False)` (sleep, no force, wake events enabled).
Timer canceled/handle closed afterward. Evidence:
`diagnostics/automated-sleep-wake.json`. Suspend API succeeded and timer wait
returned signaled. Started 10:43:42.578 UTC, returned 10:45:08.943 UTC (about
86 seconds). The requested 25-second wake was not achieved as an observed
interactive return. `powercfg /lastwake` reported "Presume Wake Timer" owned by
the test Python executable; no claim of precise firmware wake timing is made.

App log `diagnostics-1792147237729437400.log`: suspend notifications at 23:43:44
and 23:43:49, resume at 23:45:08 and 23:45:09. First usable inference at 23:45:14,
about six seconds after the first resume, followed by continued usable inference.
No manual Pause/Resume or logged camera error. Same PID remained responsive.
Active real sleep/wake recovery passed on the verified fixed build.

Repeated native suspend/resume notifications were observed. Restart requests
remain serialized through worker completion, but can cause unnecessary repeated
reinitialization. This run does not establish exact restart count. Physical
indicator, actual mouse dragging, and paused sleep were not automatically checked
in this cycle. No images/video saved, and no settings or OS security policies changed.
