# Shrimply — private Mac beta check

Prepared locally for a first-friend test before the coordinated Windows/Mac
release. Nothing has been uploaded or published. Test results are pending.

Package: `shrimply-macos-x86_64.zip`, version 1.3.0, macOS 15.0 or later.
This is an Intel app, not a native Apple Silicon build. M-series use through
Rosetta is experimental and has not been tested. Record it separately from
Intel results. Apple's Rosetta instructions:
https://support.apple.com/en-nz/102527

## Installation

1. Record Mac model, Intel or M-series chip, and macOS version from About This Mac.
2. Obtain the exact built-app ZIP through the owner's chosen private transfer.
   Record the transfer method. A local copy alone does not establish browser
   download/quarantine acceptance. Do not use GitHub's source-code ZIP.
3. Extract it and move Shrimply.app to Applications. Quit Unshrimp first if present.
4. Open the app. This beta is not Developer ID signed or notarized. If you trust
   the supplied app and macOS blocks it, follow Apple's instructions:
   https://support.apple.com/en-nz/102445
   Record the exact warning and whether Privacy & Security → Open Anyway works.
   Report damaged-app errors rather than disabling system protections.

## First-use checks

On a new profile (do not delete existing data to create one):

- Welcome says Shrimply and explains setup/privacy. Choose Later: camera light
  stays off. Quit and reopen: setup remains available on the Dashboard.
- Choose Calibrate, allow camera access, check preview proportions and follow
  the upright, normal, slouch and verification instructions. Choose Start tracking.
- Sit normally, slouch and return upright: observe the posture cue and recovery.
- Try the sound/notification test controls and a break reminder. Posture itself
  should use the cue/meter rather than system notification banners.
- Quit from the menu-bar menu and reopen: baseline and settings persist.
- Enable login startup only if desired; log out/in to check it, then restore
  the original preference. Confirm the camera releases after quitting.

On an existing Unshrimp profile, separately confirm settings/calibration/history
carry over. New-user and upgrade results are separate.

## Result to record

Mac model/chip:
macOS version:
Artifact SHA-256:
Transfer method and download warning:
Intel / Rosetta / native arm64 (this ZIP is Intel):
Welcome / Later / relaunch:
Camera permission / preview / calibration / tracking:
Cue recovery / sound / break reminder:
Saved state after Quit/reopen:
Login startup (or not tested):
Problems, exact messages and steps:

For logs, inspect ~/Library/Application Support/Shrimply/shrimply.log before
sharing. No camera recording is required.

Expected ZIP SHA-256:
12da97ccdf0f9773872ee9b72397284f85db7808b923e429b14b1ba5520d30c2
