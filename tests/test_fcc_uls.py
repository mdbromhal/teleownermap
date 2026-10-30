"""Tests for the FCC ULS license/application parser, on small hand-made files."""

import json
import zipfile

import pytest

from teleownermap.ingest import fcc_uls
from teleownermap.ingest.uls_columns import COLUMNS
from teleownermap.schema import connect

KEY = b"k" * 32


def line(rtype, usi, **values):
    fields = {"record_type": rtype, "unique_system_identifier": usi, **values}
    return "|".join(fields.get(c, "") for c in COLUMNS[rtype])


def write_zip(path, members):
    with zipfile.ZipFile(path, "w") as zf:
        for name, lines in members.items():
            zf.writestr(name, "\r\n".join(lines) + "\r\n")
    return path


def load(path, source_id="s"):
    con = connect()
    con.execute(
        "INSERT INTO sources (source_id, source_type, retrieved_at, sha256) "
        "VALUES (?, 'fcc_uls_bulk', now(), 'x')",
        [source_id],
    )
    report = fcc_uls.load(con, path, source_id, KEY)
    return con, report


@pytest.fixture
def licenses(tmp_path):
    path = write_zip(
        tmp_path / "l_cell.zip",
        {
            "HD.dat": [
                line("HD", "1", call_sign="KNKA123", license_status="A", radio_service_code="CL",
                     grant_date="01/02/2015", expired_date="10/01/2025", alien_control="Y",
                     female="Y", white="Y", certifier_first_name="Pat",
                     certifier_last_name="Signer", certifier_title="CEO"),
                line("HD", "2", call_sign="WQAB456", license_status="A", radio_service_code="CL"),
            ],
            "MK.dat": [line("MK", "1", market_code="CMA001", market_name="New York")],
            "EN.dat": [
                line("EN", "1", entity_type="L", entity_name="Example Cellular LLC",
                     fcc_registration_number_frn="0000000100", applicant_type_code="L",
                     street_address="1 Main St", city="Austin", state="TX", zip_code="78701"),
                line("EN", "1", entity_type="CL", entity_name="Law Firm LLP", phone="2025550100"),
                line("EN", "1", entity_type="O", entity_name="Example Cellular LLC"),
                line("EN", "2", entity_type="L", first_name="Jane", last_name="Doe",
                     fcc_registration_number_frn="0000000200", applicant_type_code="I",
                     street_address="9 Home Rd", city="Hailey", state="ID", zip_code="83333",
                     phone="2085550199", email="jane@example.com"),
            ],
            "LO.dat": [
                line("LO", "1", location_address="Tower Rd", location_city="Austin",
                     location_state="TX", latitude_degrees="30", latitude_minutes="16",
                     latitude_seconds="12.0", latitude_direction="N", longitude_degrees="97",
                     longitude_minutes="44", longitude_seconds="24.0", longitude_direction="W",
                     tower_registration_number="1234567"),
                line("LO", "2", location_address="9 Home Rd", location_city="Hailey",
                     location_state="ID", latitude_degrees="43", latitude_minutes="31",
                     latitude_seconds="0.0", latitude_direction="N", longitude_degrees="114",
                     longitude_minutes="19", longitude_seconds="0.0", longitude_direction="W"),
            ],
            "HS.dat": [line("HS", "1", call_sign="KNKA123", log_date="03/04/2016",
                            code="LITRAN")],
        },
    )  # fmt: skip
    return load(path)[0]


def test_license_and_licensee(licenses):
    lic = licenses.execute(
        "SELECT call_sign, market, status, grant_date::VARCHAR FROM licenses ORDER BY 1"
    ).fetchall()
    assert lic[0] == ("KNKA123", "CMA001 New York", "A", "2015-01-02")
    holders = licenses.execute(
        "SELECT r.interested_party_id, e.entity_type, e.labels FROM relationships r "
        "JOIN entities e ON e.entity_id = r.interested_party_id "
        "WHERE interest_type = 'license_holder' ORDER BY 1"
    ).fetchall()
    assert holders == [
        ("frn:0000000100", "company", ["fcc_applicant_type:Limited Liability Company"]),
        ("frn:0000000200", "person", None),
    ]


def test_demographics_are_never_stored(licenses):
    raws = [json.loads(r) for (r,) in licenses.execute("SELECT raw FROM records").fetchall()]
    for raw in raws:
        assert not {"female", "white", "hispanic"} & raw.keys()


def test_foreign_ownership_answer_is_an_attribute(licenses):
    assert licenses.execute(
        "SELECT value FROM attributes WHERE entity_id = 'frn:0000000100' "
        "AND name = 'fcc_answer:alien_control'"
    ).fetchall() == [("Y",)]


def test_individual_licensee_contact_details_and_site_are_hashed(licenses):
    rows = licenses.execute(
        "SELECT name, value, is_sensitive, hmac_full IS NOT NULL FROM attributes "
        "WHERE entity_id = 'frn:0000000200' AND name IN ('address', 'phone', 'email') "
        "ORDER BY name"
    ).fetchall()
    assert rows == [("address", None, True, True), ("email", None, True, True),
                    ("phone", None, True, True)]  # fmt: skip
    sites = licenses.execute(
        "SELECT address, latitude, is_sensitive, hmac_coords IS NOT NULL, tower_registration "
        "FROM license_sites ORDER BY is_sensitive"
    ).fetchall()
    assert sites[0][0] == "Tower Rd" and sites[0][1] == pytest.approx(30.27)
    assert sites[0][4] == "1234567"
    assert sites[1][:4] == (None, None, True, True)
    dump = json.dumps([r for (r,) in licenses.execute("SELECT raw FROM records").fetchall()])
    assert "Home Rd" not in dump and "Hailey" not in dump and "2085550199" not in dump


def test_company_contact_and_history(licenses):
    assert licenses.execute(
        "SELECT a.value FROM relationships r JOIN attributes a "
        "ON a.entity_id = r.interested_party_id AND a.name = 'phone' "
        "WHERE r.interest_type = 'license_contact'"
    ).fetchall() == [("2025550100",)]
    events = dict(licenses.execute("SELECT event_type, date::VARCHAR FROM events").fetchall())
    assert events["license_transferred"] == "2016-03-04"
    assert events["license_grant"] == "2015-01-02"


def test_owner_rows_are_records_only(licenses):
    n = licenses.execute(
        "SELECT count(*) FROM entities e JOIN attributes a USING (entity_id) "
        "WHERE a.value = 'Example Cellular LLC'"
    ).fetchone()[0]
    assert n == 1


def test_transfer_and_assignment_parties(tmp_path):
    path = write_zip(
        tmp_path / "a_aatc.zip",
        {
            "HD.dat": [line("HD", "10"), line("HD", "20")],
            "AD.dat": [
                line("AD", "10", application_purpose="TC", application_status="G",
                     receipt_date="05/01/2008"),
                line("AD", "20", application_purpose="AA", application_status="G",
                     receipt_date="06/01/2009"),
            ],
            "EN.dat": [
                line("EN", "10", entity_type="L", entity_name="Licensee Inc",
                     fcc_registration_number_frn="0000000001", applicant_type_code="C"),
                line("EN", "10", entity_type="R", entity_name="Old Parent",
                     fcc_registration_number_frn="0000000002"),
                line("EN", "10", entity_type="E", entity_name="New Parent",
                     fcc_registration_number_frn="0000000003"),
                line("EN", "20", entity_type="R", entity_name="Seller LLC",
                     fcc_registration_number_frn="0000000004"),
                line("EN", "20", entity_type="E", entity_name="Buyer LLC",
                     fcc_registration_number_frn="0000000005"),
            ],
            "TA.dat": [line("TA", "10", pro_forma="N", consent_date="07/01/2008",
                            consummation_date="08/01/2008", assignor_transferor_white="Y")],
        },
    )  # fmt: skip
    con, _ = load(path)
    rels = con.execute(
        "SELECT interest_type, interested_party_id, subject_entity_id, "
        "effective_date::VARCHAR, list_contains(labels, 'pro_forma:N') "
        "FROM relationships ORDER BY 1"
    ).fetchall()
    assert rels == [
        ("assignor", "frn:0000000004", "frn:0000000005", None, False),
        ("transferee", "frn:0000000003", "frn:0000000001", "2008-08-01", True),
        ("transferor", "frn:0000000002", "frn:0000000001", "2008-08-01", True),
    ]
    events = set(con.execute("SELECT event_type, entity_id FROM events").fetchall())
    assert ("transfer_consummation", "frn:0000000001") in events
    assert ("assignment_application", "frn:0000000005") in events
    raws = " ".join(r for (r,) in con.execute("SELECT raw FROM records").fetchall())
    assert "assignor_transferor_white" not in raws


def test_records_broken_across_lines_are_rejoined(tmp_path):
    path = write_zip(
        tmp_path / "l_cell.zip",
        {"HD.dat": [line("HD", "1", call_sign="K1", license_status="A")],
         "EN.dat": [line("EN", "1", entity_type="L", entity_name="Two\nLines Inc")]},
    )  # fmt: skip
    con, report = load(path)
    assert report.malformed == []
    assert con.execute("SELECT value FROM attributes WHERE name = 'name'").fetchone() == (
        "Two\nLines Inc",
    )
