"""FCC ULS ownership file (`owner.zip`: Form 602 ownership filings and Form 175 auction
short-forms) into the statement tables. Modeling choices are in docs/decisions.md.

Record types (FCC "Public Access Table for Ownership Filing"): O filer, D disclosable
interest holder (DIH), F FCC-regulated businesses (FRBs) of the filer, H FRBs of a DIH,
A Form 175 affiliate, T attachment. All rows of one filing share `unique_system_identifier`.

- Only direct holders enter the equity graph. Indirect holders and F/H holdings are kept as
  "named" links with an upper-bound share (`graph = 'none'`), because FCC reports any link
  over 50% or controlling as 100% and lists every level of one stake separately.
- Officers, directors, key management and management contracts are control links.
- A person's street, address line 2, city and ZIP are stored only as keyed hashes.
- Records sharing an FRN are one entity; a party without an FRN is its own entity.
"""

from __future__ import annotations

import io
import zipfile
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

from teleownermap.ingest._bulk import bulk_insert
from teleownermap.ingest.hashing import hash_address

PARSER_VERSION = "fcc_owner/1"

# Column names from FCC's pubacc_ownership_sql_tbl_def.txt (same order as the files).
COLUMNS: dict[str, tuple[str, ...]] = {
    "O": (
        "record_type", "frn_filer", "file_num", "filer_fname", "filer_mi", "filer_lname",
        "filer_suffix", "filer_name", "date_entered", "date_receipt", "certifier_fname",
        "certifier_mi", "certifier_lname", "certifier_suffix", "certifier_title",
        "contact_company", "contact_fname", "contact_mi", "contact_lname", "contact_suffix",
        "contact_phone", "contact_fax", "contact_address", "contact_city", "contact_state",
        "contact_zip_code", "contact_po_box", "contact_email", "form_num", "filing_type",
        "filing_status", "unique_system_identifier",
    ),
    "F": (
        "record_type", "file_num", "business_name", "principal_business", "frn",
        "pct_interest", "form_num", "filing_type", "filing_status", "unique_system_identifier",
    ),
    "H": (
        "record_type", "file_num", "business_name", "principle_business", "frn", "dih_frn",
        "pct_interest", "form_num", "filing_type", "filing_status", "unique_system_identifier",
    ),
    "D": (
        "record_type", "file_num", "entity_name", "type_entity", "fname", "mi", "lname",
        "suffix", "frn", "address", "address2", "city", "state", "zip_code", "country",
        "international_address_ind", "interest_direct", "interest_indirect",
        "interest_officer", "interest_director", "interest_key_mgmt",
        "interest_mgmt_contract", "interest_other", "interest_other_desc", "own_comm_stk",
        "own_comm_stk_vote_ind", "own_gen_part", "own_gen_part_vote_ind", "own_ltd_part",
        "own_ltd_part_vote_ind", "own_member", "own_option", "own_proprietor",
        "own_pref_stk", "own_pref_stk_vote_ind", "own_pref_stk_convert_ind", "own_warrant",
        "own_other", "own_other_desc", "pct_interest", "country_citizenship", "jurisdiction",
        "state_jurisdiction", "non_affiliate_option", "year1_in_existence", "year1_end_date",
        "year1_revenue", "year2_in_existence", "year2_end_date", "year2_revenue",
        "year3_in_existence", "year3_end_date", "year3_revenue", "total_assets",
        "financial_statement_type", "form_num", "filing_type", "filing_status",
        "unique_system_identifier",
    ),
    "A": (
        "record_type", "file_num", "type_entity", "fname", "mi", "lname", "suffix",
        "entity_name", "principal_business", "frn", "year1_in_existence", "year1_end_date",
        "year1_revenue", "year2_in_existence", "year2_end_date", "year2_revenue",
        "year3_in_existence", "year3_end_date", "year3_revenue", "total_assets",
        "financial_statement_type", "form_num", "filing_type", "filing_status",
        "unique_system_identifier",
    ),
    "T": (
        "record_type", "file_num", "attachment_code", "attachment_desc", "attachment_date",
        "attachment_filename", "form_num", "filing_type", "filing_status",
        "unique_system_identifier",
    ),
}  # fmt: skip
MEMBERS = {f"_{t}.dat": t for t in COLUMNS}

# The only `type_entity` code checked against ULS's display ("Government Entity", City of
# Bastrop filing). Other codes are undefined in FCC's code list and kept only as labels.
GOVERNMENT_CODE = "b"

# A person's address parts that are hashed and never stored (docs/decisions.md).
SENSITIVE_PERSON_FIELDS = ("address", "address2", "city", "zip_code")

# Form 602 Item 5 categories that are control links, with the classification shown.
CONTROL_ROLES = {
    "interest_officer": ("officer", "Officer", "(officer)"),
    "interest_director": ("board_seat", "Director", "(director)"),
    "interest_key_mgmt": ("key_management", "Key management personnel", "(key management)"),
    "interest_mgmt_contract": (
        "management_contract",
        "Management contract",
        "(management contract)",
    ),
}
STOCK_CLASSES = {
    "own_comm_stk": ("common_stock", "own_comm_stk_vote_ind"),
    "own_gen_part": ("general_partnership", "own_gen_part_vote_ind"),
    "own_ltd_part": ("limited_partnership", "own_ltd_part_vote_ind"),
    "own_member": ("membership", None),
    "own_option": ("option", None),
    "own_proprietor": ("proprietorship", None),
    "own_pref_stk": ("preferred_stock", "own_pref_stk_vote_ind"),
    "own_warrant": ("warrant", None),
    "own_other": ("other", None),
}


@dataclass(frozen=True)
class Row:
    member: str
    line: int
    """First line of the record in its member file (records can span lines)."""
    fields: dict[str, str | None]


@dataclass
class ParseReport:
    rows: dict[str, int]
    stitched: int
    """Records that were split across lines in the file and joined back together."""
    malformed: list[tuple[str, int, int]]
    """(member, line, field count) of records that couldn't be reassembled; skipped."""


def _clean(value: str) -> str | None:
    value = value.replace("\x00", "").strip()
    return value or None


def read_rows(path: Path, report: ParseReport | None = None) -> Iterator[Row]:
    """Yield every record in owner.zip, joining records broken across lines (free-text
    fields can contain line breaks)."""
    with zipfile.ZipFile(path) as zf:
        for member in zf.namelist():
            rtype = MEMBERS.get(Path(member).name)
            if rtype is None:
                continue
            want = len(COLUMNS[rtype])
            buf, start = None, 0
            with zf.open(member) as raw:
                text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
                for n, line in enumerate(text, start=1):
                    line = line.rstrip("\r\n")
                    if buf is None:
                        buf, start = line, n
                    else:
                        buf += "\n" + line
                    count = buf.count("|") + 1
                    if count < want:
                        continue
                    if count == want:
                        fields = dict(zip(COLUMNS[rtype], map(_clean, buf.split("|")), strict=True))
                        if report is not None:
                            report.rows[rtype] = report.rows.get(rtype, 0) + 1
                            report.stitched += n != start
                        yield Row(member=Path(member).name, line=start, fields=fields)
                    elif report is not None:
                        report.malformed.append((Path(member).name, start, count))
                    buf = None
                if buf is not None and report is not None:
                    report.malformed.append((Path(member).name, start, buf.count("|") + 1))


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        return None


def _pct(value: str | None) -> tuple[float | None, list[str]]:
    """Share as a fraction, plus a label when the reported value can't be a share."""
    if value is None:
        return None, []
    try:
        share = float(value) / 100
    except ValueError:
        return None, [f"reported_pct:{value}"]
    if not 0 <= share <= 1:
        return None, [f"reported_pct:{value}"]
    return share, []


def _person_name(f: dict, prefix: str = "") -> str | None:
    parts = [f.get(prefix + k) for k in ("fname", "mi", "lname", "suffix")]
    return " ".join(p for p in parts if p) or None


class _Loader:
    def __init__(self, source_id: str, key: bytes):
        self.source_id = source_id
        self.key = key
        self.tables: dict[str, list[dict]] = defaultdict(list)
        self.entity_types: dict[str, set[str]] = defaultdict(set)
        self.entity_labels: dict[str, set[str]] = defaultdict(set)
        self.filers: dict[str, tuple[str, date | None]] = {}
        """unique_system_identifier -> (filer entity, filing date)."""
        self.self_described: dict[str, str] = {}
        """Type of each FRN holder that filed for itself; wins over others' descriptions."""

    # -- helpers -------------------------------------------------------------------------

    def record(self, row: Row, redact: tuple[str, ...] = ()) -> str:
        record_id = f"{self.source_id}:{row.member}:{row.line}"
        raw = {k: (None if k in redact else v) for k, v in row.fields.items()}
        if redact:
            raw["redacted"] = [k for k in redact if row.fields.get(k)]
        self.tables["records"].append(
            {
                "record_id": record_id,
                "source_id": self.source_id,
                "locator": f"{row.member} line {row.line}",
                "raw": raw,
                "parser_version": PARSER_VERSION,
            }
        )
        return record_id

    def entity(self, frn: str | None, etype: str, record_id: str, suffix: str = "") -> str:
        """FRN holders are one entity per FRN; anyone else is one entity per record."""
        entity_id = f"frn:{frn}" if frn else f"{record_id}{suffix}"
        self.entity_types[entity_id].add(etype)
        self.tables["entity_records"].append({"entity_id": entity_id, "record_id": record_id})
        if frn:
            self.tables["identifiers"].append(
                {"entity_id": entity_id, "scheme": "FRN", "value": frn, "record_id": record_id}
            )
        return entity_id

    def attr(self, entity_id: str, name: str, value, record_id: str, **extra) -> None:
        if value is None and not extra.get("is_sensitive"):
            return
        n = len(self.tables["attributes"])
        self.tables["attributes"].append(
            {
                "attribute_id": f"{record_id}/attr{n}",
                "entity_id": entity_id,
                "name": name,
                "value": value,
                "record_id": record_id,
                "is_sensitive": False,
                **extra,
            }
        )

    def address(self, entity_id, record_id, *, person, street, street2, city, state, zip_code,
                country) -> None:  # fmt: skip
        if not any((street, street2, city, zip_code)):
            return
        h = hash_address(
            self.key,
            street=street,
            street2=street2,
            city=city,
            state=state,
            zip_code=zip_code,
            country=country,
        )
        plain = ", ".join(p for p in (street, street2, city, state, zip_code, country) if p)
        self.attr(
            entity_id,
            "address",
            None if person else plain,
            record_id,
            is_sensitive=person,
            hmac_full=h.full,
            hmac_zip=h.zip,
            hmac_city=h.city,
        )
        if person:  # state and country are shown (docs/decisions.md)
            self.attr(entity_id, "address_state", state, record_id)
            self.attr(entity_id, "address_country", country, record_id)

    def rel(self, record_id: str, kind: str, **cols) -> None:
        cols.setdefault("basis", "documented")
        cols.setdefault("assertion_status", "stated")
        self.tables["relationships"].append(
            {"rel_id": f"{record_id}/{kind}", "record_id": record_id, **cols}
        )

    @staticmethod
    def filing_labels(f: dict) -> list[str]:
        """Form number plus FCC's raw filing type (C/P) and status codes, which FCC's code
        list doesn't define, so they're passed through as written."""
        return [
            f"form_{f['form_num']}",
            f"filing_type:{f.get('filing_type')}",
            f"filing_status:{f.get('filing_status')}",
        ]

    # -- record types --------------------------------------------------------------------

    def filer(self, row: Row) -> None:
        f = row.fields
        rid = self.record(row)
        person = f["filer_lname"] is not None and f["filer_name"] is None
        filer = self.entity(f["frn_filer"], "person" if person else "company", rid)
        self.self_described[filer] = "person" if person else "company"
        self.attr(filer, "name", _person_name(f, "filer_") if person else f["filer_name"], rid)
        filed = _date(f["date_receipt"]) or _date(f["date_entered"])
        self.filers[f["unique_system_identifier"]] = (filer, filed)
        if filed:
            self.tables["events"].append(
                {
                    "event_id": f"{rid}/filed",
                    "entity_id": filer,
                    "event_type": f"form_{f['form_num']}_filing",
                    "date": filed,
                    "precision": "day",
                    "record_id": rid,
                }
            )
        common = {"subject_entity_id": filer, "graph": "none", "filing_date": filed,
                  "labels": self.filing_labels(f)}  # fmt: skip
        if f["contact_company"]:
            counsel = self.entity(None, "company", rid, "/counsel")
            self.attr(counsel, "name", f["contact_company"], rid)
            self.address(counsel, rid, person=False, street=f["contact_address"], street2=None,
                         city=f["contact_city"], state=f["contact_state"],
                         zip_code=f["contact_zip_code"], country=None)  # fmt: skip
            self.attr(counsel, "phone", f["contact_phone"], rid)
            self.attr(counsel, "email", f["contact_email"], rid)
            self.rel(rid, "counsel", interested_party_id=counsel, interest_type="legal_counsel",
                     **common)  # fmt: skip
        if f["contact_lname"]:
            contact = self.entity(None, "person", rid, "/contact")
            self.attr(contact, "name", _person_name(f, "contact_"), rid)
            if not f["contact_company"]:
                self.attr(contact, "phone", f["contact_phone"], rid)
                self.attr(contact, "email", f["contact_email"], rid)
            self.rel(rid, "contact", interested_party_id=contact, interest_type="filing_author",
                     title_as_written="Contact", **common)  # fmt: skip
        if f["certifier_lname"]:
            certifier = self.entity(None, "person", rid, "/certifier")
            self.attr(certifier, "name", _person_name(f, "certifier_"), rid)
            self.rel(rid, "certifier", interested_party_id=certifier,
                     interest_type="filing_author", title_as_written=f["certifier_title"],
                     **common)  # fmt: skip

    def holder(self, row: Row) -> None:
        f = row.fields
        person = f["entity_name"] is None and (f["lname"] or f["fname"]) is not None
        named = f["entity_name"] is not None or person
        rid = self.record(row, SENSITIVE_PERSON_FIELDS if person else ())
        etype = "person" if person else ("company" if named else "unclassified")
        if not person and f["type_entity"] == GOVERNMENT_CODE:
            etype = "government"
        dih = self.entity(f["frn"], etype, rid)
        if f["type_entity"]:
            self.entity_labels[dih].add(f"fcc_type_entity:{f['type_entity']}")
        self.attr(dih, "name", _person_name(f) if person else f["entity_name"], rid)
        self.address(dih, rid, person=person, street=f["address"], street2=f["address2"],
                     city=f["city"], state=f["state"], zip_code=f["zip_code"],
                     country=f["country"])  # fmt: skip
        self.attr(dih, "citizenship", f["country_citizenship"], rid)
        self.attr(dih, "jurisdiction", f["jurisdiction"], rid)
        self.attr(dih, "state_jurisdiction", f["state_jurisdiction"], rid)

        filer, filed = self.filers.get(f["unique_system_identifier"], (None, None))
        if filer is None:
            return
        pct, bad_pct = _pct(f["pct_interest"])
        labels = (
            self.filing_labels(f)
            + bad_pct
            + [
                f"{name}:{f[vote]}" if vote and f.get(vote) else name
                for col, (name, vote) in STOCK_CLASSES.items()
                if f.get(col) == "Y"
            ]
        )
        common = {"interested_party_id": dih, "subject_entity_id": filer, "filing_date": filed}
        linked = False
        if f["interest_direct"] == "Y":
            zero = pct == 0
            self.rel(rid, "direct", interest_type="shareholding", graph="equity",
                     share_min=None if zero else pct, share_max=None if zero else pct,
                     labels=labels + (["reported_0.00"] if zero else []), **common)  # fmt: skip
            linked = True
        if f["interest_indirect"] == "Y":
            self.rel(rid, "indirect", interest_type="named_indirect_holder", graph="none",
                     share_min=0.0 if pct else None, share_max=pct or None,
                     labels=labels + ["upper_bound"], **common)  # fmt: skip
            linked = True
        for col, (kind, title, role_class) in CONTROL_ROLES.items():
            if f[col] == "Y":
                self.rel(rid, kind, interest_type=kind, graph="control", title_as_written=title,
                         role_class=role_class, labels=self.filing_labels(f), **common)  # fmt: skip
                linked = True
        if f["interest_other"] == "Y" or not linked:
            desc = f["interest_other_desc"]
            self.rel(rid, "other", interest_type="other_interest", graph="none",
                     title_as_written=desc, labels=labels, **common)  # fmt: skip

    def holding(self, row: Row) -> None:
        """F (filer's) and H (a holder's) FCC-regulated businesses."""
        f = row.fields
        rid = self.record(row)
        frb = self.entity(f["frn"], "company", rid)
        self.attr(frb, "name", f["business_name"], rid)
        if row.fields["record_type"] == "F":
            holder, filed = self.filers.get(f["unique_system_identifier"], (None, None))
        else:
            holder = f"frn:{f['dih_frn']}" if f["dih_frn"] else None
            filed = self.filers.get(f["unique_system_identifier"], (None, None))[1]
        if holder is None:
            return
        pct, bad_pct = _pct(f["pct_interest"])
        self.rel(rid, "holding", interested_party_id=holder, subject_entity_id=frb,
                 interest_type="named_holding", graph="none", share_min=0.0 if pct else None,
                 share_max=pct or None, filing_date=filed,
                 labels=self.filing_labels(f) + bad_pct + ["upper_bound"])  # fmt: skip

    def affiliate(self, row: Row) -> None:
        f = row.fields
        person = f["entity_name"] is None and f["lname"] is not None
        rid = self.record(row)
        etype = "person" if person else "company"
        if not person and f["type_entity"] == GOVERNMENT_CODE:
            etype = "government"
        aff = self.entity(f["frn"], etype, rid)
        if f["type_entity"]:
            self.entity_labels[aff].add(f"fcc_type_entity:{f['type_entity']}")
        self.attr(aff, "name", _person_name(f) if person else f["entity_name"], rid)
        filer, filed = self.filers.get(f["unique_system_identifier"], (None, None))
        if filer is not None:
            self.rel(rid, "affiliate", interested_party_id=aff, subject_entity_id=filer,
                     interest_type="affiliate", graph="none", filing_date=filed,
                     labels=self.filing_labels(f))  # fmt: skip

    # -- output --------------------------------------------------------------------------

    def conflicting(self, entity_id: str) -> bool:
        """A person and a non-person under one FRN: a possible ID error. (A filer row says
        only "not an individual", so company plus government isn't a conflict.)"""
        types = self.entity_types[entity_id] - {"unclassified"}
        return "person" in types and len(types) > 1

    def resolve_type(self, entity_id: str) -> str:
        types = self.entity_types[entity_id]
        own = self.self_described.get(entity_id)
        if "government" in types and own != "person":
            return "government"
        if own:
            return own
        named = types - {"unclassified"}
        if len(named) == 1:
            return next(iter(named))
        return "unclassified"

    def entities(self) -> list[dict]:
        out = []
        for entity_id, types in self.entity_types.items():
            labels = set(self.entity_labels.get(entity_id, ()))
            if self.conflicting(entity_id):
                labels.add("conflicting_entity_types:" + "/".join(sorted(types)))
            out.append(
                {
                    "entity_id": entity_id,
                    "entity_type": self.resolve_type(entity_id),
                    "labels": sorted(labels) or None,
                }
            )
        return out


def load(con: duckdb.DuckDBPyConnection, path: Path, source_id: str, key: bytes) -> ParseReport:
    """Parse owner.zip and load it. A source already loaded is skipped."""
    report = ParseReport(rows={}, stitched=0, malformed=[])
    if con.execute("SELECT count(*) FROM records WHERE source_id = ?", [source_id]).fetchone()[0]:
        return report
    loader = _Loader(source_id, key)
    rows = list(read_rows(path, report))
    # Filers first, so every other row can find its filing.
    order = {"O": 0, "D": 1, "F": 2, "H": 3, "A": 4, "T": 5}
    for row in sorted(rows, key=lambda r: order[r.fields["record_type"]]):
        rtype = row.fields["record_type"]
        if rtype == "O":
            loader.filer(row)
        elif rtype == "D":
            loader.holder(row)
        elif rtype in ("F", "H"):
            loader.holding(row)
        elif rtype == "A":
            loader.affiliate(row)
        else:  # T: exhibit listing, used by the exhibit guide
            loader.record(row)
    # Every H/F link must point at an entity, even one seen only as `dih_frn`.
    for rel in loader.tables["relationships"]:
        party = rel["interested_party_id"]
        if party.startswith("frn:") and party not in loader.entity_types:
            loader.entity_types[party].add("unclassified")
    conflicts = {e for e in loader.entity_types if loader.conflicting(e)}
    for ident in loader.tables["identifiers"]:
        ident["conflict_flag"] = ident["entity_id"] in conflicts
    bulk_insert(con, "records", loader.tables["records"])
    bulk_insert(con, "entities", loader.entities(), or_ignore=True)
    for table in ("entity_records", "identifiers", "attributes", "relationships", "events"):
        bulk_insert(con, table, loader.tables[table])
    return report
