# Main window and tray startup

- Manual launch shows the main window and starts the existing tray lifecycle.
- Login entries include --background, hiding the main window when a baseline is
  available. First-run onboarding is shown once; dismissing it prevents repeated login popups.
- Manual duplicate launch connects to a per-user local Qt endpoint and restores
  the existing window, including when minimized. Windows foreground permission
  is handed to the existing lock owner. No second camera/controller is created.
- Background duplicate launches exit quietly without opening a window.
- Closing the main window hides it; tray Quit exits and releases camera resources.
- Manual pause/resume is saved. A saved pause prevents camera startup in either
  launch mode; opening the main window does not resume tracking.
- Already enabled login entries are refreshed to the current executable path and
  background flag. Disabled login startup stays disabled.

340 tests pass, covering mode routing, local socket activation, lock isolation,
login command generation/migration, pause persistence, initial camera policy,
minimized-window restoration, and existing lifecycle regressions.

Not verified: an actual Windows sign-out/login cycle or macOS login integration.
An older running build cannot accept activation messages; a manual second launch
falls back to the existing tray instruction until that older build is closed.

Packaged checks: executable built successfully and smoke test exited 0 (Qt image/icon loading, both models, native inference). Launched the updated build manually. Both a background duplicate and a manual duplicate exited 0; one responsive Unshrimp process remained, with its main-window title present. Startup log confirmed baseline loading and tray creation. Actual Windows login and foreground focus visual verification remain unchecked.
