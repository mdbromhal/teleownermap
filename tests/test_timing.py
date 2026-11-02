"""Tests for timing evidence on hand-computed examples."""

from datetime import date, timedelta

from teleownermap.metrics import timing
from teleownermap.metrics.timing import closest_gap, lead_time, pair_timing

D0 = date(2014, 1, 1)


def days(*offsets):
    return [D0 + timedelta(days=o) for o in offsets]


def test_closest_gap_uses_the_nearest_events():
    assert closest_gap(days(0, 100), days(97, 300)) == 3
    assert closest_gap(days(10), days(10)) == 0


def test_pair_timing_percentile_against_other_pairs():
    # A and B filed 1 day apart; every other pair is 10+ days apart.
    events = {"A": days(0), "B": days(1), "C": days(20), "D": days(40)}
    r = pair_timing(events, "A", "B")
    # Other pairs: A-C 20, A-D 40, B-C 19, B-D 39, C-D 20 -> none as close as 1 day.
    assert (r.days, r.percentile, r.entities, r.comparisons) == (1, 0.0, 4, 5)
    assert r.small_group and not r.sampled and r.caveat == timing.CAVEAT


def test_ties_count_as_close():
    events = {"A": days(0), "B": days(5), "C": days(100), "D": days(105)}
    # Baseline: A-C 100, A-D 105, B-C 95, B-D 100, C-D 5 -> 1 of 5 as close as 5 days.
    assert pair_timing(events, "A", "B").percentile == 20.0


def test_lead_time_before_an_outside_event():
    deadline = D0 + timedelta(days=100)
    events = {"A": days(99), "B": days(10), "C": days(50), "D": days(150)}
    r = lead_time(events, "A", deadline)
    # A filed 1 day before; B 90 and C 50 days before; D only after (left out).
    assert (r.days, r.percentile, r.entities, r.comparisons) == (1, 0.0, 3, 2)


def test_missing_entities_or_events_give_no_result():
    assert pair_timing({"A": days(0)}, "A", "B") is None
    assert lead_time({"A": days(200)}, "A", D0) is None


def test_large_groups_are_sampled_reproducibly(monkeypatch):
    monkeypatch.setattr(timing, "MAX_PAIRS", 10)
    events = {f"E{i}": days(i * 3) for i in range(10)}
    r1 = pair_timing(events, "E0", "E1", seed=1)
    r2 = pair_timing(events, "E0", "E1", seed=1)
    assert r1 == r2 and r1.sampled and r1.comparisons == 10 and r1.entities == 10


def test_small_group_is_judged_by_entities_not_pairs():
    # 9 entities make 35 other pairs: more than 30 comparisons, but still a small group.
    events = {f"E{i}": days(i * 3) for i in range(9)}
    r = pair_timing(events, "E0", "E1")
    assert r.comparisons == 35 and r.entities == 9 and r.small_group
    big = {f"E{i}": days(i) for i in range(30)}
    assert not pair_timing(big, "E0", "E1").small_group
