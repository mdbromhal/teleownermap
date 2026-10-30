"""Ownership probabilities and anonymity metrics via an absorbing Markov chain.

Model (see docs/decisions.md):
- Walk upward from a start entity (e.g. a licensee). From each company, step to each owner
  with probability share x confidence. Whatever share is unaccounted for flows to that
  company's "unknown owner" endpoint (or "public shareholders" for publicly traded
  companies), so ignorance is explicit rather than hidden.
- People, governments and unclassified parties end the walk (absorbing states). A company
  with no recorded owners sends its whole share to its unknown owner.
- Nominee links ("this registered party acts for that party") pass ownership through: a
  person who is a nominee doesn't end the walk. Their holding flows on to the party they
  act for, weighted by the nominee link's share x confidence, and whatever remains stays
  with the nominee themself as a possible real owner.
- With only documented edges at confidence 1, this reduces to multiplying equity stakes
  along each path (the documented-only view).
- Share ranges: `analyze_range` reports the true lower and upper bound of every metric over
  all share values in their ranges. `analyze` evaluates one scenario ("low" = every
  share_min, "high" = every share_max, "mid" = the optional, labeled simplification).
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from scipy.optimize import minimize

Scenario = Literal["low", "high", "mid"]
TERMINAL_TYPES = frozenset({"person", "government", "unclassified"})
EPS = 1e-12


def unknown_owner(company: str) -> str:
    return f"unknown:{company}"


def public_shareholders(company: str) -> str:
    return f"public:{company}"


def is_unknown(node: str) -> bool:
    return node.startswith("unknown:")


def is_public(node: str) -> bool:
    return node.startswith("public:")


@dataclass(frozen=True)
class Stake:
    """One statement that `owner` holds an interest in `owned`.

    Shares are fractions in [0, 1]. A share that isn't stated is None and is treated as the
    full range [0, 1]. `confidence` is 1 for documented links and the match/inference
    confidence for inferred ones. `notes` records disagreements found when merging sources.
    """

    owner: str
    owned: str
    share_min: float | None = None
    share_max: float | None = None
    confidence: float = 1.0
    graph: Literal["equity", "control", "nominee"] = "equity"
    """`nominee` links run from the hidden party (owner) to the registered party (owned)."""
    rel_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def lo(self) -> float:
        return 0.0 if self.share_min is None else self.share_min

    @property
    def hi(self) -> float:
        return 1.0 if self.share_max is None else self.share_max

    def share(self, scenario: Scenario) -> float:
        return {"low": self.lo, "high": self.hi, "mid": (self.lo + self.hi) / 2}[scenario]


def combine_statements(stakes: list[Stake]) -> list[Stake]:
    """Merge statements about the same (owner, owned, graph) into one range.

    Disagreeing sources become a range spanning every reported value, and every source
    rel_id is kept. Unstated shares widen the range to [0, 1]. Confidence is the highest
    among the statements (a documented statement makes the link documented); any
    disagreement in shares or confidence is recorded in `notes`.
    """
    groups: dict[tuple[str, str, str], list[Stake]] = defaultdict(list)
    for s in stakes:
        groups[(s.owner, s.owned, s.graph)].append(s)
    merged = []
    for (owner, owned, graph), group in groups.items():
        notes = [n for s in group for n in s.notes]
        ranges = {(s.lo, s.hi) for s in group}
        if len(ranges) > 1:
            shown = ", ".join(_fmt_range(lo, hi) for lo, hi in sorted(ranges))
            notes.append(f"{owner} → {owned}: sources disagree on share ({shown})")
        confidences = {s.confidence for s in group}
        if len(confidences) > 1:
            shown = ", ".join(f"{c:g}" for c in sorted(confidences))
            notes.append(
                f"{owner} → {owned}: sources disagree on confidence ({shown}); highest used"
            )
        merged.append(
            Stake(
                owner=owner,
                owned=owned,
                share_min=min(s.lo for s in group),
                share_max=max(s.hi for s in group),
                confidence=max(confidences),
                graph=graph,
                rel_ids=tuple(r for s in group for r in s.rel_ids),
                notes=tuple(notes),
            )
        )
    return merged


def _fmt_range(lo: float, hi: float) -> str:
    return f"{lo:.0%}" if lo == hi else f"{lo:.0%}–{hi:.0%}"


class ClosedOwnershipLoopError(ValueError):
    """Companies own each other entirely, so no ownership ever leaves the loop."""


@dataclass
class OwnershipResult:
    start: str
    scenario: str
    probabilities: dict[str, float]
    """Probability that each endpoint is the ultimate owner (includes unknown and public)."""
    unknown_share: float
    public_share: float
    entropy_bits: float
    """Shannon entropy over all endpoints, each unknown endpoint counted separately."""
    entropy_known_bits: float | None
    """Entropy over known owners only, renormalized; None if no known owner."""
    anonymity_set_size: int
    """Number of known parties with nonzero probability."""
    hop_distribution: dict[int, float]
    """Probability of reaching an endpoint after exactly k hops."""
    expected_hops: float
    overallocated: list[str] = field(default_factory=list)
    """Companies whose owners' shares summed to more than 100% and were scaled down."""
    discrepancies: list[str] = field(default_factory=list)
    """Disagreements between sources on links used in this result."""


Key = tuple[str, str, str]


def _key(s: Stake) -> Key:
    return (s.owner, s.owned, s.graph)


def _equity(stakes: list[Stake]) -> list[Stake]:
    """Links the ownership walk follows: equity, plus nominee pass-throughs."""
    return combine_statements([s for s in stakes if s.graph in ("equity", "nominee")])


def _solve(
    merged: list[Stake],
    start: str,
    entity_types: dict[str, str],
    shares: dict[Key, float],
    publicly_traded: frozenset[str],
    scenario: str,
    max_hops: int = 50,
) -> OwnershipResult:
    owners_of: dict[str, list[tuple[Stake, float]]] = defaultdict(list)
    for s in merged:
        owners_of[s.owned].append((s, shares[_key(s)] * s.confidence))

    transient = _reachable_companies(merged, start, entity_types)
    if not transient:  # start is itself an ultimate party
        return OwnershipResult(start, scenario, {start: 1.0}, 0.0, 0.0, 0.0, 0.0, 1, {0: 1.0}, 0.0)

    t_index = {n: i for i, n in enumerate(transient)}
    absorbing: list[str] = []
    a_index: dict[str, int] = {}

    def a_idx(node: str) -> int:
        if node not in a_index:
            a_index[node] = len(absorbing)
            absorbing.append(node)
        return a_index[node]

    Q = np.zeros((len(transient), len(transient)))
    R_entries: list[tuple[int, int, float]] = []
    overallocated, discrepancies = [], []
    for node in transient:
        i = t_index[node]
        total = sum(w for _, w in owners_of[node])
        scale = 1.0
        if total > 1.0 + 1e-9:
            overallocated.append(node)
            scale = 1.0 / total
        for stake, w in owners_of[node]:
            discrepancies.extend(stake.notes)
            w *= scale
            if w <= 0:
                continue
            if stake.owner in t_index:
                Q[i, t_index[stake.owner]] += w
            else:  # every non-terminal owner was collected as transient
                R_entries.append((i, a_idx(stake.owner), w))
        leftover = 1.0 - min(total, 1.0)
        if leftover > EPS:
            if entity_types.get(node) in TERMINAL_TYPES:  # a nominee: may be the real owner
                rest = node
            elif node in publicly_traded:
                rest = public_shareholders(node)
            else:
                rest = unknown_owner(node)
            R_entries.append((i, a_idx(rest), leftover))

    R = np.zeros((len(transient), len(absorbing)))
    for i, j, w in R_entries:
        R[i, j] += w

    try:
        B = np.linalg.solve(np.eye(len(transient)) - Q, R)
    except np.linalg.LinAlgError as e:
        raise ClosedOwnershipLoopError(
            f"Ownership loop with no outside owner among: {', '.join(transient)}"
        ) from e

    row = B[t_index[start]]
    probs = {absorbing[j]: float(row[j]) for j in range(len(absorbing)) if row[j] > EPS}
    known = {n: p for n, p in probs.items() if not is_unknown(n) and not is_public(n)}

    # Hop distribution: probability mass absorbed after exactly k steps.
    hops: dict[int, float] = {}
    v = np.zeros(len(transient))
    v[t_index[start]] = 1.0
    for k in range(1, max_hops + 1):
        absorbed = float((v @ R).sum())
        if absorbed > EPS:
            hops[k] = absorbed
        v = v @ Q
        if v.sum() < EPS:
            break

    known_total = sum(known.values())
    return OwnershipResult(
        start=start,
        scenario=scenario,
        probabilities=probs,
        unknown_share=sum(p for n, p in probs.items() if is_unknown(n)),
        public_share=sum(p for n, p in probs.items() if is_public(n)),
        entropy_bits=_entropy(probs.values()),
        entropy_known_bits=(
            _entropy(p / known_total for p in known.values()) if known_total > 0 else None
        ),
        anonymity_set_size=len(known),
        hop_distribution=hops,
        expected_hops=sum(k * p for k, p in hops.items()),
        overallocated=overallocated,
        discrepancies=list(dict.fromkeys(discrepancies)),
    )


def _reachable_companies(
    merged: list[Stake], start: str, entity_types: dict[str, str]
) -> list[str]:
    """Companies (and nominees) reachable upward from start: the transient states."""
    owners: dict[str, list[str]] = defaultdict(list)
    nominees = {s.owned for s in merged if s.graph == "nominee"}
    for s in merged:
        owners[s.owned].append(s.owner)
    found, seen, queue = [], {start}, deque([start])
    while queue:
        node = queue.popleft()
        if entity_types.get(node) in TERMINAL_TYPES and node not in nominees:
            continue
        found.append(node)
        for o in owners[node]:
            if o not in seen:
                seen.add(o)
                queue.append(o)
    return found


def analyze(
    stakes: list[Stake],
    start: str,
    entity_types: dict[str, str],
    scenario: Scenario = "low",
    publicly_traded: Iterable[str] = (),
) -> OwnershipResult:
    """Compute ownership probabilities and metrics for `start` in one share scenario."""
    merged = _equity(stakes)
    shares = {_key(s): s.share(scenario) for s in merged}
    return _solve(merged, start, entity_types, shares, frozenset(publicly_traded), scenario)


@dataclass
class RangeResult:
    """Lower and upper bound of every metric over all share values within their ranges."""

    start: str
    probabilities: dict[str, tuple[float, float]]
    unknown_share: tuple[float, float]
    public_share: tuple[float, float]
    entropy_bits: tuple[float, float]
    entropy_known_bits: tuple[float, float] | None
    anonymity_set_size: tuple[int, int]
    expected_hops: tuple[float, float]
    exact: bool
    """True if every combination of range ends was checked. Entropy bounds are additionally
    refined by numerical search, since entropy can peak between range ends."""
    overallocated: list[str]
    discrepancies: list[str]
    mid: OwnershipResult | None = None
    """Optional midpoint view: a labeled simplification, not a bound."""


def analyze_range(
    stakes: list[Stake],
    start: str,
    entity_types: dict[str, str],
    publicly_traded: Iterable[str] = (),
    include_mid: bool = False,
    max_combinations: int = 4096,
    seed: int = 0,
) -> RangeResult:
    """Bound every metric over all share values within their reported ranges.

    Owner probabilities, unknown/public share and expected hops change monotonically as any
    single share moves, so their bounds occur at combinations of range ends; all
    combinations are checked when there are at most `max_combinations` (otherwise a seeded
    random sample is checked and `exact` is False). Entropy can peak between range ends, so
    its bounds are then refined by a bounded numerical search.
    """
    merged = _equity(stakes)
    public = frozenset(publicly_traded)
    relevant = set(_reachable_companies(merged, start, entity_types))
    ranged = [s for s in merged if s.owned in relevant and s.lo < s.hi]
    base = {_key(s): s.lo for s in merged}
    keys = [_key(s) for s in ranged]
    bounds = [(s.lo, s.hi) for s in ranged]

    def solve(x) -> OwnershipResult | None:
        shares = dict(base)
        shares.update(zip(keys, (float(v) for v in x), strict=True))
        try:
            return _solve(merged, start, entity_types, shares, public, "range")
        except ClosedOwnershipLoopError:
            return None

    n = len(ranged)
    exact = 2**n <= max_combinations
    if exact:
        corners = list(itertools.product(*bounds))
    else:
        rng = np.random.default_rng(seed)
        corners = [tuple(lo for lo, _ in bounds), tuple(hi for _, hi in bounds)]
        corners += [tuple(rng.choice(b) for b in bounds) for _ in range(max_combinations - 2)]

    points = [(c, r) for c in corners if (r := solve(c)) is not None]
    if not points:
        raise ClosedOwnershipLoopError(f"Every share combination closes an ownership loop: {start}")
    results = [r for _, r in points]

    entropy_lo, entropy_hi = _refine_entropy(points, bounds, solve, "entropy_bits")
    known_points = [(c, r) for c, r in points if r.entropy_known_bits is not None]
    entropy_known = (
        _refine_entropy(known_points, bounds, solve, "entropy_known_bits") if known_points else None
    )

    owners = {n for r in results for n in r.probabilities}
    mid = None
    if include_mid:
        mid = analyze(stakes, start, entity_types, "mid", public)
    return RangeResult(
        start=start,
        probabilities={
            o: _span(r.probabilities.get(o, 0.0) for r in results) for o in sorted(owners)
        },
        unknown_share=_span(r.unknown_share for r in results),
        public_share=_span(r.public_share for r in results),
        entropy_bits=(entropy_lo, entropy_hi),
        entropy_known_bits=entropy_known,
        anonymity_set_size=_span(r.anonymity_set_size for r in results),
        expected_hops=_span(r.expected_hops for r in results),
        exact=exact,
        overallocated=sorted({c for r in results for c in r.overallocated}),
        discrepancies=list(dict.fromkeys(d for r in results for d in r.discrepancies)),
        mid=mid,
    )


def _span(values: Iterable[float]) -> tuple:
    values = list(values)
    return (min(values), max(values))


def _refine_entropy(points, bounds, solve, attr: str) -> tuple[float, float]:
    """Entropy bounds: best range-end combination, refined by bounded numerical search."""
    lo = min(points, key=lambda p: getattr(p[1], attr))
    hi = max(points, key=lambda p: getattr(p[1], attr))
    best_lo, best_hi = getattr(lo[1], attr), getattr(hi[1], attr)
    if not bounds:
        return best_lo, best_hi

    def value(x) -> float | None:
        r = solve(x)
        return None if r is None else getattr(r, attr)

    midpoint = [(a + b) / 2 for a, b in bounds]
    for sign, starts in ((1, [lo[0], midpoint]), (-1, [hi[0], midpoint])):

        def objective(x, sign=sign):
            v = value(x)
            return 1e6 if v is None else sign * v

        for x0 in starts:
            res = minimize(objective, np.array(x0, dtype=float), bounds=bounds, method="L-BFGS-B")
            v = value(res.x)
            if v is not None:
                best_lo, best_hi = min(best_lo, v), max(best_hi, v)
    return best_lo, best_hi


def _entropy(ps: Iterable[float]) -> float:
    return -sum(p * math.log2(p) for p in ps if p > 0)


def _owners_by_link(stakes: list[Stake], graphs: tuple[str, ...]) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = defaultdict(set)
    for s in stakes:
        if s.graph in graphs:
            owners[s.owned].add(s.owner)
    return owners


def _upward(owners: dict[str, set[str]], sources: dict[str, int]) -> dict[str, int]:
    """Fewest hops upward from any source (sources may start at different distances)."""
    dist = dict(sources)
    heap = [(d, n) for n, d in sources.items()]
    heapq.heapify(heap)
    while heap:
        d, node = heapq.heappop(heap)
        if d > dist[node]:
            continue
        for o in owners[node]:
            if d + 1 < dist.get(o, math.inf):
                dist[o] = d + 1
                heapq.heappush(heap, (d + 1, o))
    return dist


def control_reach(stakes: list[Stake], start: str) -> dict[str, int]:
    """Parties holding control over the start's ownership chain, with the fewest hops to each.

    Control links are looked for anywhere along the chain (the start and its equity/nominee
    owners upward), so a party controlling a parent two levels up is reported at 3 hops.
    From each controller, control and nominee links are followed further up, so control
    exercised through a proxy reaches the party the proxy acts for. The control graph has
    no weights, so no probabilities or entropy are invented for it.
    """
    chain = _upward(_owners_by_link(stakes, ("equity", "nominee")), {start: 0})
    controllers = _owners_by_link(stakes, ("control", "nominee"))
    direct_control = _owners_by_link(stakes, ("control",))
    via_control = {c for node in chain for c in direct_control[node]}
    reached = _upward(controllers, chain)
    # Report parties reached through a control link (not equity-only owners in the chain).
    controlled_from = set(via_control)
    queue = deque(via_control)
    while queue:
        for c in controllers[queue.popleft()]:
            if c not in controlled_from:
                controlled_from.add(c)
                queue.append(c)
    return {p: reached[p] for p in controlled_from if p != start}


def control_without_equity(stakes: list[Stake], start: str) -> dict[str, int]:
    """Parties with control over the chain but no equity link into it (shown as 0% equity).

    The chain is the start, its equity/nominee owners upward, and the parties reached through
    control. Equity a party holds elsewhere (e.g. in an unrelated company) doesn't count.
    A controller whose own equity owners (upward) hold equity in the licensee's ownership
    chain is backed by that equity, e.g. a general partner with no partnership shares that
    is owned by the limited partner. A nominee arrangement over a controller isn't equity.
    """
    reach = control_reach(stakes, start)
    owners = _owners_by_link(stakes, ("equity", "nominee"))
    chain = _upward(owners, {start: 0, **dict.fromkeys(reach, 0)})
    equity_parties = {o for node in chain for o in owners[node]}
    ownership_chain = _upward(owners, {start: 0})
    chain_holders = {o for node in ownership_chain for o in owners[node]}
    equity_owners = _owners_by_link(stakes, ("equity",))

    def backed(p: str) -> bool:
        lineage = set(_upward(equity_owners, {p: 0})) - {p}
        return p in equity_parties or bool(lineage & chain_holders)

    return {p: h for p, h in reach.items() if not backed(p)}
