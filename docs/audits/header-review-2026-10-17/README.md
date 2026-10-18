# Shared window shell and app icon — 17 October 2026

The Windows title bar now uses normal OS drawing in all windows, with the shared
Unshrimp icon. Removed the extra in-window brand strips from Settings, Calibration,
About, Welcome, and the suggestion editor. This makes their headers consistent
with the main window and removes repeated titles.

Today and Progress remain tabs. Settings remains a separate window because it
contains infrequent configuration tasks, not daily tracking content. Its Tracking,
Reminders, Appearance, and General tabs keep the established layout. The autosave
note now shares the footer row with Done, so the navigation starts level with the
main window's tab row.

The app icon now uses the full-color photoreal shrimp asset. Its PNG is used by Qt
for window/task-switcher identity, and its multi-size ICO is embedded in Windows
Explorer's executable icon. The status-colored shrimp remains the tray icon.

Fresh camera-free Qt renders are `01-main.png` and `02-settings.png`. The packaged
smoke check and runtime UI weren't repeated for this latest change yet. The Windows
titlebar itself isn't shown in those widget captures.
