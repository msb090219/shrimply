# Shrimply 1.3.0 joint beta publication

Published on 21 October 2026 at https://github.com/msb090219/shrimply/releases/tag/v1.3.0, marked prerelease. Both platform ZIPs and
SHA256SUMS.txt were attached and verified before publishing. Repository is public.
Prior releases and their assets were retained.

Windows source/tag: `1f0253f0180cb53d6a55f4f504287272c494946e` / `v1.3.0`.
[Windows release workflow](https://github.com/msb090219/shrimply/actions/runs/39542822883)
passed 507 tests and packaged Qt/icon/model/inference smoke. The downloaded ZIP
passed integrity and PE x64 checks; all 42 bundled project modules match Windows
source. See [verification](windows-verification.json) and [checksums](SHA256SUMS.txt).

Mac source: `acdad7928948a5b109a75368bbd19f3756a47bfd`. The published Intel ZIP is
the same verified local candidate: 573 tests, 2 Windows-only skips, 44 project
module/source matches, strict signatures and extracted frozen inference pass.
[Mac staging evidence](../shrimply-macos-rebrand-2026-10-20/README.md).
Source-host Mac CI also passed on Intel and arm64. An arm64 development build
passed automated packaging/smoke, but is not a released asset or physical-camera
acceptance. Public Mac compatibility remains macOS 15+ · Intel Macs.

The separate Windows job on the Mac source branch found a suggestions-list
height failure (`tests/test_settings.py:296`, last row 189 vs viewport 156).
This does not affect the Windows main source/package shipped here. The finding
is recorded in TODO before a future Mac-to-Windows merge; no unverified shared
Mac fixes were merged into Windows for this release.

Release notes and download documentation use a compact platform table and
include unsigned-app instructions. No claim is made that clean-machine,
physical Apple Silicon, longer-use or real login acceptance is complete.
