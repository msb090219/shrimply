# Shrimply Mac feature parity and Windows isolation

21 October publication: [joint Windows/Mac beta](https://github.com/msb090219/shrimply/releases/tag/v1.3.0).
Windows uses `1f0253f`; the verified Intel Mac uses `acdad79`. Source branches
and build artifacts remain separate. Older staging statuses below are historical.

Rebrand update: the Shrimply U21/M12 handoff is integrated from Windows
`e16ef8a` through `1f0253f`. Current imports/spec/app identity use `shrimply` /
`Shrimply.app`; data migrates from Unshrimp and the old folders are retained.
The Unshrimp paths and build results below are historical evidence. Current
release staging and remaining checks are recorded in the
[rebrand audit](audits/shrimply-macos-rebrand-2026-10-20/README.md).
The current Intel ZIP is `dist/macos-release/shrimply-macos-x86_64.zip`;
573 tests passed (2 Windows-only skips), strict signatures and extracted frozen
inference passed. This unsigned beta requires macOS 15.0 or later. It is installed at
`~/Applications/Shrimply.app`, with the old app backed up and user data retained.

20 October feature update: Windows 1.3.0 handoffs M01–M11 are integrated in the
Mac working tree, preserving native behaviour, camera fixes and quiet posture
notifications. The new candidate is `dist/macos-features/Unshrimp.app` (Intel,
1.3.0). The full Mac regression suite passes **548 tests, 2 Windows-only checks
skipped**; native window/preference/overlay checks and packaged inference smoke
pass. [Integration details and screenshots](audits/macos-features-2026-10-20/README.md)
distinguish implementation from remaining physical/packaged acceptance.
The verified 1.3.0 candidate is now installed at `~/Applications/Unshrimp.app`;
the prior app and Mac source state are archived under `dist/install-backups/`.

Reviewed against the local checkout on 19 October 2026. The latest pass adds
native Cocoa automation with isolated settings/history; it does not replace
hands-on packaged acceptance.

20 October installation update: continued posture notifications were traced to
the old installed app, whose embedded code still contained posture/recovery
toasts. The installed `~/Applications/Unshrimp.app` has now been replaced with
the current Mac candidate (including the camera resolution fix), after archiving
the old app under `dist/install-backups/`. Installed signature verification
passed; the controller/tray suite passed 101 tests. Earlier statements below
about leaving the installed app untouched describe the 19 October work only.
The incoming Windows v1.3.0 code still has posture toasts; integration must retain
the Mac quieter policy.

## Build and release separation

- Current branch: `macos-development`. Local `main` and its remote-tracking
  reference remain at `a663068`; the Mac branch's last commit is `9c7d84e`.
  The current Mac implementation is largely uncommitted working-tree changes.
- One shared Python codebase produces separate native packages. Mac-only code
  uses platform/backend guards and conditional dependencies. This is not a
  second independent repository or an independent product version sequence.
- The latest parity-pass Intel app is `dist/macos-parity/Unshrimp.app`. Building it did
  not replace the installed app or any Windows executable/download.
- `tools/build_win.ps1` is unchanged. The Windows release workflow now requires
  the tagged commit to be in `main` history and refuses to replace existing
  release assets. These local workflow changes have not run on GitHub yet.
- A separate `macos-build.yml` workflow builds Intel and Apple Silicon apps,
  checks signatures/inference and uploads architecture-specific Actions
  artifacts. It runs on Mac-branch pushes or manual dispatch and has read-only
  repository permissions. It does not publish releases. These jobs still need
  to run on GitHub before either architecture is CI-verified.
- Windows retains `v*` release tags. Reserve `mac-v*` for future Mac releases;
  those do not match the Windows workflow. Mac release publication and
  signing/notarization are still unfinished. No release was published or
  uploaded in this session.
- Existing Windows artifacts are unaffected by local source edits. A future
  Windows build from this working tree would include shared changes and needs
  real Windows validation before merging/releasing. Checking out another branch
  with these uncommitted edits is not an isolation mechanism.

## Feature coverage

| Feature | Mac implementation | Remaining acceptance |
| --- | --- | --- |
| Camera capture | AVFoundation, permission-specific errors, native capture format with in-memory resizing to avoid startup stalls | Longer packaged use, other cameras/permission states |
| Camera selection/rescan | AVFoundation device names; rescan avoids opening capture | Multiple physical cameras and disconnect/reconnect |
| Calibration and posture scoring | Shared calibration, models and scoring; Mac disclosure controls | Packaged calibration was user-confirmed; broader poses, lighting and interruption checks remain |
| Dashboard and history | Quote/progress Dashboard, SQLite history, weekly chart and calendar up to 26 weeks | VoiceOver, broader scaling and packaged walkthrough |
| Settings | Embedded page, collapsible main sidebar, horizontal categories, Mac fonts/shortcuts and autosave | Broader packaged keyboard/accessibility/control walkthrough |
| Tray/menu controls | Native menu-bar menu; duplicate popup fixed | Single-menu behaviour was user-confirmed |
| Application menus | About, Settings, Quit, Close and Minimize with Mac shortcuts; Command-W added to About/Welcome and standalone previews | Native About/calibration close policies verified; remaining normal-use focus checks |
| Alerts and sound | Qt tray notification request and application beep | User confirmed both test notification and sound in the installed Mac app on 19 October; Focus/system suppression remains OS-controlled |
| Break reminders | Shared detected-sitting timer, break state, Later/Skip and editable suggestions | Full packaged reminder walkthrough and sleep/pause accounting |
| Floating meter/cue | Horizontal/vertical meter, shrimp/text cue, hold times, entrance choices; native Space handling and repaint optimisation | Native flags verified for both orientations/styles; broader full-screen apps, external displays and legibility remain |
| Pause/preview/recovery | Shared controller and worker; independent paused preview | Separate short preview runs pass; longer reliability and physical camera-light checks remain |
| Idle shutdown | Core Graphics system-idle API, shared five-minute policy | Actual five-minute packaged shutdown/return remains deferred |
| Sleep/lock/session handling | Cocoa workspace observers with overlapping suspension reasons | Injected native tests pass; user reported sleep/wake working; detailed lid/lock/paused/calibration/display matrix remains |
| Login startup | Per-user LaunchAgent instead of Windows registry startup | Real logout/login, quiet launch and disabling afterward |
| Local data/support | Application Support storage; data-folder opening through Qt | Packaged Finder opening and persistence walkthrough |
| Single instance/activation | Shared Qt lock and local socket; Mac Quit exits after cleanup | Packaged duplicate-launch/focus and repeat relaunch acceptance |
| Appearance/themes/motion | Shared controls, Mac system font, reduced-motion/static timer handling | Device theme changes, multiple display scaling, keyboard/accessibility and visual acceptance |
| Packaging | Intel `.app`, ICNS, camera usage text, version metadata, ad hoc signature | Apple Silicon, clean/quarantined installation, Developer ID/notarization and dedicated release workflow |

The Mac suite passed **488 tests, 1 skipped**. The skipped test requires real
Windows native message delivery. Windows routing is also covered with mocks, but
running tests on Mac does not replace a Windows regression run.

## Latest native parity checks

`tests/test_macos_features.py` runs in a separate Cocoa process. It verifies:

- Command-W closes About and standalone camera preview (including its refresh
  timer), routes active calibration to cancellation, and closes completed
  calibration feedback.
- Quiet paused startup leaves the dashboard hidden and the worker stopped.
- Local-socket activation opens the existing controller's dashboard.
- All four Settings pages are reachable; edited alert delay, break timing,
  appearance and meter size persist through the real save/controller path.
- Login startup can be enabled/disabled through Settings against a temporary
  LaunchAgent path; the user's actual startup configuration is untouched.
- Closing the dashboard leaves the controller available. Synthetic timed history
  persists after shutdown and database reopening.

The focused native/startup run passed **6 tests** after adding the integrated
checks. No camera capture was started, and no real settings/history were edited.
The startup tests also cover source/packaged paths containing spaces and confirm
that the Mac registration path never calls the Windows registry.

Windows/Intel/Apple Silicon CI is now configured for pushes to
`macos-development`. The runner labels follow [GitHub's runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Workflow YAML parses locally, and the ancestry guard was checked against local
`main` (accepted) and the current Mac branch (rejected). Remote execution remains
pending; local parsing is not a CI pass.

Qt already provides a Mac tray notification path; a separate notification
backend has not been added. [Qt's notification documentation](https://doc.qt.io/qt-6/qsystemtrayicon.html)
does not establish delivery on this user's configured desktop by itself. The
user confirmed both notification and sound delivery in the installed Mac app.
The subsequent quieter-notification change reserves popups for camera problems,
uses the shrimp icon, and leaves posture/recovery feedback to the meter/shrimp
and optional chime. Calibration guidance/results stay in the calibration window;
breaks retain their separate card. That change passes **492 tests, 1 skipped**.

The earlier Intel parity build passed strict ad hoc signature verification and the
[packaged Qt/models/inference smoke check](audits/macos-parity-2026-10-19/packaged-smoke.json).
That test predates the quieter-notification change and does not start capture
or replace normal-use acceptance. The local app at `dist/macos-parity/Unshrimp.app`
has been rebuilt successfully for the quieter policy. No existing installed app
or Windows release was replaced.

## Verification order before more optimisation

The camera investigation now passes **505 tests, 1 skipped**. A raw capture probe
isolated live resolution reconfiguration as a trigger for empty camera sessions;
retaining native Mac capture settings and resizing in memory passes full native
UI transitions. Longer use and other cameras still need acceptance; see the
[camera evidence and remaining work](audits/macos-camera-2026-10-19/README.md).

1. Packaged feature walkthrough: calibration, dashboard/history, all Settings,
   notifications/sound, break reminders, data folder, pause/preview, duplicate
   launch and Quit. Record observed results rather than marking implementation
   as acceptance.
2. Login startup and lifecycle/display scenarios, including the deferred idle
   check when the user is available.
3. Investigate intermittent camera capture failure and complete longer runs.
4. Validate shared changes on Windows, including packaging and native lifecycle
   checks, before merging or releasing them for Windows.
5. Establish separate Mac publication conventions/workflow and finish signing,
   notarization, Apple Silicon and clean-machine checks.

Evidence: [Mac Settings](audits/macos-settings-2026-10-18/README.md),
[packaged app](audits/macos-packaged-2026-10-19/README.md),
[full-screen/Quit](audits/macos-fullscreen-2026-10-19/README.md),
[performance](audits/macos-performance-2026-10-19/README.md).
