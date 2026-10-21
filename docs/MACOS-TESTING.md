# Mac beta verification

Use the same separation as [the Windows procedure](TESTING.md): source review,
automated fault checks, packaged delivery, and physical acceptance each have
their own results. A smoke pass does not complete the normal app walkthrough.

## Repeatable local checks

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
uv pip check
.venv/bin/python -m PyInstaller --noconfirm --clean shrimply.spec
codesign --verify --deep --strict dist/Shrimply.app
dist/Shrimply.app/Contents/MacOS/Shrimply --smoke-test diagnostics/mac-package-smoke.json
```

The smoke command must exit zero and report `ok: true`, `frozen: true` and the
expected version. Archive the `.app` with `ditto -c -k --sequesterRsrc --keepParent`,
extract it into a path containing spaces, then repeat signature and smoke checks
on the extracted app. A local ad hoc signature does not establish Developer ID
signing, notarization or Gatekeeper acceptance of a downloaded ZIP.

Tests that use native Cocoa or local activation sockets need a normal desktop
session. Sandbox restrictions on sockets are not an app activation failure.
Fault tests must use temporary config/history and temporary LaunchAgent paths.
Never damage the user's real files to simulate corruption or write failure.

## Packaged walkthrough still to record

1. On a clean Mac/account without the development environment, download the
   actual intended artifact, extract and launch it through Finder. Record OS,
   architecture, quarantine/Gatekeeper result and artifact SHA-256. Check the
   privacy disclosure, Later (camera remains off), relaunch and camera permission
   grant/denial. Keep Intel and Apple Silicon results separate.
2. Complete fresh calibration after the camera aspect-ratio correction. Check
   failure/cancel feedback, retained previous baseline, successful save, explicit
   Start tracking and persistence after relaunch. Repeat the normal/slouch/return
   and leave/return sequences in the Windows guide; record posture observations
   separately from whether detection/inference merely ran.
3. Check all four Settings categories, autosave, shrink/expand, Light/Dark/system,
   break suggestion editing, previews and data-folder opening. Try both meter
   orientations, shrimp/text cues, all entrance options and reduced motion.
4. Launch twice: the second launch should activate the first without another
   camera owner. Close the main window, reopen through the menu bar, then Quit
   during capture/retry. Confirm process exit and that another app can use the
   camera. Relaunch after clean quit.
5. Pause with preview closed: camera stops. Open and close preview while paused:
   framing works without counting posture history or sitting time. Repeat fast
   pause/resume and camera retry/selection. Test contention and physical device
   loss when suitable hardware is available.
6. Let five minutes pass without input, observe camera shutdown, then return.
   Verify manual pause still wins. Separately check sleep/wake, lock/unlock,
   physical lid close, and calibration/preview interruptions in active and
   paused states. Repeat transitions; observers injected by tests do not prove
   physical lid behavior.
7. Check cue/meter placement over multiple full-screen applications and external
   displays, including display removal, scaling and saved off-screen positions.
   Complete keyboard and VoiceOver traversal.
8. Observe a reminder become due, Later/Skip, a full break countdown and early
   end. Confirm pause, absence, calibration and camera loss do not count as
   sitting. Posture/recovery stay in the shrimp/meter; only camera problems may
   generate system notifications. Test notification/sound buttons separately.
9. Enable login startup, log out/in, confirm quiet startup and one instance,
   disable it and repeat login. A temporary plist round-trip test is insufficient.
10. Run longer tracking with preview, pause/resume and Away periods. Record CPU,
    memory and thread trends after warmup. Short inference tests do not establish
    battery consumption or working-day stability. Check data preservation when
    upgrading and document uninstall/data-retention behavior.

Before distribution, complete signing/notarization, bundled dependency/model
distribution review, architecture CI and the final downloaded-artifact checks.
Windows native verification remains necessary before releasing shared fixes
there. This checklist does not authorize tagging, uploading or publishing.

Latest source/local-package findings: [20 October review](audits/macos-release-review-2026-10-20/README.md).
