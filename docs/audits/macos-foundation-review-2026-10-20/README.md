# Shared foundation and code-quality review — 20 October 2026

**Assessment:** a sound, reasonably clean foundation for this desktop app. Keep
the shared architecture. The reviewed code does not need a rewrite or a separate
Mac engine. This pass found and corrected additional interruption/panel issues;
code review and passing tests still do not establish distribution readiness.

## Windows comparison

Reference: the locally available Windows `origin/main` revision
`cdfebc08e41f7dba4b9641109779c73107b03dc0`, including its v1.3.0 work and P01–P03
release records. This is a source reference, not a claim that every Windows
release acceptance task is complete. No branch switch, Windows build, remote
change or release publication was performed.

[The comparison manifest](windows-comparison.json) records hashes for the 42
application files in the reference tree: 18 remain byte-for-byte identical.
All **307 named Windows test functions** remain present. That name check is
evidence of retained tests, not a claim that every assertion is unchanged or
that running them on Mac proves native Windows behavior.

The only additional Mac-specific application modules are `ui/macos_power.py`
and `ui/macos_windows.py`. Other native choices use small platform branches in
the existing shared modules.

| Layer | Foundation retained | Mac/current differences |
| --- | --- | --- |
| Core posture logic | Same state machine, smoothing, adaptive rates and baseline model | Shared validation fixes from the earlier audit; shared interruption fixes below |
| Calibration | Same phases, signals, sample gates, verification and saved baseline version 4 | Setup continuity fix below; Mac preview/disclosure presentation |
| History and storage | Same accumulator, SQLite schema, local-day accounting and rollups | Same implementations as Windows; platform-specific data-folder location |
| Vision | Same landmark extraction, confidence/geometry checks and scoring signals | AVFoundation permissions/capture resizing, startup validation and worker lifecycle improvements |
| UI/controller | Same controller, Dashboard, Settings, HUD, cue and break classes | Native menus, Mac fonts/shortcuts/Spaces, quieter notification policy and subsequent layout fixes |
| OS integration | One camera/pause/calibration policy | Cocoa power/session observers, Core Graphics idle query and per-user LaunchAgent instead of Windows APIs/registry |
| Delivery | Same app version and build specification | Separate `.app`, ICNS/usage metadata and architecture-specific dependencies/artifacts |

Mac-specific behavior is not a second copy of scoring, calibration or storage.
Shared fixes in this Mac working tree still need Windows verification before a
future Windows merge/build. Existing Windows release artifacts are unchanged.

## Confirmed findings corrected in this pass

1. **P2 — Capture interruptions counted toward sustained posture alerts.**
   A bad score at time 10, an interruption, then another at time 300 could emit
   an alert immediately because the old bad-posture clock survived. Reproduced
   separately through sleep/wake, manual retry and idle shutdown/return. The
   state machine now exposes a small observation-reset operation, called when
   capture restarts or suspends. It preserves the current state/manual pause
   while discarding stale alert/recovery/presence timing. Regressions prove a new
   full grace interval is required. This is shared logic, not a Mac-only fork.
2. **P2 — Calibration setup accepted a delivery gap as continuous checks.**
   Five seconds of setup, then a long stall and one good frame could advance to
   the next pose. Setup now restarts its continuous-check streak across delivery
   gaps over two seconds, matching the existing capture phases' gap bound.
   Normal phase lengths, scoring and baseline format are unchanged.
3. **P2 — Break cards lacked the existing full-screen panel configuration.**
   Native Cocoa inspection reproduced the missing Space flags. Top-level break
   cards now reuse `join_fullscreen_spaces`, like the shrimp/meter, and remain
   interactive. The embedded Settings example is guarded so it never changes
   the main window's native Space behavior. Native show/reshow tests include the
   reminder and verify that it is not click-through. This proves the panel
   configuration; a physical walkthrough over other apps remains separate.
4. **P3 — Loaded defaults shared the break-suggestion list.**
   Independent calls to `config.load()` shared the same nested list and its
   dictionaries with `DEFAULTS`. Replaced the partial copy with standard-library
   `copy.deepcopy`; regression confirms mutations do not affect a second load or
   defaults. No new config key or persistence format was introduced.

Also removed one unused worker import after checking repository callers and
corrected diagnostic documentation that still named the old OSA log path.

## Code quality and structure

The useful boundaries are already present: pure timing/scoring/calibration
logic, a worker owning capture/models, a storage module, a controller wiring
state and Qt signals, reusable UI widgets, and small native adapters. Settings
and calibration save-before-apply behavior, atomic settings replacement, bounded
history intervals and serialized worker replacement are worth preserving.

`ui/app.py` and `ui/settings.py` are each roughly 1,100 lines. They are the main
maintenance concentration, and follow the Windows structure. Their size alone
does not justify moving state across new services immediately before beta.
Consider extracting a cohesive responsibility after beta if changes repeatedly
require touching unrelated sections. No speculative framework, new dependency
or alternate platform hierarchy was added in this review.

Review covered application modules plus their Windows deltas and regression
paths: startup/config, baseline/calibration/state clocks, history/storage,
vision/capture/thread teardown, settings commits, Dashboard/calendar, themes,
overlays/captions, break cards/countdowns, menus, OS adapters and packaging.
This is a manual review with targeted fault reproduction, not exhaustive formal
verification. Native capture reads can still block inside a driver; retaining
thread ownership prevents unsafe destruction but does not guarantee bounded
hardware shutdown. Existing longer-use/device-loss acceptance remains open.

## Verification and candidate

- [Tests](tests.txt): **566 passed, 2 skipped**, two existing protobuf warnings.
  Includes the new lifecycle/defaults regressions, embedded-preview guard and
  actual Cocoa show/reshow/preferences/power checks. Windows-only native checks
  remain skipped on this Mac.
- [Source checks](source-checks.json): 92 first-party Python files compile; no
  duplicate module/class definitions found. This is a targeted AST check, not a
  complete linter or coverage result. `git diff --check` passes.
- [Package verification](package.json): fresh Intel build, all 44 bundled project
  modules including the entry point match source, strict local signature and
  version/permission metadata verified.
- [Archive report](archive.json) and [frozen smoke](extracted-smoke.json): local
  candidate extracted into a path containing spaces; Qt/icon/models/native
  inference checked without development tools on `PATH`. Local ad hoc signing
  is not Developer ID signing/notarization or clean-download verification.

Candidate: `dist/macos-foundation-review/Unshrimp.app`, with its local beta
candidate ZIP. The installed app remains the previous UI-polished version.
No live camera session was started or user data changed by this pass.

The earlier [release review](../macos-release-review-2026-10-20/README.md) remains
the record for migration/invalid-data/storage-startup fixes. The remaining
[Mac acceptance procedure](../../MACOS-TESTING.md) still applies: clean download,
Apple Silicon, signing/notarization, login, real idle/lid/display/camera behavior,
longer resource use, accessibility and distribution review. These remaining
checks, rather than a structural rewrite, are the next release steps.
