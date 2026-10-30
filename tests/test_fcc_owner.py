"""Tests for the FCC ownership-file parser, on a small hand-made owner.zip."""

import json
import zipfile

import pytest

from teleownermap.ingest import fcc_owner
from teleownermap.ingest.fcc_owner import COLUMNS, ParseReport, read_rows
from teleownermap.schema import connect

KEY = b"k" * 32
USI = "2572134"


def line(rtype, **values):
    cols = COLUMNS[rtype]
    fields = {"record_type": rtype, "form_num": "602", "filing_type": "C", "filing_status": "1",
              "unique_system_identifier": USI, **values}  # fmt: skip
    return "|".join(fields.get(c, "") for c in cols)


def holder(**values):
    base = {"file_num": "0002081616", "interest_direct": "N", "interest_indirect": "N",
            "interest_officer": "N", "interest_director": "N", "interest_key_mgmt": "N",
            "interest_mgmt_contract": "N", "interest_other": "N"}  # fmt: skip
    return line("D", **{**base, **values})


@pytest.fixture
def owner_zip(tmp_path):
    members = {
        "_O.dat": [
            line("O", frn_filer="0004122032", file_num="0002081616",
                 filer_name="AT&T Wireless Services, Inc.", date_receipt="08/18/2004",
                 certifier_fname="Douglas", certifier_lname="Brandon",
                 certifier_title="Vice President", contact_company="Example Law LLP",
                 contact_fname="Ann", contact_lname="Lawyer", contact_phone="2025550100",
                 contact_address="1 Main St", contact_city="Washington", contact_state="DC",
                 contact_zip_code="20036"),
        ],
        "_D.dat": [
            holder(entity_name="DCM Capital USA (UK) Limited", frn="0007737273",
                   interest_direct="Y", own_comm_stk="Y", own_comm_stk_vote_ind="V",
                   pct_interest="16.00"),
            holder(entity_name="Nippon Telegraph and Telephone Corporation", frn="0007737323",
                   interest_indirect="Y", pct_interest="16.00"),
            holder(entity_name="Zero Holder LLC", interest_direct="Y", pct_interest=".00"),
            holder(fname="Jack", lname="Levin", frn="0009070765", address="611 Valley Club Dr.",
                   city="Hailey", state="ID", zip_code="83333", country="United States",
                   interest_director="Y", interest_officer="Y", pct_interest=".00"),
            # A free-text field with a line break splits this record across two lines.
            holder(entity_name="Split Co", interest_other="Y",
                   interest_other_desc="See Exhibit 1\nfor details"),
        ],
        "_F.dat": [line("F", business_name="Cordova Wireless", frn="0001567692",
                        pct_interest="49.00")],
        "_H.dat": [line("H", business_name="Other License Co", frn="0001111111",
                        dih_frn="0007737273", pct_interest="100.00")],
        "_T.dat": [line("T", attachment_code="I",
                        attachment_desc="Ex. A: Description of Indirect Ownership Interests",
                        attachment_date="09/30/2002",
                        attachment_filename="./upload_files/1034901775")],
    }  # fmt: skip
    path = tmp_path / "owner.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, lines in members.items():
            zf.writestr(name, "\r\n".join(lines) + "\r\n")
    return path


@pytest.fixture
def con(owner_zip):
    con = connect()
    con.execute(
        "INSERT INTO sources (source_id, source_type, retrieved_at, sha256) "
        "VALUES ('s', 'fcc_uls_bulk', now(), 'x')"
    )
    fcc_owner.load(con, owner_zip, "s", KEY)
    return con


def rels(con, kind):
    return con.execute(
        "SELECT interested_party_id, subject_entity_id, graph, share_min, share_max, labels "
        "FROM relationships WHERE interest_type = ? ORDER BY 1",
        [kind],
    ).fetchall()


def test_records_split_across_lines_are_rejoined(owner_zip):
    report = ParseReport(rows={}, stitched=0, malformed=[])
    rows = list(read_rows(owner_zip, report))
    split = next(r for r in rows if r.fields.get("entity_name") == "Split Co")
    assert split.fields["interest_other_desc"] == "See Exhibit 1\nfor details"
    assert report.stitched == 1 and report.malformed == []
    assert report.rows["D"] == 5


def test_only_direct_holders_enter_the_equity_graph(con):
    filer = "frn:0004122032"
    [(owner, subject, graph, lo, hi, labels)] = [
        r for r in rels(con, "shareholding") if r[0] == "frn:0007737273"
    ]
    assert (owner, subject, graph, lo, hi) == ("frn:0007737273", filer, "equity", 0.16, 0.16)
    assert "common_stock:V" in labels
    [indirect] = rels(con, "named_indirect_holder")
    assert indirect[:5] == ("frn:0007737323", filer, "none", 0.0, 0.16)
    assert "upper_bound" in indirect[5]


def test_direct_holder_at_zero_percent_is_unstated(con):
    [zero] = [r for r in rels(con, "shareholding") if r[0] != "frn:0007737273"]
    assert zero[3:5] == (None, None)
    assert "reported_0.00" in zero[5]


def test_officers_and_directors_are_control_links(con):
    assert [r[:3] for r in rels(con, "officer")] == [
        ("frn:0009070765", "frn:0004122032", "control")
    ]
    assert [r[:3] for r in rels(con, "board_seat")] == [
        ("frn:0009070765", "frn:0004122032", "control")
    ]


def test_person_address_is_hashed_and_removed_from_raw(con):
    rows = con.execute(
        "SELECT name, value, is_sensitive, hmac_full IS NOT NULL FROM attributes "
        "WHERE entity_id = 'frn:0009070765' ORDER BY name"
    ).fetchall()
    assert ("address", None, True, True) in rows
    assert ("address_state", "ID", False, False) in rows
    raw = json.loads(
        con.execute(
            "SELECT raw FROM records r JOIN entity_records er USING (record_id) "
            "WHERE er.entity_id = 'frn:0009070765'"
        ).fetchone()[0]
    )
    assert raw["address"] is None and raw["city"] is None and raw["zip_code"] is None
    assert raw["redacted"] == ["address", "city", "zip_code"]
    assert "Hailey" not in json.dumps(raw) and "Valley Club" not in json.dumps(raw)


def test_company_contact_address_is_shown(con):
    [(value,)] = con.execute(
        "SELECT value FROM attributes a JOIN relationships r "
        "ON r.interested_party_id = a.entity_id "
        "WHERE r.interest_type = 'legal_counsel' AND a.name = 'address'"
    ).fetchall()
    assert value == "1 Main St, Washington, DC, 20036"


def test_holdings_are_upper_bound_links_outside_the_metrics(con):
    holdings = rels(con, "named_holding")
    assert [(r[0], r[1], r[2], r[4]) for r in holdings] == [
        ("frn:0004122032", "frn:0001567692", "none", 0.49),
        ("frn:0007737273", "frn:0001111111", "none", 1.0),
    ]


def test_certifier_and_contact_are_filing_authors(con):
    titles = con.execute(
        "SELECT title_as_written FROM relationships WHERE interest_type = 'filing_author' "
        "ORDER BY 1"
    ).fetchall()
    assert titles == [("Contact",), ("Vice President",)]


def test_filer_self_description_wins_and_code_b_is_government(tmp_path):
    path = tmp_path / "owner.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("_O.dat", line("O", frn_filer="0000000001", filer_name="Twin Valley Inc."))
        zf.writestr(
            "_D.dat",
            "\n".join(
                [
                    # The filer's own FRN reused for an officer: a possible ID error.
                    holder(fname="A", lname="Foster", frn="0000000001", interest_officer="Y"),
                    holder(
                        entity_name="City of Bastrop",
                        frn="0000000002",
                        type_entity="b",
                        interest_direct="Y",
                        pct_interest="100.00",
                    ),  # fmt: skip
                ]
            ),
        )
    con = connect()
    con.execute(
        "INSERT INTO sources (source_id, source_type, retrieved_at, sha256) "
        "VALUES ('s', 'fcc_uls_bulk', now(), 'x')"
    )
    fcc_owner.load(con, path, "s", KEY)
    types = dict(con.execute("SELECT entity_id, entity_type FROM entities").fetchall())
    assert types["frn:0000000001"] == "company"
    assert types["frn:0000000002"] == "government"
    flags = con.execute(
        "SELECT DISTINCT conflict_flag FROM identifiers WHERE entity_id = 'frn:0000000001'"
    ).fetchall()
    assert flags == [(True,)]


def test_filing_event_and_reload_is_skipped(con, owner_zip):
    assert con.execute("SELECT event_type, date FROM events").fetchall()[0][0] == "form_602_filing"
    n = con.execute("SELECT count(*) FROM records").fetchone()[0]
    fcc_owner.load(con, owner_zip, "s", KEY)
    assert con.execute("SELECT count(*) FROM records").fetchone()[0] == n
