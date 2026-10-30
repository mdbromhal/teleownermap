"""FCC ULS license (`l_*.zip`) and application (`a_*.zip`) files into the statement tables.
Modeling choices are in docs/decisions.md.

Record types loaded: HD header, EN entity, AD application detail, MK market, LO location,
HS license history. Rows of one license or application share `unique_system_identifier`.

- License files give licenses, their licensees and contacts, transmitter sites and history.
- Application files give dated applications: who applied, and for transfers of control (TC)
  and assignments (AA), the transferor/assignor and transferee named in the application.
  They keep old applications, so they partly fill the history `owner.zip` lacks.
- Entity types come from FCC's documented Applicant Type Code.
- Race, ethnicity and sex fields are never stored. Individuals' addresses, phone, fax and
  email are kept only as keyed hashes, and so are their transmitter sites.
"""

from __future__ import annotations

import io
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import duckdb

from teleownermap.ingest._bulk import BATCH_ROWS, TableSink
from teleownermap.ingest.hashing import (
    hash_address,
    hash_value,
    standardize,
    standardize_phone,
)
from teleownermap.ingest.uls_columns import COLUMNS

PARSER_VERSION = "fcc_uls/1"
LOADED = ("MK", "HD", "EN", "AD", "TA", "LO", "HS")  # MK and HD before EN and LO need them
INSERT_ORDER = (
    "records",
    "entities",
    "licenses",
    "license_sites",
    "entity_records",
    "identifiers",
    "attributes",
    "relationships",
    "events",
)

# FCC code list, "EN Applicant Type Code" (docs/decisions.md).
APPLICANT_TYPES = {
    "I": ("person", None),
    "G": ("government", "Governmental Entity"),
    "N": ("government", "Tribal Entity"),
    "B": ("company", "Amateur Club"),
    "C": ("company", "Corporation"),
    "D": ("company", "General Partnership"),
    "E": ("company", "Limited Partnership"),
    "F": ("company", "Limited Liability Partnership"),
    "J": ("company", "Joint Venture"),
    "L": ("company", "Limited Liability Company"),
    "M": ("company", "Military Recreation"),
    "O": ("company", "Consortium"),
    "P": ("company", "Partnership"),
    "R": ("company", "RACES"),
    "T": ("company", "Trust"),
    "U": ("company", "Unincorporated Association"),
    "Z": ("company", "Tribal Entity Controlled by a Business"),
    "H": ("unclassified", "Other"),
}
TYPE_RANK = {"unclassified": 0, "company": 1, "government": 2}

# HD fields never stored anywhere in the database.
DEMOGRAPHIC_FIELDS = (
    "female",
    "black_or_african_american",
    "native_american",
    "hawaiian",
    "asian",
    "white",
    "hispanic",
)
TA_DEMOGRAPHIC_FIELDS = (
    "assignor_transferor_male_or_female",
    "assignor_transferor_african_american",
    "assignor_transferor_native_american",
    "assignor_transferor_hawaiian_other_pacific",
    "assignor_transferor_asian",
    "assignor_transferor_white",
    "assignor_transferor_ethnicity",
)
PERSON_EN_FIELDS = ("street_address", "city", "zip_code", "po_box", "phone", "fax", "email")
PERSON_LO_FIELDS = ("location_address", "location_city", "location_county_borough_parish")
# HD answers stored as stated attributes on the licensee.
HD_ANSWERS = ("alien", "alien_government", "alien_corporation", "alien_officer",
              "alien_control", "revoked", "convicted", "adjudged")  # fmt: skip

# FCC code list, "HS History Code": license events kept with their own type.
HISTORY_EVENTS = {
    "LIISS": "license_issued",
    "LITRAN": "license_transferred",
    "LIASS": "license_assigned",
    "LIPASS": "license_partially_assigned",
    "LIREN": "license_renewed",
    "LICAN": "license_canceled",
    "LIEXP": "license_expired",
}
APPLICATION_EVENTS = {"NE": "license_application", "TC": "transfer_of_control_application",
                      "AA": "assignment_application"}  # fmt: skip
# Application EN roles (FCC code list, "EN Entity Type": L licensee or assignee,
# E transferee, R assignor or transferor). In a transfer of control the licensee (L) stays
# and control moves from R to E; in an assignment there is no L row and the license moves
# from R to the assignee E, so E is the subject.
PARTY_ROLES = {
    "TC": {"R": "transferor", "E": "transferee"},
    "AA": {"R": "assignor"},
}
# Amendments, withdrawals and data corrections restate the parties of the original
# application; AD gives that application's purpose.
RESTATING_PURPOSES = ("AM", "WD", "DC")
CONTACT_TYPES = ("CL", "CE", "CR", "CS")


@dataclass(frozen=True)
class Row:
    member: str
    line: int
    fields: dict[str, str | None]


@dataclass
class ParseReport:
    rows: dict[str, int] = field(default_factory=dict)
    malformed: list[tuple[str, int, int]] = field(default_factory=list)


def _clean(value: str) -> str | None:
    value = value.replace("\x00", "").strip()
    return value or None


def read_rows(path: Path, report: ParseReport | None = None) -> Iterator[Row]:
    """Yield the loaded record types in LOADED order, joining records broken across lines."""
    with zipfile.ZipFile(path) as zf:
        names = {Path(n).name: n for n in zf.namelist()}
        for rtype in LOADED:
            member = names.get(f"{rtype}.dat")
            if member is None:
                continue
            cols = COLUMNS[rtype]
            buf, start = None, 0
            with zf.open(member) as raw:
                text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
                for n, line in enumerate(text, start=1):
                    line = line.rstrip("\r\n")
                    buf, start = (line, n) if buf is None else (buf + "\n" + line, start)
                    count = buf.count("|") + 1
                    if count < len(cols):
                        continue
                    if count == len(cols):
                        if report is not None:
                            report.rows[rtype] = report.rows.get(rtype, 0) + 1
                        values = map(_clean, buf.split("|"))
                        yield Row(f"{rtype}.dat", start, dict(zip(cols, values, strict=True)))
                    elif report is not None:
                        report.malformed.append((f"{rtype}.dat", start, count))
                    buf = None


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        return None


def _coordinate(deg, minutes, sec, direction) -> float | None:
    try:
        value = float(deg) + float(minutes or 0) / 60 + float(sec or 0) / 3600
    except (TypeError, ValueError):
        return None
    return -value if direction in ("S", "W") else value


def _person_name(f: dict) -> str | None:
    parts = [f.get(k) for k in ("first_name", "mi", "last_name", "suffix")]
    return " ".join(p for p in parts if p) or None


class _Loader:
    def __init__(self, source_id: str, key: bytes, is_license_file: bool):
        self.source_id = source_id
        self.key = key
        self.license_file = is_license_file
        self.sink = TableSink(INSERT_ORDER)
        self.entity_types: dict[str, Counter] = defaultdict(Counter)
        self.entity_labels: dict[str, set[str]] = defaultdict(set)
        self.markets: dict[str, str] = {}
        self.headers: dict[str, dict] = {}
        """usi -> HD answers and certifier, attached once the licensee is known."""
        self.licensee: dict[str, tuple[str, bool]] = {}
        """usi -> (licensee entity, is a person)."""
        self.purpose: dict[str, tuple[str | None, str | None, date | None]] = {}
        """usi -> (application purpose, status, receipt date)."""
        self.parties: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        """usi -> [(EN entity type, entity, record)] for application roles."""
        self.transfers: dict[str, dict] = {}
        """usi -> TA consent/consummation dates and labels."""
        self.original: dict[str, str] = {}
        """usi -> original application purpose, for amendments/withdrawals/corrections."""
        self._n = 0

    def _id(self, record_id: str, kind: str) -> str:
        self._n += 1
        return f"{record_id}/{kind}{self._n}"

    def record(self, row: Row, redact: tuple[str, ...] = (), drop: tuple[str, ...] = ()) -> str:
        record_id = f"{self.source_id}:{row.member}:{row.line}"
        raw = {k: (None if k in redact else v) for k, v in row.fields.items() if k not in drop}
        if redact:
            raw["redacted"] = [k for k in redact if row.fields.get(k)]
        self.sink.write("records", {"record_id": record_id, "source_id": self.source_id,
                                    "locator": f"{row.member} line {row.line}", "raw": raw,
                                    "parser_version": PARSER_VERSION})  # fmt: skip
        return record_id

    def entity(self, frn: str | None, etype: str, record_id: str, suffix: str = "") -> str:
        entity_id = f"frn:{frn}" if frn else f"{record_id}{suffix}"
        self.entity_types[entity_id][etype] += 1
        self.sink.write("entity_records", {"entity_id": entity_id, "record_id": record_id})
        if frn:
            self.sink.write("identifiers", {"entity_id": entity_id, "scheme": "FRN",
                                            "value": frn, "record_id": record_id,
                                            "conflict_flag": False})  # fmt: skip
        return entity_id

    def attr(self, entity_id: str, name: str, value, record_id: str, **extra) -> None:
        if value is None and not extra.get("is_sensitive"):
            return
        self.sink.write("attributes", {"attribute_id": self._id(record_id, "attr"),
                                       "entity_id": entity_id, "name": name, "value": value,
                                       "record_id": record_id, "is_sensitive": False,
                                       **extra})  # fmt: skip

    def license_id(self, usi: str) -> str:
        return f"{self.source_id}#{usi}"

    # -- record types --------------------------------------------------------------------

    def market(self, row: Row) -> None:
        f = row.fields
        self.record(row)
        if f["market_code"]:
            name = f"{f['market_code']} {f['market_name'] or ''}".strip()
            self.markets[f["unique_system_identifier"]] = name

    def header(self, row: Row) -> None:
        f = row.fields
        rid = self.record(row, drop=DEMOGRAPHIC_FIELDS)
        usi = f["unique_system_identifier"]
        self.headers[usi] = {"record_id": rid, **{k: f[k] for k in HD_ANSWERS},
                             "certifier": " ".join(f[k] for k in ("certifier_first_name",
                                                   "certifier_mi", "certifier_last_name",
                                                   "certifier_suffix") if f[k]) or None,
                             "certifier_title": f["certifier_title"]}  # fmt: skip
        if not self.license_file:
            return
        lic = self.license_id(usi)
        dates = {k: _date(f[k]) for k in ("grant_date", "expired_date", "effective_date",
                                          "cancellation_date")}  # fmt: skip
        self.sink.write("licenses", {"license_id": lic, "call_sign": f["call_sign"],
                                     "radio_service": f["radio_service_code"],
                                     "market": self.markets.get(usi),
                                     "grant_date": dates["grant_date"],
                                     "expiry_date": dates["expired_date"],
                                     "effective_date": dates["effective_date"],
                                     "cancellation_date": dates["cancellation_date"],
                                     "status": f["license_status"],
                                     "auction_id": f["auction_id"],
                                     "record_id": rid})  # fmt: skip
        for kind, key in (("license_grant", "grant_date"), ("license_expiry", "expired_date"),
                          ("license_cancellation", "cancellation_date")):  # fmt: skip
            if dates[key]:
                self.event(rid, kind, dates[key], license_id=lic)

    def event(self, record_id: str, kind: str, when: date, **about) -> None:
        self.sink.write("events", {"event_id": self._id(record_id, "event"), "event_type": kind,
                                   "date": when, "precision": "day", "record_id": record_id,
                                   **about})  # fmt: skip

    def transfer(self, row: Row) -> None:
        """TA: FCC consent and consummation dates of an assignment or transfer of control."""
        f = row.fields
        rid = self.record(row, drop=TA_DEMOGRAPHIC_FIELDS)
        labels = [f"{k}:{f[k]}" for k in ("pro_forma", "full_assignment",
                                          "voluntary_involuntary") if f[k]]  # fmt: skip
        self.transfers[f["unique_system_identifier"]] = {
            "record_id": rid,
            "consent": _date(f["consent_date"]),
            "consummation": _date(f["consummation_date"]),
            "labels": labels,
        }

    def application(self, row: Row) -> None:
        f = row.fields
        self.record(row)
        purpose = f["application_purpose"]
        if purpose in RESTATING_PURPOSES and f["original_application_purpose"]:
            self.original[f["unique_system_identifier"]] = f["original_application_purpose"]
        self.purpose[f["unique_system_identifier"]] = (
            purpose,
            f["application_status"],
            _date(f["receipt_date"]),
        )

    def en(self, row: Row) -> None:
        f = row.fields
        usi, role = f["unique_system_identifier"], f["entity_type"]
        person = f["entity_name"] is None and f["last_name"] is not None
        rid = self.record(row, PERSON_EN_FIELDS if person else ())
        if role == "O":  # repeats the licensee's name on every license; kept as a record only
            return
        frn = f["fcc_registration_number_frn"]
        if role in CONTACT_TYPES:
            etype = "person" if person else "company"
            ent = self.entity(frn, etype, rid)
        else:
            etype, label = APPLICANT_TYPES.get(f["applicant_type_code"] or "", (None, None))
            if etype is None:
                etype = "person" if person else "unclassified"
            elif person and etype != "person":
                etype = "person"
            ent = self.entity(frn, etype, rid)
            if label:
                self.entity_labels[ent].add(f"fcc_applicant_type:{label}")
        self.attr(ent, "name", _person_name(f) if person else f["entity_name"], rid)
        self.contact_details(ent, rid, f, person)

        if role in CONTACT_TYPES and self.license_file:
            self.rel(rid, ent, "license_contact", title_as_written=f["attention_line"],
                     subject_license_id=self.license_id(usi))  # fmt: skip
            return
        if role == "L":
            self.licensee[usi] = (ent, person)
            self.licensee_details(usi, ent, rid)
        else:
            self.parties[usi].append((role, ent, rid))

    def contact_details(self, ent: str, rid: str, f: dict, person: bool) -> None:
        h = hash_address(self.key, street=f["street_address"] or f["po_box"], street2=None,
                         city=f["city"], state=f["state"], zip_code=f["zip_code"],
                         country=None)  # fmt: skip
        if any((f["street_address"], f["po_box"], f["city"], f["zip_code"])):
            plain = ", ".join(p for p in (f["street_address"], f["po_box"], f["city"],
                                          f["state"], f["zip_code"]) if p)  # fmt: skip
            self.attr(ent, "address", None if person else plain, rid, is_sensitive=person,
                      hmac_full=h.full, hmac_zip=h.zip, hmac_city=h.city)  # fmt: skip
            if person:
                self.attr(ent, "address_state", f["state"], rid)
        for name in ("phone", "fax"):
            if f[name]:
                digest = hash_value(self.key, "phone", standardize_phone(f[name]))
                self.attr(ent, name, None if person else f[name], rid, is_sensitive=person,
                          hmac_full=digest)  # fmt: skip
        if f["email"]:
            digest = hash_value(self.key, "email", f["email"].strip().lower())
            self.attr(ent, "email", None if person else f["email"], rid, is_sensitive=person,
                      hmac_full=digest)  # fmt: skip

    def licensee_details(self, usi: str, ent: str, rid: str) -> None:
        hd = self.headers.get(usi)
        if self.license_file:
            self.rel(rid, ent, "license_holder", subject_license_id=self.license_id(usi))
        if hd is None:
            return
        for answer in HD_ANSWERS:
            self.attr(ent, f"fcc_answer:{answer}", hd[answer], hd["record_id"])
        if hd["certifier"]:
            cert = self.entity(None, "person", hd["record_id"], "/certifier")
            self.attr(cert, "name", hd["certifier"], hd["record_id"])
            subject = ({"subject_license_id": self.license_id(usi)} if self.license_file
                       else {"subject_entity_id": ent})  # fmt: skip
            self.rel(hd["record_id"], cert, "filing_author",
                     title_as_written=hd["certifier_title"], **subject)  # fmt: skip

    def location(self, row: Row) -> None:
        f = row.fields
        usi = f["unique_system_identifier"]
        person = self.licensee.get(usi, (None, False))[1]
        rid = self.record(row, PERSON_LO_FIELDS if person else ())
        if not self.license_file:
            return
        lat = _coordinate(f["latitude_degrees"], f["latitude_minutes"], f["latitude_seconds"],
                          f["latitude_direction"])  # fmt: skip
        lon = _coordinate(f["longitude_degrees"], f["longitude_minutes"],
                          f["longitude_seconds"], f["longitude_direction"])  # fmt: skip
        coords = f"{lat:.5f},{lon:.5f}" if lat is not None and lon is not None else None
        address = standardize(" ".join(p for p in (f["location_address"], f["location_city"],
                                                   f["location_state"]) if p))  # fmt: skip
        self.sink.write("license_sites", {
            "site_id": rid, "license_id": self.license_id(usi),
            "address": None if person else f["location_address"],
            "city": None if person else f["location_city"],
            "county": None if person else f["location_county_borough_parish"],
            "state": f["location_state"],
            "latitude": None if person else lat, "longitude": None if person else lon,
            "tower_registration": f["tower_registration_number"], "is_sensitive": person,
            "hmac_coords": hash_value(self.key, "coords", coords),
            "hmac_address": hash_value(self.key, "site", address), "record_id": rid,
        })  # fmt: skip

    def history(self, row: Row) -> None:
        f = row.fields
        rid = self.record(row)
        when = _date(f["log_date"])
        if self.license_file and when and f["code"]:
            kind = HISTORY_EVENTS.get(f["code"], f"uls_history:{f['code']}")
            self.event(rid, kind, when, license_id=self.license_id(f["unique_system_identifier"]))

    def rel(self, record_id: str, party: str, kind: str, **cols) -> None:
        self.sink.write("relationships", {"rel_id": self._id(record_id, "rel"),
                                          "interested_party_id": party, "interest_type": kind,
                                          "graph": "none", "basis": "documented",
                                          "assertion_status": "stated", "record_id": record_id,
                                          **cols})  # fmt: skip

    def finish_applications(self) -> None:
        """Application events and the parties named in transfers and assignments."""
        for usi, (purpose, status, received) in self.purpose.items():
            parties = self.parties.get(usi, ())
            applicant = self.licensee.get(usi, (None,))[0]
            if applicant is None:  # an assignment: the assignee (E) is the subject
                applicant = next((ent for role, ent, _ in parties if role == "E"), None)
            hd = self.headers.get(usi)
            rid = hd["record_id"] if hd else None
            if applicant is None or rid is None:
                continue
            labels = [f"application_purpose:{purpose}", f"application_status:{status}"]
            original = self.original.get(usi)
            if original:
                labels.append(f"original_application_purpose:{original}")
            roles = PARTY_ROLES.get(original or purpose, {})
            if received:
                kind = APPLICATION_EVENTS.get(purpose, f"application:{purpose}")
                self.event(rid, kind, received, entity_id=applicant)
            ta = self.transfers.get(usi)
            if ta:
                labels += ta["labels"]
                for kind in ("consent", "consummation"):
                    if ta[kind]:
                        self.event(ta["record_id"], f"transfer_{kind}", ta[kind],
                                   entity_id=applicant)  # fmt: skip
            for role, party, party_rid in parties:
                if role in CONTACT_TYPES:
                    self.rel(party_rid, party, "license_contact", subject_entity_id=applicant,
                             filing_date=received, labels=labels)  # fmt: skip
                    continue
                kind = roles.get(role)
                if kind and party != applicant:
                    self.rel(party_rid, party, kind, subject_entity_id=applicant,
                             filing_date=received,
                             effective_date=ta["consummation"] if ta else None,
                             labels=labels)  # fmt: skip

    def entities(self) -> Iterator[dict]:
        for entity_id, types in self.entity_types.items():
            labels = set(self.entity_labels.get(entity_id, ()))
            named = {t for t in types if t != "unclassified"}
            if "person" in named and len(named) > 1:
                labels.add("conflicting_entity_types:" + "/".join(sorted(named)))
                etype = types.most_common(1)[0][0]
            elif named:
                etype = max(named, key=lambda t: TYPE_RANK.get(t, 1))
            else:
                etype = "unclassified"
            yield {"entity_id": entity_id, "entity_type": etype,
                   "labels": sorted(labels) or None}  # fmt: skip


def load(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    source_id: str,
    key: bytes,
    *,
    batch_rows: int = BATCH_ROWS,
) -> ParseReport:
    """Parse one l_*.zip or a_*.zip and load it. A source already loaded is skipped."""
    report = ParseReport()
    if con.execute("SELECT count(*) FROM records WHERE source_id = ?", [source_id]).fetchone()[0]:
        return report
    loader = _Loader(source_id, key, is_license_file=Path(path).name.startswith("l_"))
    loader.sink = TableSink(INSERT_ORDER, batch_rows)
    handlers = {"MK": loader.market, "HD": loader.header, "EN": loader.en,
                "AD": loader.application, "TA": loader.transfer, "LO": loader.location,
                "HS": loader.history}  # fmt: skip
    try:
        for row in read_rows(path, report):
            handlers[row.fields["record_type"]](row)
        loader.finish_applications()
        for entity in loader.entities():
            loader.sink.write("entities", entity)
        loader.sink.insert(con, or_ignore=("entities",))
    finally:
        loader.sink.close()
    return report
