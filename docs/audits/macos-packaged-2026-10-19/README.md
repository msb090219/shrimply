# Packaged Mac app checks — 19 October 2026

Host: Intel Mac, macOS 15.7.9. Development branch: `macos-development`.
These checks exercise an x86_64 PyInstaller app, not an Apple Silicon build or
a downloaded, quarantined release on a clean Mac.

## Confirmed

- The initial packaged smoke check loaded Qt image plugins, artwork, both models
  and native inference successfully: [initial-smoke.json](initial-smoke.json).
- After the user allowed camera access, the packaged app processed live camera
  frames and posture scores. A numeric snapshot contained 265 processed frames,
  all with usable landmarks; median inference was 28.15 ms. This is a short
  functional check, not a battery benchmark:
  [live-camera-summary.json](live-camera-summary.json).
- The user confirmed that the menu-bar shrimp opens one menu and calibration works.
- Full regression suite after the fixes: **477 passed, 1 skipped**, with three
  existing deprecation warnings. This includes menu-popup routing, calibration
  disclosure keyboard behavior, and denied/restricted/authorized camera cases.
- Native Cocoa reports the standard Refresh shortcut as **⌘R**.
- The rebuilt app reports bundle version **1.2.0** and includes the camera usage
  description and ICNS icon. The installed copy passes
  `codesign --verify --deep --strict` with an **ad hoc** signature.
- The installed copy also passes the model/inference smoke check:
  [installed-smoke.json](installed-smoke.json),
  [signature-check.txt](signature-check.txt). This fresh ad hoc build initially
  reports camera authorization as `not_determined`; it needs its own first-launch
  permission decision. The successful live-camera check above was on the prior
  build that the user had already allowed.
- After allowing the updated installed copy, the user confirmed camera access
  and the smaller disclosure arrow. Its diagnostics independently confirm live
  inference: [installed-live-camera-summary.json](installed-live-camera-summary.json).
  That snapshot includes 71 processed frames, 51 with usable landmarks; the
  remaining frames had no usable detection. This does not establish accuracy
  across lighting, poses or users.

## Fixes made during this check

- Set the Mac bundle's version from `unshrimp.__version__`; it previously showed 0.0.0.
- Check native camera authorization before capture. Denied access now explains
  where to enable it; restricted access points to Screen Time or the administrator.
  Existing OpenCV handling still requests access when authorization is undetermined.
  [Apple's capture authorization guidance](https://developer.apple.com/documentation/bundleresources/requesting-authorization-for-media-capture-on-macos).
- Add permission status and bundle version to the Mac smoke report without
  opening the camera.
- Replace oversized Mac calibration arrows with 16-point chevron icons using the
  existing icon renderer. Both Camera details and How it works retain checkable
  state and keyboard access. Windows keeps its existing arrows.

Native production-control captures, without a camera feed:

| Before | Dark, collapsed | Dark, expanded |
| --- | --- | --- |
| ![Original arrow](disclosure-before.png) | ![Small right chevron](disclosure-dark-collapsed.png) | ![Small down chevron](disclosure-dark-expanded.png) |

Light captures: [collapsed](disclosure-light-collapsed.png),
[expanded](disclosure-light-expanded.png). Control captures have transparent
backgrounds and should be viewed against the corresponding theme.

## Local build environment

The original `.venv` contained offloaded iCloud files, and filesystem operations
stalled. Qt platform plugins also had hidden flags. The original bundle under
Documents carried `com.apple.FinderInfo`; strict signature verification rejected
it. Apple documents this metadata failure in
[QA1940](https://developer.apple.com/library/archive/qa/qa1940/_index.html).

A separate local build environment now lives at
`~/Library/Caches/Unshrimp/macos-build-venv`. Build output and working files are
under `~/Library/Caches/Unshrimp/macos-build`. The usable installed app is
`~/Applications/Unshrimp.app`. The source checkout and original `.venv` were kept.
Tests use `PYTHONPYCACHEPREFIX=~/Library/Caches/Unshrimp/pycache` so rewritten
bytecode does not depend on offloaded caches in Documents.

## Still required before release

- Finish the Settings walkthrough; the user has confirmed the smaller arrow in normal use.
- Packaged real sleep/wake, lid close, external displays and login startup checks.
- Longer battery and resource measurements.
- Apple Silicon build and a clean-machine installation check.
- Developer ID signing, notarization and a dedicated Mac release artifact.

No camera images were saved in this report. Camera diagnostics contain numeric
measurements only; the saved summary omits personal posture scores and device IDs.
