# Settings layout polish

The enclosed sections remain, but their headings now sit fully inside each
border, sharing the contents' left inset. Borders are subdued and the heavy
outer tab frame is replaced with a simple divider. Settings-only styling leaves
other windows alone. Numeric fields share a 112-pixel logical width; Appearance
uses aligned label/field rows. The initial window size is capped to available
screen space, with vertical scrolling at smaller sizes.

- [Tracking](tab-0.png)
- [Reminders](tab-1.png)
- [Appearance](tab-2.png)
- [General](tab-3.png)
- [Separate suggestion editor](suggestions.png)
- [Tracking at minimum size](compact-0.png)
- [Reminders at minimum size](compact-1.png)
- [Reminders at Qt scale factor 1.5](reminders-scale-1.5.png)
- [Reminders at Qt scale factor 2](reminders-scale-2.png)

The suggestion editor opens modelessly through Edit suggestions. It supports
multiline instructions and Add/Update/Remove, clarifies when edits are saved,
disables Update/Remove with no selection, and closes with Settings. Opening it
does not save or change reminder progress. Returning to an open editor reuses
the same window. Add and Update are explicit; all other preferences still save
as their controls change.

Validation: 299 tests passed, including multiline editing, removing the last
suggestion, modeless reuse, cleanup, and existing no-camera-probe behavior.
Real Qt renders were reviewed at the normal size and 620 × 500 logical minimum.
All four task tabs fit horizontally at minimum size at Qt scale factors 1.5 and
2 (reported DPR 1.5 and 2). These are widget checks, not physical display,
screen-reader, or macOS verification. Captures use synthetic settings/history;
no webcam imagery or personal history was saved.
