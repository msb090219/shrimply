# Mac full-screen overlays and CPU baseline — 19 October 2026

## Report and fix

The user reported that the floating metric disappeared over full-screen Terminal
and some other apps. The overlays had Qt's always-on-top tool flags, but no native
Space collection policy. Always-on-top alone does not configure membership in a
different app's full-screen Space.

The metric and floating shrimp now configure their native NSPanel after each
show: join all Spaces, full-screen auxiliary, and (on macOS 13+) join all
applications. Conflicting primary/auxiliary and move-to-active-Space flags are
cleared, preserving unrelated behavior. Window level and input handling are kept.
The helper is inactive on other operating systems and non-Cocoa Qt backends.

Apple documents [fullScreenAuxiliary](https://developer.apple.com/documentation/appkit/nswindow/collectionbehavior-swift.struct/fullscreenauxiliary)
and recommends [canJoinAllApplications](https://developer.apple.com/documentation/appkit/nswindow/collectionbehavior-swift.struct/canjoinallapplications)
for floating windows and overlays joining other apps' full-screen Spaces.

Native Cocoa checks on this Mac report both windows as QNSPanel, collection
behavior 262401, level 8. Automated checks cover native flags after show and
reshow, exclude conflicting flags, and preserve the shrimp's click-through
behavior. They do not switch the user's Spaces or automate Terminal.

Full regression suite: **480 passed, 1 skipped**, three existing deprecation
warnings. After installing the updated packaged app, the user confirmed that the
floating metric now stays visible over full-screen Terminal.

The rebuilt copy is installed at `~/Applications/Unshrimp.app`. Strict ad hoc
signature verification passes, as does its
[packaged Qt/models/inference smoke check](packaged-smoke.json). It was reopened
without diagnostic logging. The prior installed build is retained under
`~/Library/Caches/Unshrimp/app-backups` for rollback.

## Explicit Quit

During installation, the user chose Quit. Capture stopped and SQLite storage
closed, but the old process stayed alive. The close-to-tray dashboard rejects
window-close events, which can also cancel Qt's `quit()` request on Mac. The Mac
controller now calls `exit(0)` after `shutdown()` succeeds. Pending settings and
worker completion are still handled first. Other platforms keep their current
quit path.

Regression checks cover Mac/Windows exit routing and the existing deferred-storage
shutdown path. A native Cocoa check with the production dashboard close handler
confirms that explicit Quit returns zero rather than remaining in the event loop.
The already-shut-down prior process was then terminated before replacing files.
The updated package subsequently logged camera recovery, posture scoring and a
clean `app: exit 0` at 07:47:11.

## CPU observations

- User's Activity Monitor snapshot: **23.3% CPU**, packaged app PID 21805.
- Three later five-second process CPU measurements: **13.37%, 14.75%, 10.37%**.
  See [cpu-samples.json](cpu-samples.json). These are CPU time divided by elapsed
  time, expressed relative to one logical CPU; the Mac has eight logical CPUs.
- The app was still running its previous build with numeric diagnostics enabled.
  No inference rates or camera settings were changed for these measurements.
  These samples are a baseline, not a measured optimization or battery benchmark.
- Recent diagnostics showed mostly four inference passes per second, with brief
  two-pass periods. The existing policy uses four while drifting/bad, one after
  sustained comfortable posture, and half a pass per second while away.
- A short native process profile includes model inference and OpenCV image-copy
  work. Many worker threads are waiting. This does not isolate all CPU costs or
  justify claiming that a particular optimization has reduced consumption.

## Remaining checks

- Wider full-screen app and external-display coverage beyond the user's Terminal check.
- Longer tracking/paused/idle CPU and energy comparisons under matching conditions.
- Actual five-minute idle camera shutdown remains unverified in the packaged app;
  earlier logic and injected-idle checks are separate evidence.
- User reports sleep/wake working; the detailed lid/lock/display matrix remains open.

Windows releases are unchanged. All development changes remain on the Mac branch.
