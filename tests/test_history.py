import pytest

from shrimply.core.history import HistoryAccumulator


def totals(history):
    return {state: sum(bucket[state] for bucket in history.minutes.values())
            for state in ("good", "drifting", "bad")}


def test_equal_durations_are_equal_despite_different_sampling_rates():
    history = HistoryAccumulator()
    for second in range(30):
        history.push("good", second, 6000 + second)
    history.push("bad", 30., 6030.)
    for tick in range(1, 121):
        now = 30 + tick / 4
        history.push("bad", now, 6000 + now)
    assert totals(history) == {"good": 30., "drifting": 0., "bad": 30.}


def test_missing_observations_and_pause_break_continuity():
    history = HistoryAccumulator()
    history.push("good", 0., 6000.)
    history.push("good", 1., 6001.)
    history.push(None, 1.5, 6001.5)
    history.push("bad", 2., 6002.)
    history.push("bad", 2.25, 6002.25)
    history.reset()
    history.push("good", 100., 6100.)
    assert totals(history) == {"good": 1., "drifting": 0., "bad": .25}


@pytest.mark.parametrize("monotonic,wall", [(10., 6010.), (1., 6200.), (1., 5900.)])
def test_long_gaps_and_clock_changes_are_not_monitored_time(monotonic, wall):
    history = HistoryAccumulator()
    history.push("good", 0., 6000.)
    history.push("good", monotonic, wall)
    assert history.minutes == {}


def test_observed_interval_is_split_across_minutes():
    history = HistoryAccumulator()
    history.push("good", 0., 6059.75)
    history.push("good", .5, 6060.25)
    assert history.minutes[6000]["good"] == .25
    assert history.minutes[6060]["good"] == .25
