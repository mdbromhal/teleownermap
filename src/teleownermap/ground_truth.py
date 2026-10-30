"""Hand-built ground-truth case graphs (ground_truth/graphs/*.csv).

Each case has one CSV of links, one row per source statement, plus a row in cases.csv giving
the licensees to start from, the snapshot date and the publicly traded companies. Two views
are analyzed (see docs/decisions.md):
- "disclosed": only links found in the companies' own filings and publications.
- "full": every link, including hidden ones from court or FCC documents.
Legal status (stated/alleged/...) is a label for filtering, never a confidence number.

Run `python -m teleownermap.ground_truth` to write results/dev_cases.md.
"""

from __future__ import annotations

import calendar
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import duckdb

from teleownermap.metrics.ownership import (
    RangeResult,
    Stake,
    analyze_range,
    control_reach,
    control_without_equity,
)
from teleownermap.schema import ASSERTION_STATUSES, ENTITY_TYPES, GRAPHS

View = Literal["disclosed", "full"]
VIEWS: tuple[View, ...] = ("disclosed", "full")
PARSER_VERSION = "ground_truth_csv/1"
DEFAULT_DIR = Path(__file__).resolve().parents[2] / "ground_truth" / "graphs"


@dataclass(frozen=True)
class Link:
    case: str
    line: int
    """Line number in the CSV (unique; `row` can repeat when one cases.md row gives several
    links)."""
    row: str
    """The cases.md table row this link comes from."""
    owner: str
    owner_type: str
    owned: str
    owned_type: str
    graph: str
    share_min: float | None
    share_max: float | None
    status: str
    disclosed: bool
    start: str
    end: str
    source: str
    note: str


@dataclass(frozen=True)
class Case:
    case: str
    starts: tuple[str, ...]
    snapshot: date
    snapshot_basis: str
    publicly_traded: tuple[str, ...]


def _split(value: str) -> tuple[str, ...]:
    return tuple(v.strip() for v in value.split(";") if v.strip())


def _share(value: str) -> float | None:
    return float(value) if value.strip() else None


def load_cases(graphs_dir: Path = DEFAULT_DIR) -> list[Case]:
    with open(graphs_dir / "cases.csv", newline="", encoding="utf-8") as f:
        return [
            Case(
                case=r["case"],
                starts=_split(r["starts"]),
                snapshot=date.fromisoformat(r["snapshot"]),
                snapshot_basis=r["snapshot_basis"],
                publicly_traded=_split(r["publicly_traded"]),
            )
            for r in csv.DictReader(f)
        ]


def load_links(path: Path) -> list[Link]:
    """Read and check one case's links. Raises ValueError on any malformed row."""
    case = path.stem
    links = []
    with open(path, newline="", encoding="utf-8") as f:
        for line, r in enumerate(csv.DictReader(f), start=2):
            where = f"{path.name} line {line}"
            if r["graph"] not in GRAPHS:
                raise ValueError(f"{where}: unknown graph {r['graph']!r}")
            if r["status"] not in ASSERTION_STATUSES:
                raise ValueError(f"{where}: unknown status {r['status']!r}")
            if r["disclosed"] not in ("yes", "no"):
                raise ValueError(f"{where}: disclosed must be yes or no")
            for t in (r["owner_type"], r["owned_type"]):
                if t not in ENTITY_TYPES:
                    raise ValueError(f"{where}: unknown entity type {t!r}")
            link = Link(
                case=case,
                line=line,
                row=r["row"],
                owner=r["owner"],
                owner_type=r["owner_type"],
                owned=r["owned"],
                owned_type=r["owned_type"],
                graph=r["graph"],
                share_min=_share(r["share_min"]),
                share_max=_share(r["share_max"]),
                status=r["status"],
                disclosed=r["disclosed"] == "yes",
                start=r["start"].strip(),
                end=r["end"].strip(),
                source=r["source"],
                note=r["note"],
            )
            for s in (link.share_min, link.share_max):
                if s is not None and not 0 <= s <= 1:
                    raise ValueError(f"{where}: share {s} outside [0, 1]")
            if None not in (link.share_min, link.share_max) and link.share_min > link.share_max:
                raise ValueError(f"{where}: share_min > share_max")
            links.append(link)
    _check_entity_types(links)
    return links


def _check_entity_types(links: list[Link]) -> None:
    seen: dict[str, str] = {}
    for link in links:
        for name, t in ((link.owner, link.owner_type), (link.owned, link.owned_type)):
            if seen.setdefault(name, t) != t:
                raise ValueError(f"{link.case}: {name!r} is both {seen[name]} and {t}")


def date_bounds(value: str) -> tuple[date, date, str]:
    """Earliest and latest day a partial date ("2005", "2015-01", "2001-03-13") can mean."""
    parts = [int(p) for p in value.split("-")]
    if len(parts) == 1:
        return date(parts[0], 1, 1), date(parts[0], 12, 31), "year"
    if len(parts) == 2:
        last = calendar.monthrange(parts[0], parts[1])[1]
        return date(parts[0], parts[1], 1), date(parts[0], parts[1], last), "month"
    return date(*parts), date(*parts), "day"


def valid_on(link: Link, snapshot: date) -> bool:
    """Whether the link may hold on the snapshot date. Missing dates count as possibly valid,
    and a start or end in the same year/month as the snapshot is included (inclusive)."""
    if link.start and date_bounds(link.start)[0] > snapshot:
        return False
    if link.end and date_bounds(link.end)[1] < snapshot:
        return False
    return True


def select(links: list[Link], view: View, snapshot: date) -> list[Link]:
    return [
        link for link in links if valid_on(link, snapshot) and (view == "full" or link.disclosed)
    ]


def to_stakes(links: list[Link]) -> tuple[list[Stake], dict[str, str]]:
    """Links the metrics walk (graph "none" is recorded but not walked), plus entity types."""
    entity_types = {}
    for link in links:
        entity_types[link.owner] = link.owner_type
        entity_types[link.owned] = link.owned_type
    stakes = [
        Stake(
            owner=link.owner,
            owned=link.owned,
            share_min=link.share_min,
            share_max=link.share_max,
            graph=link.graph,
            rel_ids=(f"{link.case}:{link.line}",),
            notes=(f"{link.case} row {link.row}: {link.status}",)
            if link.status != "stated"
            else (),
        )
        for link in links
        if link.graph != "none"
    ]
    return stakes, entity_types


def load_into_duckdb(con: duckdb.DuckDBPyConnection, path: Path, links: list[Link]) -> None:
    """Insert one case's links through the real schema, so its constraints check the data."""
    case = path.stem
    source_id = f"ground_truth:{case}"
    con.execute(
        "INSERT INTO sources (source_id, source_type, title, retrieved_at, sha256, local_path, "
        "snapshot_label) VALUES (?, 'hand_built_ground_truth', ?, now(), ?, ?, ?)",
        [
            source_id,
            f"Hand-built graph for {case} from ground_truth/cases.md",
            hashlib.sha256(path.read_bytes()).hexdigest(),
            str(path),
            case,
        ],
    )
    for link in links:
        for name, t in ((link.owner, link.owner_type), (link.owned, link.owned_type)):
            con.execute(
                "INSERT INTO entities (entity_id, entity_type) VALUES (?, ?) "
                "ON CONFLICT DO NOTHING",
                [name, t],
            )
        record_id = rel_id = f"{case}:{link.line}"
        con.execute(
            "INSERT INTO records (record_id, source_id, locator, raw, parser_version) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                record_id,
                source_id,
                f"{case} row {link.row} ({link.source})",
                json.dumps(asdict(link)),
                PARSER_VERSION,
            ],
        )
        start = date_bounds(link.start) if link.start else (None, None, None)
        end = date_bounds(link.end) if link.end else (None, None, None)
        con.execute(
            "INSERT INTO relationships (rel_id, interested_party_id, subject_entity_id, "
            "interest_type, graph, title_as_written, share_min, share_max, start_date, "
            "start_precision, end_date, end_precision, end_status, basis, assertion_status, "
            "record_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'documented', ?, ?)",
            [
                rel_id,
                link.owner,
                link.owned,
                {"equity": "shareholding"}.get(link.graph, link.graph),
                link.graph,
                link.note or None,
                link.share_min,
                link.share_max,
                start[0],
                start[2],
                end[0],
                end[2],
                "ended" if link.end else "unknown",
                link.status,
                record_id,
            ],
        )


@dataclass
class ViewResult:
    case: str
    start: str
    view: View
    ownership: RangeResult
    control: dict[str, int]
    control_without_equity: dict[str, int]
    statuses: dict[str, int]
    """How many walked links of each legal status this view uses."""


def analyze_case(case: Case, links: list[Link]) -> list[ViewResult]:
    results = []
    for start in case.starts:
        for view in VIEWS:
            chosen = select(links, view, case.snapshot)
            stakes, entity_types = to_stakes(chosen)
            entity_types.setdefault(start, "company")
            statuses: dict[str, int] = {}
            for link in chosen:
                if link.graph != "none":
                    statuses[link.status] = statuses.get(link.status, 0) + 1
            results.append(
                ViewResult(
                    case=case.case,
                    start=start,
                    view=view,
                    ownership=analyze_range(stakes, start, entity_types, case.publicly_traded),
                    control=control_reach(stakes, start),
                    control_without_equity=control_without_equity(stakes, start),
                    statuses=statuses,
                )
            )
    return results


def _pct(span: tuple[float, float]) -> str:
    lo, hi = span
    return f"{lo:.1%}" if abs(hi - lo) < 5e-4 else f"{lo:.1%}–{hi:.1%}"


def _num(span: tuple[float, float], fmt: str = ".2f") -> str:
    lo, hi = (0 if abs(v) < 5e-4 else v for v in span)  # avoid "-0.00"
    return f"{lo:{fmt}}" if abs(hi - lo) < 5e-4 else f"{lo:{fmt}}–{hi:{fmt}}"


def _hops(found: dict[str, int]) -> str:
    return "; ".join(f"{p} ({h})" for p, h in sorted(found.items(), key=lambda x: x[1])) or "—"


def report(graphs_dir: Path = DEFAULT_DIR, cases: list[str] | None = None) -> str:
    """Markdown results for each case, start licensee and view."""
    out = [
        "# Development-case results",
        "",
        "Generated by `python -m teleownermap.ground_truth` from `ground_truth/graphs/`. "
        "Shares and entropy are lower–upper bounds over all share ranges. Control lists "
        "give the hop count in parentheses.",
        "",
    ]
    for case in load_cases(graphs_dir):
        if cases is not None and case.case not in cases:
            continue
        links = load_links(graphs_dir / f"{case.case}.csv")
        out += [f"## {case.case}", "", f"Snapshot {case.snapshot} ({case.snapshot_basis}).", ""]
        for r in analyze_case(case, links):
            o = r.ownership
            out += [
                f"### {r.start} — {r.view}",
                "",
                "| Metric | Value |",
                "|---|---|",
                f"| Link statuses used | "
                f"{', '.join(f'{k} {v}' for k, v in sorted(r.statuses.items())) or '—'} |",
                f"| Unknown owner share | {_pct(o.unknown_share)} |",
                f"| Public shareholders share | {_pct(o.public_share)} |",
                f"| Entropy, all endpoints (bits) | {_num(o.entropy_bits)} |",
                f"| Anonymity set size (known owners) | {_num(o.anonymity_set_size, 'd')} |",
                f"| Expected hops | {_num(o.expected_hops)} |",
                f"| Control reach | {_hops(r.control)} |",
                f"| Control without equity | {_hops(r.control_without_equity)} |",
                "",
                "| Endpoint | Probability |",
                "|---|---|",
                *(f"| {p} | {_pct(span)} |" for p, span in o.probabilities.items()),
                "",
            ]
            if o.discrepancies:
                out += ["Notes:", "", *(f"- {d}" for d in o.discrepancies), ""]
    return "\n".join(out)


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[2] / "results" / "dev_cases.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text(report())
    print(f"Wrote {target}")
