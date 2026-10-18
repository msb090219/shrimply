# Restrained utility icon pass

- [Main page with Settings cog](main.png)
- [Dark-palette detail](cog-dark.png)
- [Light-palette detail](cog-light.png)

The main header Settings text button is replaced with a 32 × 32 logical target
and an 18-pixel cog. The original line drawing is rendered at multiple sizes
without another dependency. Its color follows the desktop text palette and
refreshes when the palette changes. Hover uses a neutral surface; keyboard
focus retains the coral border. Tooltip, accessible name, Alt+S and the existing
modeless Settings action remain.

This deliberately changes one utility control. Specific actions such as
Calibrate, Camera settings and Take a break retain their explanatory labels.
Captures use synthetic app state. 316 tests pass, including icon presence,
accessible naming, focus policy, shortcut and action routing. Full assistive
technology and physical mixed-DPI checks remain pending.
