# Calibration hierarchy — 18 October 2026

The camera-details control was checkable without an explicit checked style,
allowing the platform's blue highlight to show through. It now uses a quiet arrow
disclosure with a transparent checked/pressed background, coral hover text, a
visible keyboard-focus border, and an accessible name.

The page now presents three clear areas: pose and supporting instruction together,
a subdued timing panel, then the camera mirror. A small step label replaces the
redundant overall stage bar. Camera checks remain optional beneath the mirror;
opening them scrolls them into view without moving the pinned instructions.
The shorter privacy line retains its full explanation in its tooltip and accessible
description. Completion help uses the same disclosure treatment.

The twelve calibration slots and ten-segment HUD remain intact. No calibration
timing, scoring, camera policy, saved baseline, or saved preferences were changed.

## Verification

- Full automated suite: **409 passed**; one existing QImage.mirrored deprecation warning.
- Eighteen real-widget layouts at each of 100%, 150%, and 200% Qt scaling:
  **54 checks passed**, with no short labels/buttons or horizontal overflow.
- Checks include setup, expanded details, preparation, eight-/twelve-second capture,
  tracking loss, extra quality sampling, camera error, completion, and expanded help.
- Keyboard Space opens/closes the disclosure and updates its arrow. A forced blue
  highlight palette does not paint blue pixels into the focused checked control.
- Pose/support/timing order, compact details visibility, reset scroll position,
  blue preparation motion, reduced-motion stillness, and meter fill are verified.
- Visually reviewed setup, capture, expanded checks, completion help, and compact
  verification renders. These use synthetic placeholders; no camera frames saved.
- Rebuilt Windows executable passes frozen icon, both-model loading, and synthetic
  native inference smoke. Bundled preview/controller bytecode matches the tested
  source. Local records: diagnostics/calibration-hierarchy-package-smoke-2026-10-18.json
  and diagnostics/calibration-hierarchy-package-match-2026-10-18.json.

Examples: [Setup](00-setup-neutral.png), [capture](02-eight-start.png),
[expanded checks](00-setup-details-expanded.png), [completion help](14-complete-help.png).
The [100% layout report](layout-report.json) is retained here. Larger-scale output
is local under diagnostics/calibration-hierarchy-scale-150 and -200.

Native Windows interaction, mixed-monitor DPI, screen-reader behavior, and whether
the guidance feels clear during a real calibration still need desktop observation.
Existing camera/hardware verification remains historical evidence, not a new
hardware test of this visual revision.
