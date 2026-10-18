# Light and Dark appearance, 18 October 2026

Added a saved **Dark / Light** choice under Appearance. The coral accent and the
green-to-red posture scale remain the same. Application palettes now drive the
main window, Settings, calibration and camera windows, menus, break prompt, and
meter controls. The Windows title bar follows the selected mode. The caption below
the floating meter gets a compact translucent pill: dark with light text in Dark
mode, light with dark text in Light mode. Its width follows the text rather than
filling the meter. Existing configurations default to Dark; the new choice is saved
with other preferences and updates windows immediately.

Settings keeps its existing boxed, single-column layout. The theme picker is one
small row under Appearance; no extra customization page or theme system was added.

Static Python compilation succeeded and the frozen Windows build is staged and
installed in `dist/unshrimp`; `dist/unshrimp-win64.zip` was refreshed. Automated
tests and native light-mode desktop inspection have not been run for this change;
Windows caption coloring can vary by Windows version.

Follow-up: Appearance now also offers **Use device setting**. Qt's system color
scheme drives the effective palette and updates it when the device setting
changes. Inputs, tabs, scrollbars, the Progress no-data marker, Settings preview
icons, the meter preview, and calibration countdown now refresh with the theme.
The meter caption gained modest horizontal and vertical padding. Static Python
compilation passed; automated and native visual checks remain open.
