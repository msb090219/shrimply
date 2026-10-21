import pytest

from shrimply.core.breaks import BreakReminder


def observe_for(reminder, start, seconds):
    return [reminder.observe(True, start + tick) for tick in range(seconds + 1)]


def test_only_observed_sitting_counts_and_a_due_reminder_does_not_repeat():
    reminder = BreakReminder(True, 10)
    assert not any(observe_for(reminder, 0, 6))
    reminder.observe(False, 7)
    assert not any(observe_for(reminder, 100, 3))
    assert reminder.elapsed == 9
    assert reminder.observe(True, 104)
    assert reminder.pending
    assert not any(observe_for(reminder, 105, 30))
    assert reminder.elapsed == 10


@pytest.mark.parametrize("gap", [3., 3600., -10.])
def test_stalls_sleep_and_clock_reversals_are_not_sitting(gap):
    reminder = BreakReminder(True, 10)
    observe_for(reminder, 0, 5)
    reminder.observe(True, 5 + gap)
    assert reminder.elapsed == 5


def test_pause_retains_progress_but_never_bridges_the_pause():
    reminder = BreakReminder(True, 10)
    observe_for(reminder, 0, 5)
    reminder.pause()
    reminder.observe(True, 6)
    assert reminder.elapsed == 5
    reminder.observe(True, 7)
    assert reminder.elapsed == 6


def test_snooze_requires_five_more_minutes_of_detected_sitting():
    reminder = BreakReminder(True, 10)
    observe_for(reminder, 0, 10)
    reminder.snooze()
    assert reminder.remaining == 300
    assert reminder.snoozed and not reminder.pending
    reminder.observe(False, 20)
    assert not any(observe_for(reminder, 1000, 299))
    assert reminder.observe(True, 1300)
    assert reminder.pending


def test_take_break_suspends_sitting_until_the_countdown_ends():
    reminder = BreakReminder(True, 10)
    observe_for(reminder, 0, 10)
    reminder.take_break(10.)
    assert reminder.in_break
    assert not any(observe_for(reminder, 11, 100))
    assert reminder.elapsed == 10
    reminder.tick(130.)
    assert not reminder.in_break
    assert reminder.remaining == 10
    assert reminder.elapsed == 0
    assert not reminder.pending and not reminder.snoozed
    reminder.observe(True, 131)
    assert reminder.elapsed == 0


def test_unrelated_settings_do_not_reset_snooze_and_disabling_clears_it():
    reminder = BreakReminder(True, 10)
    observe_for(reminder, 0, 10)
    reminder.snooze()
    reminder.configure(True, 10)
    assert reminder.snoozed and reminder.remaining == 300
    reminder.configure(False, 10)
    assert not reminder.pending and reminder.elapsed == 0
    assert not any(observe_for(reminder, 100, 20))
    reminder.configure(True, 10)
    assert reminder.remaining == 10


def test_interval_change_preserves_sitting_time_and_recalculates_due():
    reminder = BreakReminder(True, 20)
    observe_for(reminder, 0, 10)
    reminder.configure(True, 5)
    assert reminder.observe(True, 11)
    reminder.configure(True, 30)
    assert not reminder.pending and reminder.remaining == 20


def test_break_ends_without_camera_frames_and_never_counts_the_gap():
    reminder = BreakReminder(True, 10)
    reminder.take_break(100.)
    assert reminder.break_remaining(130.) == 90
    reminder.tick(1000.)
    assert not reminder.in_break and reminder.remaining == 10
    reminder.observe(True, 1000.)
    assert reminder.elapsed == 0
    reminder.observe(True, 1001.)
    assert reminder.elapsed == 1


def test_break_early_end_and_duplicate_start_do_not_extend_the_deadline():
    reminder = BreakReminder(True, 10)
    reminder.take_break(0.)
    reminder.take_break(30.)
    reminder.snooze()
    assert reminder.break_remaining(30.) == 90
    reminder.end_break()
    assert not reminder.in_break and reminder.remaining == 10


def test_preferences_preserve_active_break_except_when_disabled():
    reminder = BreakReminder(True, 10)
    reminder.take_break(0.)
    reminder.configure(True, 20)
    assert reminder.in_break and reminder.break_remaining(30.) == 90
    reminder.tick(120.)
    assert reminder.remaining == 20
    reminder.take_break(200.)
    reminder.configure(False, 20)
    assert not reminder.in_break and reminder.elapsed == 0


def test_custom_break_length_changes_next_break_without_extending_current_one():
    reminder = BreakReminder(True, 1500, 300)
    reminder.take_break(0.)
    reminder.configure(True, 1500, 600)
    assert reminder.break_remaining(60.) == 240
    reminder.tick(300.)
    reminder.take_break(400.)
    assert reminder.break_remaining(400.) == 600


def test_later_choices_and_skip_use_detected_sitting():
    reminder = BreakReminder(True, 1500)
    reminder.pending = True
    reminder.snooze(600)
    assert reminder.remaining == 600
    reminder.observe(False, 100.)
    assert not any(observe_for(reminder, 200, 599))
    assert reminder.observe(True, 800)
    reminder.skip()
    assert not reminder.pending and not reminder.snoozed
    assert reminder.remaining == 1500
