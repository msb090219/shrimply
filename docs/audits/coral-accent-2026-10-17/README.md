# Subtle coral accent

Shared desktop theme now uses existing shrimp coral (#EC8F6B) for selected tab
underlines, slider fills/handles, checked boxes, selection palette, and default
button/focus borders. Neutral surfaces still follow the system palette. Posture
status colours are unchanged. Disabled controls retain neutral treatments.

Checkboxes use a small bundled SVG checkmark so selection is not communicated
only through colour. The icon was decoded successfully and visually verified in
the actual Qt render. No dependency added; the existing packaging rule includes
the assets folder. Packaged icon loading still needs checking after rebuilding.

250 existing tests pass. Settings renders use synthetic/default data and stub
history; no camera or saved preferences were accessed. Reviewed the final
[Appearance preview](settings-appearance.png); Tracking and Reminders were also
rendered. Screenshots reflect the current Windows dark system palette. Light
mode, macOS, high-contrast mode, and display scaling have not been checked.
