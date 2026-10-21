# Windows 1.3.0 feature integration on Mac — 20 October 2026

The shared Windows implementation from `2b22b16`, narrow Settings fix `7cc276b`,
and Mac scrollbar test fix `7cdf805` are integrated through upstream revision
`cdfebc08e41f7dba4b9641109779c73107b03dc0`. These are working-tree changes on
`macos-development`; no merge/tag/release has been published.

A pre-integration snapshot is retained at
`/private/tmp/unshrimp-integration-20261020/mac-before-integration.tar.gz` with a
binary patch and source-integration manifest alongside it. Existing Mac camera,
native menu/startup/power, animation performance and notification changes remain.
The snapshot is also retained in
`dist/install-backups/mac-source-before-1.3.0-20261020.tar.gz`.

## Implementation and evidence

| Handoff | Integrated behaviour | Verification |
| --- | --- | --- |
| M01 / U12 | Sustained bad-posture entrance and sustained recovery, editable hold times | Shared timing/interruption tests; native cue-window checks |
| M02 / U13 | Activity calendar up to 26 weeks, summaries, square cells and date navigation | Dashboard tests; native screenshots. Narrow widths show fewer weeks to preserve cell size |
| M03 / U14 | Rise, fade-only and instant entrances, independent bobbing/reduced motion | Mascot and Settings regressions; native preference persistence |
| M04 / U15 | Quote/progress Dashboard with contextual setup/camera-recovery actions | Dashboard state/route tests and native screenshots |
| M05 / U16 | Settings embedded in the main window, autosave and page return | Real Cocoa page navigation, Command-W and persisted preferences; shutdown guard test |
| M06 / U17 | Four horizontal categories, aligned previews and narrow-width editor fix | Settings layout tests and native 620/960-point captures in Light/Dark |
| M07 / U18 | Collapsible main sidebar, selected/hover/focus states | Sidebar routing tests and native collapse/expand check; Mac application menus retained |
| M08 / U19 | Horizontal/vertical meter, stacked controls and detached caption | HUD interaction/layout tests; native full-screen Space flags and click-through caption checks |
| M09 / U20 | Shared shrimp/text cue, sizing, positioning, preview and saved choice | Shared response/render tests; native text-window, preview and persistence checks |
| M10 / P02 | Validated saved settings/baselines, safer calibration saves, history/storage errors and tray retry | Shared config/calibration/history/controller/tray tests; native history persistence |
| M11 / P03 | MediaPipe SDK metrics disclosure in welcome/About, README and site | Source review and package contents; camera frames remain local |

The M tasks remain open for their remaining packaged, physical-desktop and
human acceptance steps. Implementing the shared code and passing automated
checks does not establish Apple Silicon, external-display or longer-use results.

## Mac integration fixes

- Use the new shared Settings categories inside the main sidebar; retain Mac
  Command-comma, Command-W/Quit and category shortcuts rather than nesting the
  older Mac Settings sidebar inside the new main sidebar.
- Combine the new HUD show handler with Mac Space configuration. Also configure
  the vertical meter's separate caption to accompany full-screen apps and stay
  click-through. Native checks exercise show/reshow for both meter orientations
  and both cue styles.
- Keep the Mac settled-animation/raster repaint optimisation alongside the new
  cue entrance and timing behaviour.
- Preserve the no-posture/recovery/calibration-system-notification policy.
  Optional posture sound, meter feedback and separate break cards remain;
  persistent camera errors can still notify. Failed calibration saves show their
  error in the calibration result window.
- Avoid a Dashboard/history refresh when embedded Settings finishes during
  shutdown, after history storage may already have closed. A regression test
  checks that quitting never performs that refresh.
- Keep the native-resolution camera fix with in-memory resizing and first-frame
  validation; Windows still configures its capture backend normally.
- Bundle the licensing files from the actual installed wheels. Intel Mac uses
  MediaPipe 0.10.21 (older `dist-info/LICENSE` layout, no wheel NOTICE) and
  OpenCV-contrib 4.11.0; other supported builds use their existing newer pins.
  Include the MediaPipe NOTICE whenever the selected wheel supplies it. This is
  package-content handling, not completion of the outstanding distribution review.

## Scope of checks

The Cocoa integration check uses temporary settings/history and a temporary
LaunchAgent path. It does not replace the user's login registration or data.
Captures here show an isolated paused profile and synthetic one-minute history,
not the user's posture or camera frames. They cover Settings, the Dashboard,
Light/Dark and narrow/wide sizes; they are widget captures without window chrome.

The camera checker compares 11 bundled modules with source and uses bundled
models in a source Cocoa host. It exercises real capture, inference/calibration
cancellation, preview, tray pause/resume, an intentionally unavailable index and
recovery. No camera frames are written. This is distinct from normal use of the
packaged executable. The separate packaged smoke check exercises actual frozen
Qt resource loading and inference, without opening capture.

Candidate: `dist/macos-features/Unshrimp.app` (Intel, version 1.3.0). Developer ID
signing/notarization and Apple Silicon verification remain outstanding.

Final full suite: **548 passed, 2 skipped**, recorded in [test-suite.txt](test-suite.txt).
The skipped checks require Windows native message delivery or Windows startup
controls. Dependency validation (`uv pip check`) passed for all 48 installed
packages. The rebuilt candidate passed strict ad hoc signature verification and
the [packaged smoke check](packaged-smoke.json), including version/bundle 1.3.0.

The [final live-camera report](live-camera.json) passed with zero unexpected
camera errors, no power interruptions and no unhandled Qt callback errors,
including cleanup after the embedded Settings shutdown fix. The intentionally
invalid camera index is an expected error/recovery check. Its [console log](live-camera.txt)
is retained alongside the numerical report.

Installed the verified candidate at `~/Applications/Unshrimp.app`, after archiving
the previous app. [installation.json](installation.json) records the backup,
strict signature verification and 12 embedded modules checked against source.
The app was not launched for normal use during installation. User settings and
history were not changed by the installer; no Windows artifact was rebuilt or
replaced, and nothing was published.

## Aspect-ratio correction after user testing

The user observed a squeezed camera preview. The preview widget already fits
images proportionally, but the Mac capture adapter introduced by the startup
workaround resized native 1280×720 frames directly to 640×480. Corrected that
adapter to fit within the requested bounds while preserving the native aspect
ratio, without cropping or upscaling smaller input. This camera now supplies
640×360 frames to both preview and inference/calibration. Camera session output
settings are still untouched, preserving the earlier stability fix.

Regression checks cover widescreen, portrait, 4:3 and smaller frames, failed
reads, reported dimensions and resource release. Camera/worker/preview/metrics
checks passed **152 tests**. A brief real capture confirmed 640×360 (16:9), with
no frames saved. Existing settings/history/baselines are retained; recalibrating
after the geometry correction is recommended.
The corrected package passed model smoke and strict signature verification and
replaced the closed installed app, with its previous copy archived. See
[aspect-installation.json](aspect-installation.json),
[aspect-packaged-smoke.json](aspect-packaged-smoke.json), and
[camera-aspect-live.json](camera-aspect-live.json). The app was left closed.
