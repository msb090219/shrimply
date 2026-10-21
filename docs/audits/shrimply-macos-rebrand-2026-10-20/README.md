# Shrimply Mac rebrand and beta staging — 20–21 October 2026

This records local preparation only. No tag, release, release upload or remote
source push was performed. The user selected an unsigned beta candidate and
confirmed the installed app was closed for replacement.

## Integration and preservation

Windows reference: Shrimply rename `e16ef8a`, through `1f0253f0180cb53d6a55f4f504287272c494946e`.
The Mac branch remains `macos-development`, with local implementation changes.
Origin now points to `https://github.com/msb090219/shrimply.git`.
The active checkout folder remains `unshrimp` to preserve workspace/tool paths.

The Python package, imports, app class, icons, bundle ID, specification, build
commands, site and current documentation use Shrimply. Historical audits and
backup names retain Unshrimp. Data migration copies only missing Shrimply files,
first from Unshrimp and then OSA; old data is retained. Both instance locks are
held during the new session. Enabled old Mac startup entries migrate to the new
bundle; disabling startup removes both labels.

[Integration manifest](integration.json) records the source snapshot, preservation
of 14 critical Mac functions after namespace normalization and retention of all
310 named current Windows test functions. The source snapshot is under
`dist/install-backups/source-before-shrimply-20261020-213530.tar.gz`.
The camera aspect-ratio/startup fixes, quiet posture notifications, native
sleep/menu/Spaces handling, Settings alignment and foundation audit fixes remain.
Existing Windows release artifacts have not been replaced. Shared changes still
need Windows native acceptance before a future Windows build.

## Dependency compatibility

The installed PySide6 6.12.0 wheel had Qt framework minima of 14.4 but multiple
binding/shiboken binaries declaring macOS 26.0. A release gate caught this before
installation. Mac dependencies now select PySide6 6.10.2, while Windows/Linux
retain 6.12.0. No Mach-O metadata is patched. The package declares
macOS 15.0; the build script scans actual bundled native deployment targets.
The official [6.10.2 wheel listing](https://pypi.org/project/PySide6/6.10.2/)
identifies its macOS 13+ universal2 wheel; bundled-binary verification provides
our separate package-level check. Despite that wheel tag, some bindings declare
macOS 15.0, so this beta requires macOS 15.0 rather than claiming macOS 13 support.

## Verification scope

The automated suite includes old/new instance exclusion, migration precedence,
Mac startup replacement/disable/failed-write preservation and existing release
regressions. Native Cocoa tests use disposable profiles: an upgrade retains
baseline and real SQLite history; fresh-profile Later leaves the camera off.
These are source-host checks, separate from real packaged first use.

With the final Mac dependency pin, the suite passed **573 tests, with 2
Windows-only skips**. Dependency checking passed for 46 installed packages.
The native test now destroys its previous window before creating another
controller, so queued UI work cannot outlive the temporary database. Refreshed
Cocoa captures confirm the renamed About screen and aligned suggestion actions.

The repeatable `tools/build_macos.py` checks native architecture, identity,
version, icon, camera usage text, native deployment targets, all bundled project
modules against source and strict ad hoc signatures. It extracts the ZIP into a
path containing spaces and runs frozen Qt/model/inference smoke verification.
It has no publication step. The workflow uses macOS 15 for both
architectures, matching the declared minimum; runner labels were checked against
[GitHub’s runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
The workflow has not been dispatched. Evidence and final installation results are recorded
below when those checks complete.

Native captures are in [screenshots](screenshots/). Logs: [tests](tests.txt),
[dependencies](dependencies.txt), [native upgrade](native-upgrade.txt).

## Remaining distribution acceptance

See [release notes](../../releases/macos-v1.3.0-beta.md) and
[Mac testing](../../MACOS-TESTING.md). Renamed packaged camera-permission and
upgrade acceptance, real logout/login, clean downloaded/quarantined execution,
longer hardware/lifecycle use and Apple Silicon remain separate checks.
Developer ID signing/notarization is deferred by user choice. No Apple Silicon
package or compatibility guarantee is inferred from an Intel build.

## Completed Intel package checks

Shrimply 1.3.0, x86_64, minimum macOS 15.0; actual maximum bundled deployment
target is also 15.0. All 44 bundled project modules match current source. Strict
signature checks and extracted frozen Qt/icon/model/inference checks passed.
See [verification](verification.json), [smoke](smoke.json), [build log](build.txt)
and [SHA-256](shrimply-macos-x86_64.sha256).

Local ZIP: `dist/macos-release/shrimply-macos-x86_64.zip`.
SHA-256: `12da97ccdf0f9773872ee9b72397284f85db7808b923e429b14b1ba5520d30c2`.
The smoke report's authorization observation is from command-line execution;
it does not complete Finder-launched renamed-app camera-permission acceptance.

## Installation

The verified app is installed at `~/Applications/Shrimply.app` and left closed.
Previous app backup: `dist/install-backups/installed-before-Shrimply-20261021-164454/Unshrimp.app`.
Installed executable and metadata match the verified candidate; strict signature
verification passed. Startup was disabled and remains disabled. The installer
did not read or change user settings/history; normal first launch performs the
app's tested migration. See [installation report](installation.json).
