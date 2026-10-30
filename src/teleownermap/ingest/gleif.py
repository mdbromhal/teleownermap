"""GLEIF golden copy (LEI records, relationship records, reporting exceptions).
Modeling choices are in docs/decisions.md.

`load_staging` copies the whole golden copy into the `gleif_*` staging tables, so any
company is searchable. `promote` turns chosen LEIs and their full parent chains into
entities, attributes and relationships, for companies connected to an FCC entity:
- "directly consolidated by" is a control link, plus an equity link only when GLEIF gives a
  percentage (labeled: GLEIF doesn't define it as equity);
- "ultimately consolidated by" skips the middle layers, so it is kept outside both graphs
  as a cross-check;
- "fund-managed by" is control; sub-fund, feeder and branch links are shown only;
- reporting exceptions are stated attributes shown beside the company's unaccounted share;
- links and entities from lapsed registrations are kept and labeled.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

import duckdb

from teleownermap.ingest._bulk import BATCH_ROWS, TableSink
from teleownermap.ingest.hashing import hash_address

PARSER_VERSION = "gleif_csv/1"
N_REPEATS = 5  # GLEIF's CSV repeats names, successors, events and periods up to 5 times

CATEGORY_TYPES = {
    "GENERAL": ("company", None),
    "FUND": ("company", "fund"),
    "BRANCH": ("company", "branch"),
    "SOLE_PROPRIETOR": ("person", None),
    "RESIDENT_GOVERNMENT_ENTITY": ("government", None),
    "INTERNATIONAL_ORGANIZATION": ("government", None),
}
# (interest_type, graph) for each GLEIF relationship type; parent is the interested party.
RELATIONSHIP_TYPES = {
    "IS_DIRECTLY_CONSOLIDATED_BY": ("accounting_consolidation", "control"),
    "IS_ULTIMATELY_CONSOLIDATED_BY": ("ultimate_accounting_consolidation", "none"),
    "IS_FUND-MANAGED_BY": ("fund_manager", "control"),
    "IS_SUBFUND_OF": ("umbrella_fund", "none"),
    "IS_FEEDER_TO": ("master_fund", "none"),
    "IS_INTERNATIONAL_BRANCH_OF": ("head_office", "none"),
}


def _rows(path: Path) -> Iterator[tuple[int, dict[str, str]]]:
    with zipfile.ZipFile(path) as zf:
        member = next(n for n in zf.namelist() if n.endswith(".csv"))
        with zf.open(member) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
            yield from enumerate(reader, start=2)


def _date(value: str | None) -> str | None:
    return value[:10] if value else None


def _address(row: dict, prefix: str) -> str | None:
    parts = [
        row.get(f"{prefix}.FirstAddressLine"),
        row.get(f"{prefix}.AddressNumber"),
        row.get(f"{prefix}.AddressNumberWithinBuilding"),
        row.get(f"{prefix}.MailRouting"),
    ]
    parts += [row.get(f"{prefix}.AdditionalAddressLine.{i}") for i in (1, 2, 3)]
    return ", ".join(p for p in parts if p) or None  # fmt: skip


def _repeated(row: dict, pattern: str) -> list[str]:
    return [v for i in range(1, N_REPEATS + 1) if (v := row.get(pattern.format(i)))]


def _events(row: dict) -> list[dict]:
    events = []
    for i in range(1, N_REPEATS + 1):
        p = f"Entity.LegalEntityEvents.LegalEntityEvent.{i}"
        if row.get(f"{p}.LegalEntityEventType"):
            events.append({
                "type": row[f"{p}.LegalEntityEventType"],
                "effective": _date(row[f"{p}.LegalEntityEventEffectiveDate"]),
                "recorded": _date(row[f"{p}.LegalEntityEventRecordedDate"]),
                "status": row[f"{p}.event_status"],
            })  # fmt: skip
    return events


def _periods(row: dict) -> list[dict]:
    periods = []
    for i in range(1, N_REPEATS + 1):
        p = f"Relationship.Period.{i}"
        if row.get(f"{p}.periodType"):
            periods.append({"type": row[f"{p}.periodType"], "start": _date(row[f"{p}.startDate"]),
                            "end": _date(row[f"{p}.endDate"])})  # fmt: skip
    return periods


def entity_row(source_id: str, line: int, row: dict, key: bytes) -> dict:
    person = row["Entity.EntityCategory"] == "SOLE_PROPRIETOR"
    out = {
        "source_id": source_id,
        "lei": row["LEI"],
        "line": line,
        "legal_name": row["Entity.LegalName"] or None,
        "other_names": _repeated(row, "Entity.OtherEntityNames.OtherEntityName.{}")
        + _repeated(row, "Entity.TransliteratedOtherEntityNames.TransliteratedOtherEntityName.{}"),
        "jurisdiction": row["Entity.LegalJurisdiction"] or None,
        "category": row["Entity.EntityCategory"] or None,
        "subcategory": row["Entity.EntitySubCategory"] or None,
        "legal_form_code": row["Entity.LegalForm.EntityLegalFormCode"] or None,
        "other_legal_form": row["Entity.LegalForm.OtherLegalForm"] or None,
        "entity_status": row["Entity.EntityStatus"] or None,
        "creation_date": _date(row["Entity.EntityCreationDate"]),
        "registration_status": row["Registration.RegistrationStatus"] or None,
        "initial_registration_date": _date(row["Registration.InitialRegistrationDate"]),
        "last_update_date": _date(row["Registration.LastUpdateDate"]),
        "next_renewal_date": _date(row["Registration.NextRenewalDate"]),
        "managing_lou": row["Registration.ManagingLOU"] or None,
        "successor_leis": _repeated(row, "Entity.SuccessorEntity.{}.SuccessorLEI"),
        "legal_entity_events": _events(row) or None,
        "is_sensitive": person,
    }
    for prefix, short in (("Entity.LegalAddress", "legal"), ("Entity.HeadquartersAddress", "hq")):
        street, city = _address(row, prefix), row[f"{prefix}.City"] or None
        postal, country = row[f"{prefix}.PostalCode"] or None, row[f"{prefix}.Country"] or None
        region = row[f"{prefix}.Region"]
        h = hash_address(key, street=street, street2=None, city=city, state=region,
                         zip_code=postal, country=country)  # fmt: skip
        out |= {
            f"{short}_address": None if person else street,
            f"{short}_city": None if person else city,
            f"{short}_postal_code": None if person else postal,
            f"{short}_region": row[f"{prefix}.Region"] or None,
            f"{short}_country": country,
            f"{short}_hmac_full": h.full,
            f"{short}_hmac_zip": h.zip,
            f"{short}_hmac_city": h.city,
        }
    return out


def relationship_row(source_id: str, line: int, row: dict) -> dict:
    periods = _periods(row)
    amount = row.get("Relationship.Quantifiers.1.QuantifierAmount")
    units = row.get("Relationship.Quantifiers.1.QuantifierUnits")
    return {
        "source_id": source_id,
        "line": line,
        "child_lei": row["Relationship.StartNode.NodeID"],
        "parent_id": row["Relationship.EndNode.NodeID"],
        "parent_id_type": row["Relationship.EndNode.NodeIDType"] or None,
        "relationship_type": row["Relationship.RelationshipType"],
        "relationship_status": row["Relationship.RelationshipStatus"] or None,
        "periods": periods or None,
        "measurement_method": row["Relationship.Quantifiers.1.MeasurementMethod"] or None,
        "percentage": float(amount) if amount and units == "PERCENTAGE" else None,
        "accounting_standard": next(
            (
                row[f"Relationship.Qualifiers.{i}.QualifierCategory"]
                for i in range(1, N_REPEATS + 1)
                if row.get(f"Relationship.Qualifiers.{i}.QualifierDimension")
                == "ACCOUNTING_STANDARD"
            ),
            None,
        ),  # fmt: skip
        "registration_status": row["Registration.RegistrationStatus"] or None,
        "initial_registration_date": _date(row["Registration.InitialRegistrationDate"]),
        "last_update_date": _date(row["Registration.LastUpdateDate"]),
    }


def exception_row(source_id: str, line: int, row: dict) -> dict:
    return {
        "source_id": source_id,
        "line": line,
        "lei": row["LEI"],
        "category": row["Exception.Category"],
        "reasons": _repeated(row, "Exception.Reason.{}"),
        "refs": _repeated(row, "Exception.Reference.{}") or None,
    }


def load_staging(
    con: duckdb.DuckDBPyConnection,
    files: dict[str, tuple[Path, str]],
    key: bytes,
    *,
    batch_rows: int = BATCH_ROWS,
) -> dict[str, int]:
    """Load the golden copy. `files` maps "lei2", "rr", "repex" to (zip path, source_id).
    A source already staged is skipped."""
    tables = {"lei2": "gleif_entities", "rr": "gleif_relationships", "repex": "gleif_exceptions"}
    builders = {"lei2": lambda s, n, r: entity_row(s, n, r, key), "rr": relationship_row,
                "repex": exception_row}  # fmt: skip
    counts = {}
    for name, (path, source_id) in files.items():
        table = tables[name]
        done = con.execute(f"SELECT count(*) FROM {table} WHERE source_id = ?", [source_id])
        if done.fetchone()[0]:
            continue
        sink = TableSink((table,), batch_rows)
        try:
            for line, row in _rows(path):
                sink.write(table, builders[name](source_id, line, row))
            sink.insert(con)
        finally:
            sink.close()
        counts[table] = sink.counts.get(table, 0)
    return counts


# -- promotion --------------------------------------------------------------------------


def parent_chain(con: duckdb.DuckDBPyConnection, seeds: Iterable[str], rr_source: str) -> set[str]:
    """The seed LEIs plus every LEI above them (any relationship type, any depth)."""
    seeds = sorted(set(seeds))
    if not seeds:
        return set()
    found = con.execute(
        """
        WITH RECURSIVE up(lei) AS (
            SELECT unnest(?::VARCHAR[])
            UNION
            SELECT r.parent_id FROM gleif_relationships r JOIN up ON r.child_lei = up.lei
            WHERE r.source_id = ? AND r.parent_id_type = 'LEI'
        )
        SELECT lei FROM up
        """,
        [seeds, rr_source],
    ).fetchall()
    return {lei for (lei,) in found}


def promote(
    con: duckdb.DuckDBPyConnection,
    seeds: Iterable[str],
    sources: dict[str, str],
) -> set[str]:
    """Create entities etc. for `seeds` and their parent chains. `sources` maps "lei2",
    "rr", "repex" to staged source_ids. Returns the promoted LEIs; already-promoted rows
    are skipped."""
    leis = parent_chain(con, seeds, sources["rr"])
    if not leis:
        return leis
    sink = TableSink(("records", "entities", "entity_records", "identifiers", "attributes",
                      "relationships", "events"))  # fmt: skip
    existing = {
        r for (r,) in con.execute(
            "SELECT record_id FROM records WHERE source_id IN (?, ?, ?)",
            [sources["lei2"], sources["rr"], sources["repex"]],
        ).fetchall()
    }  # fmt: skip
    cols = [c for (c,) in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
        ["gleif_entities"]).fetchall()]  # fmt: skip
    ents = con.execute(
        "SELECT * FROM gleif_entities WHERE source_id = ? AND list_contains(?, lei)",
        [sources["lei2"], sorted(leis)],
    ).fetchall()
    for values in ents:
        _promote_entity(sink, dict(zip(cols, values, strict=True)), existing)
    rr_cols = [c for (c,) in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
        ["gleif_relationships"]).fetchall()]  # fmt: skip
    staged = {row["lei"] for row in (dict(zip(cols, v, strict=True)) for v in ents)}
    rels = con.execute(
        "SELECT * FROM gleif_relationships WHERE source_id = ? AND parent_id_type = 'LEI' "
        "AND list_contains(?, child_lei)",
        [sources["rr"], sorted(staged)],
    ).fetchall()
    for values in rels:
        r = dict(zip(rr_cols, values, strict=True))
        if r["parent_id"] in staged:
            _promote_relationship(sink, r, existing)
    for line, lei, category, reasons in con.execute(
        "SELECT line, lei, category, reasons FROM gleif_exceptions "
        "WHERE source_id = ? AND list_contains(?, lei)",
        [sources["repex"], sorted(staged)],
    ).fetchall():
        rid = f"{sources['repex']}:{line}"
        if rid in existing:
            continue
        _record(sink, rid, sources["repex"], f"repex CSV line {line}",
                {"lei": lei, "category": category, "reasons": reasons})  # fmt: skip
        sink.write("attributes", {"attribute_id": f"{rid}/exception", "entity_id": f"lei:{lei}",
                                  "name": "gleif_reporting_exception",
                                  "value": f"{category}: {', '.join(reasons)}",
                                  "record_id": rid, "is_sensitive": False})  # fmt: skip
    try:
        sink.insert(con, or_ignore=("entities",))
    finally:
        sink.close()
    return staged


def _record(sink: TableSink, rid: str, source_id: str, locator: str, raw: dict) -> None:
    sink.write("records", {"record_id": rid, "source_id": source_id, "locator": locator,
                           "raw": raw, "parser_version": PARSER_VERSION})  # fmt: skip


def _promote_entity(sink: TableSink, e: dict, existing: set[str]) -> None:
    rid = f"{e['source_id']}:{e['line']}"
    if rid in existing:
        return
    raw = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in e.items()}
    if isinstance(raw.get("legal_entity_events"), str):
        raw["legal_entity_events"] = json.loads(raw["legal_entity_events"])
    _record(sink, rid, e["source_id"], f"lei2 CSV line {e['line']}", raw)
    etype, label = CATEGORY_TYPES.get(e["category"], ("unclassified", None))
    labels = [f"gleif_category:{e['category']}"] + ([label] if label else [])
    if e["registration_status"] == "LAPSED":
        labels.append(f"lei_lapsed:last_updated_{e['last_update_date']}")
    entity_id = f"lei:{e['lei']}"
    sink.write("entities", {"entity_id": entity_id, "entity_type": etype, "labels": labels})
    sink.write("entity_records", {"entity_id": entity_id, "record_id": rid})
    sink.write("identifiers", {"entity_id": entity_id, "scheme": "LEI", "value": e["lei"],
                               "record_id": rid, "conflict_flag": False})  # fmt: skip

    def attr(name, value, **extra):
        if value is None and not extra.get("is_sensitive"):
            return
        sink.write("attributes", {"attribute_id": f"{rid}/{name}", "entity_id": entity_id,
                                  "name": name, "value": value, "record_id": rid,
                                  "is_sensitive": False, **extra})  # fmt: skip

    attr("name", e["legal_name"])
    for i, other in enumerate(e["other_names"] or []):
        attr(f"other_name_{i + 1}", other)
    person = e["is_sensitive"]
    for short in ("legal", "hq"):
        plain = ", ".join(p for p in (e[f"{short}_address"], e[f"{short}_city"],
                                      e[f"{short}_region"], e[f"{short}_postal_code"],
                                      e[f"{short}_country"]) if p)  # fmt: skip
        if plain or e[f"{short}_hmac_city"]:
            attr(f"{short}_address", None if person else plain, is_sensitive=person,
                 hmac_full=e[f"{short}_hmac_full"], hmac_zip=e[f"{short}_hmac_zip"],
                 hmac_city=e[f"{short}_hmac_city"])  # fmt: skip
    attr("jurisdiction", e["jurisdiction"])
    attr("legal_form", e["legal_form_code"] or e["other_legal_form"])
    attr("entity_status", e["entity_status"])
    attr("lei_registration_status", e["registration_status"])
    for kind, when in (("lei_registration", e["initial_registration_date"]),
                       ("gleif_entity_creation", e["creation_date"])):  # fmt: skip
        if when:
            sink.write("events", {"event_id": f"{rid}/{kind}", "entity_id": entity_id,
                                  "event_type": kind, "date": when, "precision": "day",
                                  "record_id": rid})  # fmt: skip


def _promote_relationship(sink: TableSink, r: dict, existing: set[str]) -> None:
    rid = f"{r['source_id']}:{r['line']}"
    if rid in existing or r["relationship_type"] not in RELATIONSHIP_TYPES:
        return
    raw = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()}
    if isinstance(raw.get("periods"), str):
        raw["periods"] = json.loads(raw["periods"])
    _record(sink, rid, r["source_id"], f"rr CSV line {r['line']}", raw)
    interest, graph = RELATIONSHIP_TYPES[r["relationship_type"]]
    periods = raw["periods"] or []
    period = next((p for p in periods if p["type"] == "RELATIONSHIP_PERIOD"), None)
    labels = [f"gleif_{r['relationship_type'].lower()}"]
    if r["relationship_type"] == "IS_ULTIMATELY_CONSOLIDATED_BY":
        labels.append("intermediate_layers_not_stated")
    if r["registration_status"] == "LAPSED":
        labels.append(f"relationship_record_lapsed:last_updated_{raw['last_update_date']}")
    if r["accounting_standard"]:
        labels.append(f"accounting_standard:{r['accounting_standard']}")
    status = r["relationship_status"]
    common = {
        "interested_party_id": f"lei:{r['parent_id']}",
        "subject_entity_id": f"lei:{r['child_lei']}",
        "start_date": period["start"] if period else None,
        "start_precision": "day" if period and period["start"] else None,
        "end_date": period["end"] if period else None,
        "end_precision": "day" if period and period["end"] else None,
        "end_status": "ongoing" if status == "ACTIVE" else
                      ("ended" if period and period["end"] else "unknown"),
        "basis": "documented",
        "assertion_status": "stated",
        "record_id": rid,
    }  # fmt: skip
    sink.write("relationships", {"rel_id": f"{rid}/{interest}", "interest_type": interest,
                                 "graph": graph, "labels": labels, **common})  # fmt: skip
    pct = r["percentage"]
    if r["relationship_type"] == "IS_DIRECTLY_CONSOLIDATED_BY" and pct is not None:
        if 0 <= pct <= 100:
            sink.write("relationships", {
                "rel_id": f"{rid}/equity", "interest_type": "shareholding", "graph": "equity",
                "share_min": pct / 100, "share_max": pct / 100,
                "labels": [*labels, "gleif_consolidation_pct_not_defined_as_equity"], **common,
            })  # fmt: skip
