# Shrimply 1.3.0 — Mac beta candidate

Published with the [joint Shrimply 1.3.0 beta](https://github.com/msb090219/shrimply/releases/tag/v1.3.0) on 21 October 2026.
The staging and acceptance details below distinguish completed checks from remaining tests.

Shrimply is the new name for Unshrimp. The Mac app shares the Windows foundation
and includes its updated Dashboard/calendar, embedded Settings, collapsible
sidebar, shrimp/text cues, entrance/recovery timing, vertical meter and sitting
break reminders. Mac-native menus, login startup, sleep/session handling and
camera fixes are retained. Settings category tabs and suggestion actions have
also been aligned and refined.

## Package and installation

The staged Intel package is `shrimply-macos-x86_64.zip`, built for macOS 15.0 or
later and checked locally on Intel macOS 15.7.9. Python and separate posture-model
downloads are not required. An Apple Silicon package must be built and verified
separately; the Intel result is not native Apple Silicon verification.

This beta is not Developer ID signed or notarized. It has an ad hoc signature
for local execution. If macOS blocks an app you have chosen to trust, use Apple's
[instructions for opening an app from an unknown developer](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac).
Downloaded/quarantined-app behavior still needs a clean-Mac check.

1. Quit Unshrimp, if installed, from its menu-bar menu.
2. Extract the ZIP and move `Shrimply.app` into Applications (or your own
   `~/Applications` folder). Keep it there when login startup is enabled.
3. Open Shrimply and allow camera access when you choose to calibrate or track.
   The renamed bundle has a new identity; macOS may request permission again.
4. On a new profile, choose Calibrate now or Later. Later leaves the camera off.
   On an upgraded profile, saved pause and calibration settings are preserved.

## Upgrading from Unshrimp

Missing settings, calibration and history are copied from
`~/Library/Application Support/Unshrimp` into
`~/Library/Application Support/Shrimply`. Older OSA data is a fallback. Existing
Shrimply files are retained, and previous folders are not removed. Old/new
instance locks prevent the two versions running together during migration.

An enabled old Mac login registration is replaced with
`~/Library/LaunchAgents/com.msb090219.shrimply.plist`, targeting the new app.
Disabling startup removes both old and new registrations. No login registration
is created if startup was not enabled. Actual logout/login remains a manual check.

Closing the Dashboard keeps the app in the menu bar. Choose **Quit Shrimply**
or press **⌘Q** to stop it completely. Settings, history and calibration remain
on disk when the app is removed; the old data folders are also retained.

If you last calibrated with the earlier stretched Mac camera preview, recalibrate:
the corrected capture path preserves the camera's aspect ratio.

## Privacy and feedback

Camera frames are processed locally and are not saved. Settings and posture
history stay on this Mac. The bundled MediaPipe SDK sends performance/usage
metrics to Google, excluding camera frames. Shrimply is a habit reminder, not a
medical device; lighting, framing, movement and occlusion affect results.

Posture feedback uses the shrimp/text cue, meter and optional sound. Breaks use
their own reminder card. System notifications are reserved for camera problems.

For a bug report, include the app version, Mac architecture/macOS version, steps
and observed behavior. The local log is
`~/Library/Application Support/Shrimply/shrimply.log`; inspect it before sharing.
Camera frames are not included in that log.

## Staging checks and remaining acceptance

The automated suite covers legacy data/instance protection, Mac startup-entry
replacement, saved settings/baseline validation, camera lifecycle, calibration,
history and UI actions. Native Cocoa checks exercise a migrated paused profile
with its baseline and real SQLite history, plus fresh-profile Later behavior.
These source-host checks are distinct from actual packaged first use.

The local build script checks bundle identity/version/icon/minimum OS, matches
bundled project modules against source, verifies signatures, then tests model
inference after extracting the ZIP into a path containing spaces. SHA-256,
smoke and verification reports are produced beside the ZIP.

Before distribution, record the renamed packaged camera-permission/upgrade
walkthrough, clean-download launch, real login startup, hardware/lifecycle and
longer-use checks, and dependency distribution review. Apple Silicon remains
separate. Developer ID/notarization is deferred by choice for this unsigned beta.
The full checklist is [Mac testing](../MACOS-TESTING.md).

Publication was explicitly authorized for the joint Windows/Mac beta. The Mac build workflow has
read-only repository permissions and produces development artifacts; it does not
create a GitHub release or upload release assets.
