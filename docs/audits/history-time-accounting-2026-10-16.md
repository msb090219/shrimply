# T06: elapsed-time history

Completed in source on 16 October 2026. The full automated suite passes 103 tests.

New history stores observed seconds in each state, rather than counting frames.
Thirty seconds good at 1 fps and thirty seconds bad at 4 fps now produce 50% good.

## Recording rules

- An interval belongs to the last observed scorable state until the next sample.
- Only consecutive usable observations at most 2.5 seconds apart contribute.
- Missing measurements, explicit pause, idle-stop, camera failure/restart, baseline
  reset, and calibration break continuity. No time is extrapolated after the last
  observation at shutdown.
- Elapsed duration comes from a monotonic clock. Wall time assigns minute/day
  boundaries. Large clock adjustments and long gaps are excluded.
- Intervals crossing a minute are split. Daily summaries use local calendar dates,
  including 23/25-hour days, rather than subtracting fixed 24-hour intervals.

## Preservation and display

The old SQLite table is retained unchanged. A separate `duration_rollup` table is
created when the updated app opens its database. Timed writes are additive, so a
restart in the same minute does not replace an earlier timed contribution.
Successfully written pending buckets are cleared; failed writes retain their data.

Old-only days remain readable as approximate sample-based percentages, marked
`~`. When a day contains timed data, the percentage and monitored minutes use
only that timed data; old samples are not silently mixed with seconds. The UI
explains this distinction. An old day cannot be reconstructed into accurate time
percentages because its original sampling intervals were not stored.

## Verification and limits

Tests cover the 1-to-4 fps change through controller/storage, missing evidence,
pause/reset continuity, long gaps and clock changes, minute splitting, additive
writes across reopen, an original-schema database, invalid durations, failed
flushes, old/new UI labels, and a simulated daylight-saving boundary.

No live user database was edited during testing. The running app and existing
executable do not hot-reload these changes; restart from updated source to use
them. A refreshed packaged build has not been tested for this task. Timing is
still sampled, with transition uncertainty bounded by the observation interval;
this change does not establish posture-classification accuracy or full-day stability.
