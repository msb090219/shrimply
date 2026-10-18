# Utility icons

- [Tracking page](tracking.png)
- [Paused page](paused.png)
- [Progress page](progress.png)
- [Pause control detail](pause.png)
- [Resume control detail](resume.png)
- [Refresh control detail](refresh.png)

Pause and Resume retain text, with matching monochrome line icons. The icon
changes with tracking state, without rebuilding it on every refresh tick.
Progress refresh is a 32-pixel logical target with an 18-pixel arrow, named
"Refresh progress" for accessibility, a tooltip and Alt+R. The Settings cog
is included in this build. Specific actions such as calibration and break
acknowledgement retain text. No navigation or tracking behavior changed.

All three icons share the same original drawing/rendering helper and update
with the text palette. 317 tests pass, including state-switching icons, action
routing and named refresh. Captures are real Qt renders with synthetic state.
Live desktop interaction and mixed-display DPI behavior remain to be checked.
