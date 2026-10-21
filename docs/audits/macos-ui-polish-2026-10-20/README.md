# Mac UI polish — 20 October 2026

Settings navigation and break-suggestion actions are aligned. The existing boxed,
single-column Settings layout is retained. This is a maintenance follow-up to
M05/M06 (U16/U17); shared layout code still needs native Windows review before
the next Windows build.

## Review and changes

1. **Tracking and category navigation — fixed.** The category strip was centred
   over the content. Tabs now use their natural widths and start at the left
   edge at both tested widths. See [before](before/light-960-tracking-top.png)
   and [after](after/light-960-tracking-top.png).
2. **Alerts and breaks — fixed.** Add, Update and Remove previously occupied
   uneven grid positions, with Remove on another row. They now share one row,
   equal minimum widths, accessible names and action tooltips. Saved suggestions
   have an explicit label and full-row selection styling. The list and fields
   align side by side when space allows and stack in narrow windows; all five
   default suggestions remain visible. See [before](before/dark-960-alerts-editor.png),
   [wide editor](after/dark-960-alerts-editor-detail.png) and
   [narrow editor](after/dark-620-alerts-editor.png).
3. **Appearance — polished.** Preview separators use the theme's subdued border
   colour. Existing controls and boxed sections remain readable in the inspected
   [narrow Light layout](after/light-620-appearance-bottom.png).
4. **General — checked.** Inspected the top and lower sections for wrapping,
   button placement and spacing; no further change was needed in the sampled
   [Light](after/light-960-general-top.png) and
   [Dark](before/dark-960-general-bottom.png) views.
5. **Dashboard — checked, empty profile only.** The setup and empty-history cards
   remain contained at [620 points](after/dashboard-620.png) and
   [960 points](after/dashboard-960.png). These captures use an isolated profile,
   not the user's history or a live tracking session.
6. **About, calibration and reminder — layout checked.** The inspected
   [About](after/dark-about.png), [calibration placeholder](after/light-calibration.png)
   and [break reminder](after/dark-break-reminder.png) have readable text and
   contained actions. Calibration is a staged instruction with no camera frames;
   it does not prove camera startup or completion of calibration. The reminder
   was captured in its example mode.

## Evidence and verification

`tools/capture_settings.py` captures actual Cocoa/Qt widgets using temporary
configuration and history, with tracking paused and no camera opened. Settings
captures cover all four categories, Light and Dark, at 620 and 960 logical points,
including their lower sections. Screenshots are widget grabs at native display
scale, not browser renders. The numbered review above identifies the inspected
representative evidence; capture files alone are not a claim that every possible
state was manually reviewed.

- [Geometry](after/geometry.json): tab bar x=0 at both widths; all three suggestion
  buttons share a baseline and size. The narrow editor retains the full list.
- [Automated suite](tests.txt): **551 passed, 2 skipped**. Windows-only native
  checks are skipped on this Mac. Settings tests exercise actual Add/Update/Remove
  clicks, keyboard behavior, and both responsive layouts.
- [Packaged smoke](packaged-smoke.json): frozen 1.3.0 bundle loads Qt assets and
  both models and performs native inference successfully.
- The bundle passed `codesign --verify --deep --strict` (local signature only,
  not Developer ID signing or notarization). [Installation](installation.json)
  records source-module comparisons, destination and previous-app backup.

No new live camera test was needed for these layout changes. Camera aspect-ratio
handling and the earlier posture-notification removal remain in the verified
bundle. VoiceOver, additional displays, every enlarged-font setting, physical
keyboard traversal of every screen and native Windows appearance were not
verified by this pass.
