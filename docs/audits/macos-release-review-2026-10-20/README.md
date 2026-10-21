# Mac first-beta code and local package review — 20 October 2026

Used the recorded Windows release approach in [TESTING.md](../../TESTING.md),
TODO P01–P03 and M10, and the historical Windows tracking/lifecycle reports.
Those records establish the procedure; they do not establish that every Windows
release acceptance step was completed. This pass reviews the Mac source and
local Intel package. It does not declare the app ready for public distribution.

## Confirmed findings, fixed

| Priority | Trigger and previous result | Correction and regression |
| --- | --- | --- |
| P1 | Current `config.json` absent, current `log.db` present, old OSA data present: migration copied the older history over the current database. Reproduced with disposable files. | Migration copies only missing destination files. Tests cover both preserving current history and migrating when no current history exists. |
| P2 | Saved baseline contains a finite but unrepresentable date, such as `1e300`: loading accepted it, then Settings raised `OverflowError` when formatting its saved date. | Reject dates that cannot be formatted on the host during baseline validation. The existing controller recovery path treats the invalid baseline as needing calibration. |
| P2 | Valid JSON contains oversized integers in numeric settings or baseline fields: conversion inside `math.isfinite` raised `OverflowError` during startup. Reproduced with `10**400`. | Check bounded settings before conversion; reject unrepresentable baseline numbers as invalid data. Tests cover positive/negative settings and baseline date/value/tolerance. |
| P2 | Corrupt, inaccessible or unwritable history database: controller construction raised an uncaught storage exception, leaving no useful startup message. | Show an error naming the data folder and underlying problem, stop startup before capture and release the instance lock. This does not repair/delete a damaged database. Fault tests cover storage failures; a real damaged-file startup check confirms the original bytes are preserved. |

The fixes are shared source changes in this working tree, not a published commit.
Windows artifacts were not changed; run native Windows regressions before its
next release. No new runtime dependencies were added.

## Scope reviewed

- Entry point and single-instance ordering, activation, background launch and
  error paths; config loading, atomic saves and legacy migration.
- Baseline validation/calibration save ordering, Settings commit/failure paths,
  controller shutdown, pending history, SQLite and elapsed-time accumulation.
- Camera permissions, first-frame validation, retries, worker replacement,
  stale-signal guards, preview-only/pause policy, suspend/resume and cleanup.
- Native Mac login plist, application menus, idle API, overlapping power/session
  observers and full-screen overlay integration; new shared features and local
  packaging/release-workflow separation. The review found no further confirmed
  blocker in these sampled paths; it is not proof of an absence of bugs.

The new [Mac procedure](../../MACOS-TESTING.md) preserves the Windows distinction
between repeatable checks and physical/clean-machine acceptance.

## Verification

- [Full regression suite](tests.txt): **560 passed, 2 skipped**, two existing
  protobuf deprecation warnings. The skips are Windows native-only checks.
  Includes actual Cocoa window/preferences/history and overlapping power
  notification checks in isolated subprocesses. Notification injection does not
  establish physical sleep/lid handling.
- [Damaged history startup](damaged-history.json): real source controller startup
  against a disposable invalid SQLite file; only the error dialog was intercepted.
  Exit 1, helpful message, original bytes preserved, instance lock released and
  no worker started. The installed app and user's profile were not involved.
- [Dependency check](dependencies.txt): 48 installed packages compatible.
  [Environment and model hashes](environment.json): Intel macOS 15.7.9, both
  task files match the hashes pinned in `fetch_models.py`.
- [Package verification](package.json): all **44** bundled project modules,
  including `main`, compare equal to current compiled source; version 1.3.0,
  camera usage description, bundled MediaPipe/OpenCV notices and strict local
  signature verification pass. Notice presence alone is not a licensing review.
- [Archive check](archive.json) and [extracted frozen smoke](extracted-smoke.json):
  local ZIP extracted into a path containing spaces, strict signature checked,
  Qt/icon/models/native inference exercised with development tools removed from
  `PATH`. The archive report records SHA-256 and scope. This is not a fresh Mac
  without Python installed, a browser-downloaded quarantined app or live capture.

Candidate: `dist/macos-release-review/Unshrimp.app` and its local
`unshrimp-macos-x86_64-beta-candidate.zip`. The installed app remains the earlier
UI-polished build; this review does not replace it or launch a tracking session.
No Windows artifact was rebuilt, and no tag, upload or release was created.

## Remaining before distribution

Clean/quarantined downloaded-app startup and permissions; Apple Silicon build
and execution; Developer ID/notarization; real logout/login; full five-minute
idle behavior; longer packaged camera/resource use; physical camera loss,
lid/sleep/display matrix; accessibility and final feature walkthrough; dependency
distribution review. See the numbered Mac procedure and existing M01–M11 tasks.
Earlier user confirmations and camera evidence remain useful historical results,
but were not rerun as hardware acceptance in this pass.
