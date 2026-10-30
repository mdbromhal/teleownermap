"""Tests for GLEIF staging and promotion, on small hand-made golden-copy files."""

import csv
import io
import zipfile

import pytest

from teleownermap.ingest import gleif
from teleownermap.schema import connect

KEY = b"k" * 32
A = "Entity.LegalAddress"
H = "Entity.HeadquartersAddress"
LEI_COLUMNS = [
    "LEI", "Entity.LegalName", "Entity.LegalJurisdiction", "Entity.EntityCategory",
    "Entity.EntitySubCategory", "Entity.LegalForm.EntityLegalFormCode",
    "Entity.LegalForm.OtherLegalForm", "Entity.EntityStatus", "Entity.EntityCreationDate",
    "Registration.RegistrationStatus", "Registration.InitialRegistrationDate",
    "Registration.LastUpdateDate", "Registration.NextRenewalDate", "Registration.ManagingLOU",
    "Entity.OtherEntityNames.OtherEntityName.1",
    "Entity.SuccessorEntity.1.SuccessorLEI",
    *(f"{p}.{f}" for p in (A, H) for f in ("FirstAddressLine", "City", "Region", "Country",
                                          "PostalCode")),
]  # fmt: skip
RR_COLUMNS = [
    "Relationship.StartNode.NodeID", "Relationship.EndNode.NodeID",
    "Relationship.EndNode.NodeIDType", "Relationship.RelationshipType",
    "Relationship.RelationshipStatus", "Relationship.Period.1.periodType",
    "Relationship.Period.1.startDate", "Relationship.Period.1.endDate",
    "Relationship.Quantifiers.1.MeasurementMethod",
    "Relationship.Quantifiers.1.QuantifierAmount", "Relationship.Quantifiers.1.QuantifierUnits",
    "Relationship.Qualifiers.1.QualifierDimension", "Relationship.Qualifiers.1.QualifierCategory",
    "Registration.RegistrationStatus", "Registration.InitialRegistrationDate",
    "Registration.LastUpdateDate",
]  # fmt: skip
REPEX_COLUMNS = ["LEI", "Exception.Category", "Exception.Reason.1", "Exception.Reference.1"]


def write_csv_zip(path, columns, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(path.stem, buf.getvalue())
    return path


def company(lei, name, category="GENERAL", status="ISSUED", **extra):
    return {"LEI": lei, "Entity.LegalName": name, "Entity.EntityCategory": category,
            "Registration.RegistrationStatus": status,
            "Registration.InitialRegistrationDate": "2013-01-02T00:00:00Z",
            "Registration.LastUpdateDate": "2020-05-06T00:00:00Z",
            f"{A}.FirstAddressLine": "1 Chome", f"{A}.City": "Tokyo", f"{A}.Country": "JP",
            **extra}  # fmt: skip


def parent(child, par, rtype, pct=None, status="ACTIVE", reg="PUBLISHED"):
    row = {"Relationship.StartNode.NodeID": child, "Relationship.EndNode.NodeID": par,
           "Relationship.EndNode.NodeIDType": "LEI", "Relationship.RelationshipType": rtype,
           "Relationship.RelationshipStatus": status,
           "Relationship.Period.1.periodType": "RELATIONSHIP_PERIOD",
           "Relationship.Period.1.startDate": "2010-01-01T00:00:00Z",
           "Registration.RegistrationStatus": reg,
           "Registration.LastUpdateDate": "2019-01-01T00:00:00Z"}  # fmt: skip
    if pct is not None:
        row |= {"Relationship.Quantifiers.1.MeasurementMethod": "ACCOUNTING_CONSOLIDATION",
                "Relationship.Quantifiers.1.QuantifierAmount": str(pct),
                "Relationship.Quantifiers.1.QuantifierUnits": "PERCENTAGE"}  # fmt: skip
    return row


@pytest.fixture
def staged(tmp_path):
    files = {
        "lei2": write_csv_zip(tmp_path / "lei2.csv.zip", LEI_COLUMNS, [
            company("DCM", "DCM Capital USA (UK) Limited"),
            company("DOCOMO", "NTT DOCOMO, INC.", status="LAPSED"),
            company("NTT", "NIPPON TELEGRAPH AND TELEPHONE CORPORATION",
                    **{"Entity.OtherEntityNames.OtherEntityName.1": "NTT"}),
            company("SOLE", "Jane Trader", category="SOLE_PROPRIETOR",
                    **{f"{A}.FirstAddressLine": "9 Home Rd", f"{A}.City": "Hailey",
                       f"{A}.PostalCode": "83333", f"{A}.Country": "US"}),
            company("OTHER", "Unrelated Co"),
        ]),
        "rr": write_csv_zip(tmp_path / "rr.csv.zip", RR_COLUMNS, [
            parent("DCM", "DOCOMO", "IS_DIRECTLY_CONSOLIDATED_BY", pct=100),
            parent("DOCOMO", "NTT", "IS_DIRECTLY_CONSOLIDATED_BY"),
            parent("DCM", "NTT", "IS_ULTIMATELY_CONSOLIDATED_BY"),
        ]),
        "repex": write_csv_zip(tmp_path / "repex.csv.zip", REPEX_COLUMNS, [
            {"LEI": "NTT", "Exception.Category": "DIRECT_ACCOUNTING_CONSOLIDATION_PARENT",
             "Exception.Reason.1": "NON_CONSOLIDATING"},
        ]),
    }  # fmt: skip
    con = connect()
    sources = {}
    for name in files:
        con.execute(
            "INSERT INTO sources (source_id, source_type, retrieved_at, sha256) "
            "VALUES (?, 'gleif_golden_copy', now(), 'x')",
            [name],
        )
        sources[name] = name
    counts = gleif.load_staging(con, {n: (p, n) for n, p in files.items()}, KEY)
    return con, sources, counts


def test_staging_loads_everything(staged):
    con, _, counts = staged
    assert counts == {"gleif_entities": 5, "gleif_relationships": 3, "gleif_exceptions": 1}


def test_sole_proprietor_address_is_hashed_even_in_staging(staged):
    con, _, _ = staged
    row = con.execute(
        "SELECT legal_address, legal_city, legal_postal_code, legal_country, is_sensitive, "
        "legal_hmac_full IS NOT NULL FROM gleif_entities WHERE lei = 'SOLE'"
    ).fetchone()
    assert row == (None, None, None, "US", True, True)


def test_parent_chain_follows_every_level(staged):
    con, sources, _ = staged
    assert gleif.parent_chain(con, ["DCM"], sources["rr"]) == {"DCM", "DOCOMO", "NTT"}


def test_promote_maps_consolidation_to_control_and_equity(staged):
    con, sources, _ = staged
    assert gleif.promote(con, ["DCM"], sources) == {"DCM", "DOCOMO", "NTT"}
    rels = con.execute(
        "SELECT interested_party_id, subject_entity_id, interest_type, graph, share_min, labels "
        "FROM relationships ORDER BY subject_entity_id, interest_type"
    ).fetchall()
    by = {(r[0], r[1], r[2]): r for r in rels}
    direct = by[("lei:DOCOMO", "lei:DCM", "accounting_consolidation")]
    assert direct[3] == "control"
    equity = by[("lei:DOCOMO", "lei:DCM", "shareholding")]
    assert equity[3:5] == ("equity", 1.0)
    assert "gleif_consolidation_pct_not_defined_as_equity" in equity[5]
    # No percentage: control only, no equity link.
    assert ("lei:NTT", "lei:DOCOMO", "shareholding") not in by
    ultimate = by[("lei:NTT", "lei:DCM", "ultimate_accounting_consolidation")]
    assert ultimate[3] == "none" and "intermediate_layers_not_stated" in ultimate[5]


def test_promote_labels_lapsed_and_adds_exceptions_and_names(staged):
    con, sources, _ = staged
    gleif.promote(con, ["DCM"], sources)
    labels = dict(con.execute("SELECT entity_id, labels FROM entities").fetchall())
    assert any(lab.startswith("lei_lapsed:") for lab in labels["lei:DOCOMO"])
    attrs = con.execute(
        "SELECT name, value FROM attributes WHERE entity_id = 'lei:NTT' ORDER BY name"
    ).fetchall()
    assert ("gleif_reporting_exception",
            "DIRECT_ACCOUNTING_CONSOLIDATION_PARENT: NON_CONSOLIDATING") in attrs  # fmt: skip
    assert ("other_name_1", "NTT") in attrs
    assert "lei:OTHER" not in labels


def test_promote_twice_adds_nothing(staged):
    con, sources, _ = staged
    gleif.promote(con, ["DCM"], sources)
    n = con.execute("SELECT count(*) FROM records").fetchone()[0]
    gleif.promote(con, ["DCM", "DOCOMO"], sources)
    assert con.execute("SELECT count(*) FROM records").fetchone()[0] == n
