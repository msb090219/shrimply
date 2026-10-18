# Camera/status verification — 17 October 2026

## Passed with the built-in webcam

Historical results below describe the earlier policy. Explicit preview now works
while tracking remains paused; see the [updated verification](../shrimp-feedback-2026-10-17/README.md).

The test ran real DirectShow capture and bundled model inference in an isolated
Qt host. Test settings and its empty history database were temporary. No webcam
images, landmark data, or video were saved.

- Opening the framing mirror while paused left capture stopped and the mirror empty.
- Resume delivered real preview images and changed both Main and Settings to Running.
- Closing the mirror cleared its image and stopped preview delivery while tracking
  continued to deliver frames.
- Selecting unavailable camera 9999 cleared the image and exposed Retry in Main,
  Settings, and the mirror.
- Restoring camera 0 through the mirror's Retry action recovered real capture
  and the displayed image.
- Both pause/reopen cycles succeeded. Capture stopped in **881.5 ms** and
  **869.1 ms**, including resource cleanup on the worker thread.
- All six relevant Python modules extracted from the built executable matched
  the source modules under test. The packaged model/icon/native inference smoke
  check had also passed for this build.

[Machine-readable live result](../../../diagnostics/camera-ui-verification-2026-10-17-r2.json)

Reproduce after quitting the ordinary app:

```powershell
.\.venv\Scripts\python.exe tools\verify_camera_ui.py --camera 0
```

## Passed with Qt scaling simulation

Seven running/error/paused layouts were measured at each of 100%, 150%, and
200% scaling: **21 layouts**, with actual pixel ratios of 1.0, 1.5, and 2.0.
There were no buttons below their minimum size hint, wrapped labels below their
required height, or hidden horizontal overflow. Representative error and paused
captures were visually inspected. Longer pages scroll vertically at small sizes.

- [100% measurements](../../../diagnostics/camera-status-scale-100/layout-report.json)
- [150% measurements](../../../diagnostics/camera-status-scale-150/layout-report.json)
- [200% measurements](../../../diagnostics/camera-status-scale-200/layout-report.json)

## User-observed packaged Windows checks

- Starting tracking with Windows camera access disabled showed the camera
  unavailable error. Restoring access recovered capture automatically.
- The user reported that buttons and text were reachable and readable. Text at
  100% was smaller in other applications too; no Unshrimp-specific clipping was
  reported. This does not certify every scale or transitions between monitors.
- The user did not specifically observe the Retry button. Automatic recovery
  meant that using it was unnecessary in this check.

## Still unverified

Explicit packaged preview pause/resume confirmation and native Retry visibility
remain unrecorded. The source-host test and package bytecode match do not
replace testing every interactive frozen application's Windows integration path.

Physical cable disconnection is not applicable to this built-in camera. The
unavailable-index check tests open failure and recovery, not a driver dropping
frames midstream. The user-observed permission check above covers access being
disabled before starting capture, not permission loss midstream. Native Windows
DPI changes, mixed-DPI monitors, title-bar placement, and screen-reader behavior
remain outside this pass. Posture accuracy and complete calibration were not
tested.
