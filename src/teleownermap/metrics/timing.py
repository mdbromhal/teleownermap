"""Timing evidence: how unusual is it that two events happened this close together?

Shown as evidence only, never fed into match scores or ownership metrics (docs/decisions.md).
"Close in time" means nothing without knowing what's normal, so every gap is scored as a
percentile against a comparison group the user chooses (e.g. same auction, license type or
year):
- Pair timing: the gap between two entities' events (the closest pair of events of the
  chosen types), against the gaps between every other pair of entities in the group.
- Lead time: how long before an outside event (e.g. an auction deadline) an entity's event
  happened, against the lead times of the rest of the group.

The percentile is the share of the comparison group that is as close or closer, so 2 means
"only 2% of pairs in this group were this close". Both the number of entities and the number
of comparisons are reported. A group is flagged as small by its number of entities, not
comparisons, because pairs grow much faster than entities and aren't independent (each
entity is in many pairs). Every result carries the caveat that the group may itself contain
shell companies.
"""

from __future__ import annotations

import bisect
import itertools
import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

SMALL_GROUP = 30
"""Below this many entities in the group, results are flagged as based on a small group
(a rule of thumb, stated in ASSUMPTIONS.md)."""
MAX_PAIRS = 200_000
"""Larger groups are compared against a seeded random sample of pairs (flagged)."""
CAVEAT = (
    "The comparison group may itself contain shell companies, so this is a comparison with "
    "what happened in the group, not with a clean population."
)


@dataclass(frozen=True)
class TimingResult:
    days: int
    """The observed gap (pair timing) or lead time in days."""
    percentile: float
    """Share (0-100) of the comparison group that is as close or closer."""
    entities: int
    """Entities in the comparison group with events to compare (including the tested ones)."""
    comparisons: int
    """Comparisons the percentile is based on: other pairs (pair timing) or other entities
    (lead time)."""
    small_group: bool
    """Fewer than SMALL_GROUP entities."""
    sampled: bool
    caveat: str = CAVEAT


def closest_gap(a: Iterable[date], b: Iterable[date]) -> int | None:
    """Smallest absolute gap in days between any event of `a` and any event of `b`."""
    b_sorted = sorted(b)
    best = None
    for d in a:
        i = bisect.bisect_left(b_sorted, d)
        for j in (i - 1, i):
            if 0 <= j < len(b_sorted):
                gap = abs((b_sorted[j] - d).days)
                best = gap if best is None else min(best, gap)
    return best


def _percentile(observed: int, baseline: list[int]) -> float:
    """Share of the baseline as close or closer (ties count as "as close")."""
    baseline = sorted(baseline)
    return 100 * bisect.bisect_right(baseline, observed) / len(baseline)


def pair_timing(
    events: Mapping[str, Iterable[date]],
    a: str,
    b: str,
    *,
    seed: int = 0,
) -> TimingResult | None:
    """Score the gap between entities `a` and `b` against every other pair in `events`
    (entity -> event dates, already filtered to the chosen event types and group)."""
    dates = {k: sorted(v) for k, v in events.items() if v}
    if a not in dates or b not in dates:
        return None
    observed = closest_gap(dates[a], dates[b])
    others = [p for p in itertools.combinations(sorted(dates), 2) if set(p) != {a, b}]
    sampled = len(others) > MAX_PAIRS
    if sampled:
        others = random.Random(seed).sample(others, MAX_PAIRS)
    baseline = [g for x, y in others if (g := closest_gap(dates[x], dates[y])) is not None]
    if not baseline:
        return None
    return TimingResult(observed, _percentile(observed, baseline), len(dates), len(baseline),
                        len(dates) < SMALL_GROUP, sampled)  # fmt: skip


def lead_time(
    events: Mapping[str, Iterable[date]],
    entity: str,
    outside: date,
) -> TimingResult | None:
    """Score how shortly before `outside` the entity's last prior event happened, against
    the same lead time for every other entity in the group. Entities with no event before
    `outside` have no lead time and are left out."""

    def lead(dates: Iterable[date]) -> int | None:
        before = [d for d in dates if d <= outside]
        return (outside - max(before)).days if before else None

    observed = lead(events.get(entity, ()))
    if observed is None:
        return None
    baseline = [x for k, v in events.items() if k != entity and (x := lead(v)) is not None]
    if not baseline:
        return None
    entities = len(baseline) + 1
    return TimingResult(observed, _percentile(observed, baseline), entities, len(baseline),
                        entities < SMALL_GROUP, False)  # fmt: skip
