"""Tests for the hand-built ground-truth graphs and their loader."""

from datetime import date

import pytest

from teleownermap.ground_truth import (
    DEFAULT_DIR,
    analyze_case,
    date_bounds,
    load_cases,
    load_into_duckdb,
    load_links,
    select,
    valid_on,
)
from teleownermap.schema import connect

HEADER = (
    "row,owner,owner_type,owned,owned_type,graph,share_min,share_max,status,disclosed,"
    "start,end,source,note\n"
)


def case(name):
    return next(c for c in load_cases() if c.case == name)


def test_every_case_graph_loads_through_the_schema():
    con = connect()
    for c in load_cases():
        path = DEFAULT_DIR / f"{c.case}.csv"
        load_into_duckdb(con, path, load_links(path))
    n_links = sum(len(load_links(DEFAULT_DIR / f"{c.case}.csv")) for c in load_cases())
    assert con.execute("SELECT count(*) FROM relationships").fetchone()[0] == n_links


def test_partial_dates():
    assert date_bounds("2005") == (date(2005, 1, 1), date(2005, 12, 31), "year")
    assert date_bounds("2024-02") == (date(2024, 2, 1), date(2024, 2, 29), "month")
    assert date_bounds("2001-03-13") == (date(2001, 3, 13), date(2001, 3, 13), "day")


def test_snapshot_filter_is_inclusive_when_ambiguous(tmp_path):
    path = tmp_path / "X.csv"
    path.write_text(
        HEADER
        + "1,A,company,L,company,equity,1,1,stated,yes,2009,,s,\n"  # starts during 2009
        + "2,B,company,L,company,equity,1,1,stated,yes,1999,2009,s,\n"  # ends during 2009
        + "3,C,company,L,company,equity,1,1,stated,yes,2010,,s,\n"
    )
    links = load_links(path)
    assert [link.row for link in links if valid_on(link, date(2009, 6, 1))] == ["1", "2"]
    assert [link.row for link in links if valid_on(link, date(2010, 6, 1))] == ["1", "3"]


def test_disclosed_view_drops_hidden_links_and_snapshot_drops_later_ones():
    links = load_links(DEFAULT_DIR / "P4.csv")
    full = {link.row for link in select(links, "full", date(2015, 12, 31))}
    disclosed = {link.row for link in select(links, "disclosed", date(2015, 12, 31))}
    assert {"5a", "5b"} <= full - disclosed  # FCC's de facto control finding
    assert "6" not in full  # DISH's 2020 buyout is after the snapshot


@pytest.mark.parametrize(
    "line, message",
    [
        ("1,A,company,L,company,equity,1,1,rumored,yes,,,s,", "unknown status"),
        ("1,A,company,L,company,equity,0.6,0.4,stated,yes,,,s,", "share_min > share_max"),
        ("1,A,company,L,company,equity,1,1,stated,maybe,,,s,", "disclosed"),
        (
            "1,A,company,L,company,equity,1,1,stated,yes,,,s,\n2,A,person,L,company,equity,,,stated"
            ",yes,,,s,",
            "both company and person",
        ),
    ],
)
def test_malformed_rows_are_rejected(tmp_path, line, message):
    path = tmp_path / "X.csv"
    path.write_text(HEADER + line + "\n")
    with pytest.raises(ValueError, match=message):
        load_links(path)


def test_p3_hidden_controller_appears_only_in_full_view():
    results = {r.view: r for r in analyze_case(case("P3"), load_links(DEFAULT_DIR / "P3.csv"))}
    assert results["disclosed"].control_without_equity == {}
    assert results["full"].control_without_equity == {"Donald R. DePriest": 1}
    for r in results.values():  # equity is the same either way: all to Sandra
        assert r.ownership.probabilities == {"Sandra M. DePriest": pytest.approx((1.0, 1.0))}


def test_p8_look_through_share():
    (r, _) = analyze_case(case("P8"), load_links(DEFAULT_DIR / "P8.csv"))
    assert r.ownership.probabilities["SASAC"] == pytest.approx((0.521 * 0.98,) * 2)
