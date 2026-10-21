# Resumed Mac performance work — 19 October 2026

Intel Mac, macOS 15.7.9, Python 3.12.15. Source branch: `macos-development`.
These measurements use production Cocoa widgets and the source vision worker.
They measure process CPU time relative to one logical CPU, not battery drain.

## Changes completed and checked

- A settled static/reduced-motion shrimp stops its animation timer. New scores
  restart it, and recovery still fades the shrimp out.
- On Mac, the raster shrimp requests a repaint only when its opacity or integer
  pixel position changes. The animation clock continues at its existing rate.
- Preview mirroring uses one owning image transformation instead of copying
  first and then mirroring. Regression coverage checks mirroring and pixel
  ownership after the input buffer changes.
- Preview-only pacing includes capture time in the frame budget rather than
  adding a full frame interval after each capture.
- No camera frame-rate request, inference-rate, resolution, calibration, or
  scoring change was retained in this optimisation pass. The camera source is
  byte-identical to the pre-optimisation snapshot.

## Isolated animation result

Twelve-second samples after two seconds of warmup, with no camera worker.
Both bobbing windows were exposed and painting.

| Bobbing shrimp | Baseline | Current |
| --- | ---: | ---: |
| CPU, one logical CPU | 15.55% | 3.26% |
| Animation ticks | 375 | 375 |
| Paint events | 375 | 56 |

This is about 79% less CPU in the isolated bobbing-overlay sample. It is not a
79% reduction for the whole app. Reports:
[baseline](animation-baseline.json), [current](animation-current.json).

The current static sample requested no repaints and had no timer ticks, versus
376 repaint requests in the baseline. Its window reported unexposed at the end,
so its 0.14% CPU is not used as an exposed-window performance comparison.

## Camera findings and limits

The [baseline matrix](baseline-matrix.json) completed without camera errors.
The [current matrix](interrupted-current-matrix.json) had a camera interruption
during tracking-preview warmup. It recovered and delivered 16 inference frames
and 95 previews during the eight-second measurement, but the complete run is
correctly marked `ok: false` and excluded as a successful before/after comparison.
The earlier agent also recorded this failure using the baseline worker.

This does not establish the cause of camera failure or close the camera
reliability work. There is no supporting evidence for changing the requested
camera rate as a fix. Live poses and accepted-landmark counts differed across
runs; camera CPU figures cannot establish a detection-accuracy result.

A separate [preview check](preview-current.json) completed both modes without
camera errors: 38 inference frames and 239 previews over 20 seconds in tracking
preview; 287 previews (14.35 fps) over 20 seconds in preview-only mode. The
maximum observed preview gaps were 0.140 and 0.102 seconds respectively. This
checks functional delivery, not a longer-session reliability guarantee or frame
freshness measurement. Preview-only CPU was 19.97%; improved pacing delivers
more frames than the baseline's roughly 10 fps, so it is not claimed as a CPU
reduction. Tracking/inference rates remain unchanged.

The profiler now records output rates, maximum delivery gaps, camera errors,
paint requests, paint events and exposure. A recovered error or a measurement
with no expected camera output fails the run. Error counts include warmup.
Gap fields for streams that are disabled simply span the measurement interval.

## Development environment

The copied environment was preserved at
`/private/tmp/unshrimp-moved-env-qpro2qfc/.venv`. A fresh `.venv` was created from
the local uv cache and installed against this Downloads checkout. Activation,
test launchers and editable imports now point here rather than Documents.

The full regression suite in the recreated environment passed **485 tests,
1 skipped**, with two dependency deprecation warnings. macOS native subprocess
checks require running outside the agent sandbox. The import-time sandbox stall
was traced to Matplotlib's system-font subprocess, imported through MediaPipe.

After extending the settled-animation test to cover fading out again, the
focused mascot/worker checks passed **22 tests**. `git diff --check` also passes.

## Local packaged build

The updated development app is at `dist/performance/Unshrimp.app`, built with
`.venv/bin/python -m PyInstaller unshrimp.spec --noconfirm --clean --distpath
dist/performance --workpath build/performance`.

`codesign --verify --deep --strict dist/performance/Unshrimp.app` exits zero.
The [packaged smoke check](packaged-smoke.json) also exits zero and reports
`ok: true`, `frozen: true`, bundle version 1.2.0, loaded artwork and successful
model inference. This is an ad hoc signed local Intel build, not a notarized
release. The smoke test uses a synthetic frame and does not open the camera.
The existing app in `~/Applications` was not replaced. Live camera measurements
above used the source worker; this new bundle still needs a normal-use check.

Production source fingerprints are recorded in [source-hashes.json](source-hashes.json).
The original baseline snapshots remain in
`/private/tmp/unshrimp-power-baseline-20261019`; they predate the optimisations
and include the preceding Mac overlay fixes.

## Reproduce

Quit ordinary Unshrimp first so only one process owns the camera. No frames are
saved, and the profiler does not write preferences or posture history.

```sh
.venv/bin/python tools/profile_macos.py --seconds 12 \
  --modes bobbing_shrimp static_shrimp --output diagnostics/animation-new.json
.venv/bin/python tools/profile_macos.py --seconds 20 \
  --modes tracking_preview preview_only --output diagnostics/preview-new.json
```

For a baseline comparison, add
`--baseline-dir /private/tmp/unshrimp-power-baseline-20261019` and choose a fresh
output path. Run comparisons sequentially without tests/builds in parallel.
The temporary baseline snapshots and environment backup are local recovery
artifacts, not durable dependencies.

Longer battery runs, physical idle shutdown, varied posture responsiveness,
and investigation of intermittent capture failures remain open.
