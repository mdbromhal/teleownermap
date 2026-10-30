"""Metrics tests on small hand-computed examples."""

import math

import pytest

from teleownermap.metrics.ownership import (
    ClosedOwnershipLoopError,
    Stake,
    analyze,
    analyze_range,
    combine_statements,
    control_reach,
    control_without_equity,
    public_shareholders,
    unknown_owner,
)


def exact(owner, owned, share, **kw):
    return Stake(owner, owned, share, share, **kw)


def H(*ps):
    return -sum(p * math.log2(p) for p in ps)


def test_single_chain_to_one_person():
    stakes = [exact("A", "L", 1.0), exact("P", "A", 1.0)]
    r = analyze(stakes, "L", {"L": "company", "A": "company", "P": "person"})
    assert r.probabilities == pytest.approx({"P": 1.0})
    assert r.entropy_bits == pytest.approx(0.0)
    assert r.anonymity_set_size == 1
    assert r.hop_distribution == pytest.approx({2: 1.0})
    assert r.expected_hops == pytest.approx(2.0)


def test_documented_only_equals_multiplying_stakes():
    # L <- 60% A <- 50% P ; P should own 30% of L, the rest unaccounted.
    stakes = [exact("A", "L", 0.6), exact("P", "A", 0.5)]
    r = analyze(stakes, "L", {"L": "company", "A": "company", "P": "person"})
    assert r.probabilities["P"] == pytest.approx(0.30)
    assert r.probabilities[unknown_owner("L")] == pytest.approx(0.40)
    assert r.probabilities[unknown_owner("A")] == pytest.approx(0.30)
    assert r.unknown_share == pytest.approx(0.70)


def test_azerfon_shaped_example():
    # 72% via a shell split evenly between two people; 28% unaccounted.
    types = {"L": "company", "S": "company", "D1": "person", "D2": "person"}
    stakes = [exact("S", "L", 0.72), exact("D1", "S", 0.5), exact("D2", "S", 0.5)]
    r = analyze(stakes, "L", types)
    assert r.probabilities["D1"] == pytest.approx(0.36)
    assert r.probabilities["D2"] == pytest.approx(0.36)
    assert r.entropy_bits == pytest.approx(H(0.36, 0.36, 0.28))
    assert r.entropy_known_bits == pytest.approx(1.0)
    assert r.anonymity_set_size == 2
    assert r.hop_distribution == pytest.approx({1: 0.28, 2: 0.72})


def test_range_bounds_and_optional_midpoint():
    stakes = [Stake("P", "L", 0.25, 0.5)]
    r = analyze_range(stakes, "L", {"L": "company", "P": "person"}, include_mid=True)
    assert r.exact
    assert r.probabilities["P"] == pytest.approx((0.25, 0.5))
    assert r.unknown_share == pytest.approx((0.5, 0.75))
    assert r.entropy_bits == pytest.approx((H(0.25, 0.75), 1.0), abs=1e-6)
    assert r.mid.probabilities["P"] == pytest.approx(0.375)


def test_entropy_bound_found_between_range_ends():
    # P owns 30-70%: entropy is 0.881 bits at both ends but peaks at 1 bit at 50%.
    # Checking only the range ends would understate the upper bound.
    r = analyze_range([Stake("P", "L", 0.3, 0.7)], "L", {"L": "company", "P": "person"})
    assert r.entropy_bits[0] == pytest.approx(H(0.3, 0.7), abs=1e-6)
    assert r.entropy_bits[1] == pytest.approx(1.0, abs=1e-6)


def test_probability_bounds_across_two_ranged_links():
    # L <- [0.2, 0.6] A <- [0.5, 1.0] P : P owns between 10% and 60% of L.
    types = {"L": "company", "A": "company", "P": "person"}
    r = analyze_range([Stake("A", "L", 0.2, 0.6), Stake("P", "A", 0.5, 1.0)], "L", types)
    assert r.probabilities["P"] == pytest.approx((0.10, 0.60))
    assert r.anonymity_set_size == (1, 1)


def test_unstated_share_is_full_range():
    r = analyze_range([Stake("P", "L")], "L", {"L": "company", "P": "person"})
    assert r.probabilities["P"] == pytest.approx((0.0, 1.0))
    assert r.anonymity_set_size == (0, 1)


def test_publicly_traded_remainder_is_public_shareholders():
    types = {"L": "company", "T": "company", "P": "person"}
    stakes = [exact("T", "L", 1.0), exact("P", "T", 0.4)]
    r = analyze(stakes, "L", types, publicly_traded={"T"})
    assert r.probabilities[public_shareholders("T")] == pytest.approx(0.6)
    assert r.public_share == pytest.approx(0.6)
    assert r.unknown_share == pytest.approx(0.0)
    assert r.anonymity_set_size == 1
    assert r.entropy_known_bits == pytest.approx(0.0)


def test_disagreeing_sources_become_a_range_keeping_all_sources():
    merged = combine_statements(
        [exact("P", "L", 0.84, rel_ids=("r1",)), exact("P", "L", 0.80, rel_ids=("r2",))]
    )
    assert len(merged) == 1
    assert (merged[0].share_min, merged[0].share_max) == (0.80, 0.84)
    assert set(merged[0].rel_ids) == {"r1", "r2"}
    assert any("disagree on share" in n for n in merged[0].notes)


def test_confidence_disagreement_uses_highest_and_is_reported():
    stakes = [exact("P", "L", 0.5, confidence=1.0), exact("P", "L", 0.5, confidence=0.6)]
    r = analyze(stakes, "L", {"L": "company", "P": "person"})
    assert r.probabilities["P"] == pytest.approx(0.5)
    assert any("disagree on confidence" in d for d in r.discrepancies)


def test_inferred_link_confidence_leaks_to_unknown():
    r = analyze([exact("P", "L", 0.5, confidence=0.6)], "L", {"L": "company", "P": "person"})
    assert r.probabilities["P"] == pytest.approx(0.30)
    assert r.unknown_share == pytest.approx(0.70)


def test_company_with_no_recorded_owners_is_fully_unknown():
    r = analyze([exact("A", "L", 1.0)], "L", {"L": "company", "A": "company"})
    assert r.probabilities == pytest.approx({unknown_owner("A"): 1.0})
    assert r.anonymity_set_size == 0
    assert r.entropy_known_bits is None


def test_overallocated_shares_are_scaled_and_flagged():
    types = {"L": "company", "P": "person", "Q": "person"}
    r = analyze([exact("P", "L", 0.8), exact("Q", "L", 0.4)], "L", types)
    assert r.overallocated == ["L"]
    assert r.probabilities["P"] == pytest.approx(2 / 3)
    assert r.probabilities["Q"] == pytest.approx(1 / 3)


def test_cross_holding_loop_with_outside_owner():
    # A: 50% B, 50% P. B: 50% A, 50% unaccounted. P(P) = 0.5 / 0.75 = 2/3.
    types = {"A": "company", "B": "company", "P": "person"}
    stakes = [exact("B", "A", 0.5), exact("P", "A", 0.5), exact("A", "B", 0.5)]
    r = analyze(stakes, "A", types)
    assert r.probabilities["P"] == pytest.approx(2 / 3)
    assert r.probabilities[unknown_owner("B")] == pytest.approx(1 / 3)


def test_closed_loop_raises():
    types = {"A": "company", "B": "company"}
    with pytest.raises(ClosedOwnershipLoopError):
        analyze([exact("B", "A", 1.0), exact("A", "B", 1.0)], "A", types)


def test_start_is_a_person():
    r = analyze([], "P", {"P": "person"})
    assert r.probabilities == {"P": 1.0}
    assert r.anonymity_set_size == 1


def test_control_graph_is_separate_and_unweighted():
    stakes = [
        exact("A", "L", 1.0),
        exact("P", "A", 1.0),
        Stake("X", "A", graph="control"),  # board seat, no equity
        Stake("P", "A", graph="control"),
    ]
    # Control links anywhere along L's ownership chain count: A is L's owner, so X and P
    # control L's chain at 2 hops.
    assert control_reach(stakes, "L") == {"X": 2, "P": 2}
    assert control_reach(stakes, "A") == {"X": 1, "P": 1}
    assert control_without_equity(stakes, "A") == {"X": 1}
    assert control_without_equity(stakes, "L") == {"X": 2}
    r = analyze(stakes, "L", {"L": "company", "A": "company", "P": "person", "X": "person"})
    assert "X" not in r.probabilities


def test_equity_held_elsewhere_doesnt_hide_control_without_equity():
    # P3-shaped: D controls the licensee with no equity in it, but owns an unrelated company.
    stakes = [
        exact("S", "L", 1.0),
        Stake("D", "L", graph="control"),
        exact("D", "Other", 1.0),
    ]
    assert control_without_equity(stakes, "L") == {"D": 1}


# Nominees: P12-shaped structure. Takilant's registered director and shareholder is a
# proxy for Government Official A, and the same proxy is a listed shareholder of KolorIt.
P12_TYPES = {"Takilant": "company", "KolorIt": "company", "Proxy": "person", "GOA": "person"}


def test_without_nominee_link_the_walk_stops_at_the_proxy():
    r = analyze([exact("Proxy", "Takilant", 1.0)], "Takilant", P12_TYPES)
    assert r.probabilities == pytest.approx({"Proxy": 1.0})


def test_nominee_link_passes_ownership_to_hidden_party():
    stakes = [exact("Proxy", "Takilant", 1.0), exact("GOA", "Proxy", 1.0, graph="nominee")]
    r = analyze(stakes, "Takilant", P12_TYPES)
    assert r.probabilities == pytest.approx({"GOA": 1.0})
    assert r.hop_distribution == pytest.approx({2: 1.0})


def test_uncertain_nominee_link_leaves_the_rest_with_the_nominee():
    stakes = [
        exact("Proxy", "Takilant", 1.0),
        exact("GOA", "Proxy", 1.0, graph="nominee", confidence=0.7),
    ]
    r = analyze(stakes, "Takilant", P12_TYPES)
    assert r.probabilities["GOA"] == pytest.approx(0.7)
    assert r.probabilities["Proxy"] == pytest.approx(0.3)
    assert r.unknown_share == pytest.approx(0.0)
    assert r.anonymity_set_size == 2


def test_reused_proxy_reaches_same_hidden_party_from_two_companies():
    # KolorIt has two listed shareholders (split unstated); one is the proxy.
    stakes = [
        Stake("Proxy", "KolorIt"),
        Stake("Other", "KolorIt"),
        exact("GOA", "Proxy", 1.0, graph="nominee"),
    ]
    types = P12_TYPES | {"Other": "person"}
    r = analyze_range(stakes, "KolorIt", types)
    assert r.probabilities["GOA"] == pytest.approx((0.0, 1.0))
    assert "Proxy" not in r.probabilities or r.probabilities["Proxy"] == pytest.approx((0, 0))


def test_control_through_a_proxy_reaches_hidden_party():
    stakes = [
        Stake("Proxy", "Takilant", graph="control"),  # registered director
        exact("GOA", "Proxy", 1.0, graph="nominee"),
    ]
    assert control_reach(stakes, "Takilant") == {"Proxy": 1, "GOA": 2}
    # GOA's interest is held through the nominee, so it isn't "control without equity".
    assert control_without_equity(stakes, "Takilant") == {"Proxy": 1}


def test_controller_backed_by_its_owners_equity_isnt_flagged():
    # P3-shaped: GP has control but no partnership shares; the GP's owner holds them.
    stakes = [
        exact("LP", "L", 1.0),
        Stake("GP", "LP", graph="control"),
        exact("S", "GP", 1.0),
        exact("S", "LP", 1.0),
        Stake("D", "L", graph="control"),
    ]
    assert control_reach(stakes, "L") == {"GP": 2, "D": 1}
    assert control_without_equity(stakes, "L") == {"D": 1}


def test_control_high_up_the_chain_is_reached():
    # P7-shaped: the state controls the parent two levels up, with no equity share stated.
    stakes = [
        exact("CTCL", "CTA", 1.0),
        exact("CT", "CTCL", 0.7),
        Stake("SASAC", "CT", graph="control"),
    ]
    assert control_reach(stakes, "CTA") == {"SASAC": 3}
    assert control_without_equity(stakes, "CTA") == {"SASAC": 3}
