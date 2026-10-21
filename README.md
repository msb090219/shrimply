<p align="center"><img src="assets/brand/banner.png" alt="Shrimply — Don't get shrimped." width="640"></p>

# Shrimply

**A gentle posture and break reminder for Windows and macOS.** Shrimply learns your usual sitting position with your webcam, then nudges you when you drift and when it is time to move. Camera processing stays on your device.

## Get Shrimply

Previously called Unshrimp. Existing settings, calibration and history carry
forward automatically; quit the old app before opening Shrimply for the first time.
Older published releases still use the `unshrimp-win64.zip` and `unshrimp.exe` names.

| Platform | Download |
| --- | --- |
| Windows · 64-bit | [shrimply-win64.zip](https://github.com/msb090219/shrimply/releases/download/v1.3.0/shrimply-win64.zip) |
| macOS 15+ · Intel Macs | [shrimply-macos-x86_64.zip](https://github.com/msb090219/shrimply/releases/download/v1.3.0/shrimply-macos-x86_64.zip) |

Extract the ZIP and run `shrimply/shrimply.exe` on Windows. On Mac, move
`Shrimply.app` to Applications and open it. The app and posture models are
included; Python is not required. Allow camera access when you calibrate.

These beta downloads are unsigned. Windows may show SmartScreen. On Mac,
follow [Apple's opening instructions](https://support.apple.com/en-nz/102445)
if blocked. See the [joint release notes](https://github.com/msb090219/shrimply/releases/tag/v1.3.0)
for upgrade information.

Shrimply opens its Dashboard on a normal launch. Closing the window keeps tracking in the system tray; choose **Quit** from the shrimp tray icon to exit.

<p align="center"><img src="docs/shots/landing/dashboard.webp" alt="Current Windows Dashboard with sidebar, today's monitored time, weekly posture mix, and activity heatmap. Example history data." width="720"></p>

<p align="center"><em>Dashboard shown with example history.</em></p>

## Set up your posture

Choose **Calibrate** from the Dashboard or tray menu. The guide checks camera framing, then asks you to sit tall, sit normally, and hunch briefly. Your normal pose anchors scoring; the hunch shows how far you can drift. Recalibrate after moving your chair or camera.

<p align="center"><img src="docs/shots/landing/calibration.webp" alt="Shrimply calibration asking the user to sit normally, with the shrimp countdown and an illustrative camera preview." width="440"></p>

## See when you drift

The floating meter fills from green to red as posture drifts. If poor posture continues, you can show a shrimp or a discreet text cue. Pause or resume from the meter or tray; Camera preview works even while tracking is paused.

Posture feedback uses the shrimp, meter, and optional chime. System notifications
are reserved for camera problems; calibration guidance and results stay in the app.

<p align="center"><img src="docs/shots/landing/meter.webp" alt="Floating shrimp posture meter with colored segments, pause control, and more menu." width="464"></p>

## Make room for a break

After a configurable amount of detected sitting, Shrimply suggests a stretch or short walk. Start a timed break, choose **Later**, or skip the reminder. Time away, pauses, and calibration do not count toward sitting time.

<p align="center"><img src="docs/shots/landing/break-reminder.webp" alt="Break reminder suggesting chin tucks with Start and Later buttons." width="500"></p>

## See progress and make it yours

The Dashboard shows today's monitored time, a weekly posture mix, and an activity calendar covering up to 26 weeks. Open **Settings** from the sidebar to change camera, alerts, breaks, theme, and floating feedback. Changes save automatically.

<p align="center"><img src="docs/shots/landing/settings.webp" alt="Current Windows Settings page embedded in the main window, showing theme and floating cue controls." width="720"></p>

## Privacy

Shrimply runs pose detection locally, does not save camera frames, and has no account or cloud sync. Posture history is stored on your computer in `%APPDATA%\Shrimply` on Windows or `~/Library/Application Support/Shrimply` on macOS. The bundled MediaPipe Tasks SDK sends API performance and usage metrics to Google; [Google says camera input stays on your device](https://github.com/google-ai-edge/mediapipe#privacy-notice). Shrimply is a habit aid, not a medical device.

## Run from source

Requires Python 3.10+. Windows is the primary supported platform.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python fetch_models.py
.venv\Scripts\python main.py
.venv\Scripts\python -m pytest -q
```

For macOS development, use Python 3.12 and run:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -e .
.venv/bin/python fetch_models.py
.venv/bin/python main.py
```

Intel Macs automatically use compatible MediaPipe, OpenCV, and NumPy versions.
Allow camera access for your terminal application if macOS prompts for it.

On macOS, camera capture stops for system/display sleep, screen lock, or an
inactive user session. Tracking resumes after those conditions clear and respects
manual pause. Normal tracking also stops after five minutes without keyboard or
mouse input and resumes when activity returns. Native application menus provide
Command-comma for Settings, Command-Q to quit, and Command-W to close the dashboard
while leaving tracking in the menu bar.

Settings lives inside the main window, with four left-aligned categories. Use Tab
to reach its controls, or Command-1 through Command-4 to switch pages. Rescan lists native
camera names without opening a capture session or interrupting tracking.

General → Start Shrimply at login enables quiet startup at the next Mac login.
This writes a per-user LaunchAgent in `~/Library/LaunchAgents`; disabling the
setting removes it. Keep the app (or this development checkout and its virtual
environment) in the same location while startup is enabled.

The menu-bar shrimp uses macOS's native menu. Progress refresh uses Command-R,
and custom text uses the system font on Mac.

To build a local Mac application, run
`.venv/bin/python -m PyInstaller shrimply.spec --noconfirm --clean`.
The output is `dist/Shrimply.app`. This development build is not Developer ID
signed or notarized; Mac release publishing remains disabled pending packaged
app checks and distribution setup.

To stage a verified unsigned beta ZIP and checksum locally, run
`.venv/bin/python tools/build_macos.py` after the tests pass. Artifacts are written
under `dist/macos-release/`, separately for Intel (`x86_64`) or Apple Silicon
(`arm64`), according to the build machine. The script checks the bundle against
source and tests inference after ZIP extraction; it does not publish anything.

If the checkout is in iCloud-synced Documents, keep the virtual environment and
build output in a local folder outside iCloud. PyInstaller accepts `--distpath`
and `--workpath` for this. Offloaded environment files can stall builds, and
Finder metadata on the app bundle can fail strict code-signature verification.

For known issues and planned work, see the [work list](docs/TODO.md). If something goes wrong, attach `~/Library/Application Support/Shrimply/shrimply.log` on Mac or `%APPDATA%\Shrimply\shrimply.log` on Windows to a bug report. The landing page lives in [`docs/`](docs/), and artwork guidance is in the [brand asset guide](docs/ASSETS.md).

## License

[MIT](LICENSE)
