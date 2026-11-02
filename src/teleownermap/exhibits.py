"""Form 602/175 exhibits: guide the user to download them, then import their text.

FCC's bulk ownership file lists every exhibit (title, date, filing) but doesn't contain the
PDFs, and FCC's firewall refuses automated downloads, so the user downloads each exhibit in
their own browser (docs/decisions.md). This module:
- lists a filing's exhibits, ownership-related ones first, each marked read or unread, with
  step-by-step download instructions and a direct link to the ULS filing page;
- imports a downloaded file for one specific exhibit (ULS saves every attachment under a
  generic name, so the user picks the exhibit), fingerprints it, keeps an unaltered copy and
  extracts each page's text with PyMuPDF (no AI). Pages with no text layer (likely scans)
  are counted, not OCR'd.

    python -m teleownermap.exhibits list <file number or FRN>
    python -m teleownermap.exhibits add <file number or FRN> <number from list> <file>
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb
import pymupdf

from teleownermap.ingest.download import DEFAULT_DATA_DIR, sha256_file
from teleownermap.schema import connect

PARSER_VERSION = "exhibit_pymupdf/1"
ULS_FILING = (
    "https://wireless2.fcc.gov/ownerQryDetail/ownership-search-results-detail.htm"
    "?applId={}&edittype=R/O&OwnershipSearch=Y&reqPage=1"
)
# Attachment codes and title words that suggest the exhibit describes ownership
# (FCC code list: I = Indirect Ownership, N = Ownership).
OWNERSHIP_CODES = ("I", "N")
OWNERSHIP_WORDS = re.compile(
    r"owner|interest|disclosable|organi[sz]ational|chart|shareholder|partner|member|control",
    re.I,
)
LIVE_LOOKUP_WARNING = (
    "Privacy note: opening this link makes your browser ask FCC's website about this specific "
    "filing, which leaves a record on FCC's servers."
)


@dataclass(frozen=True)
class Exhibit:
    number: int
    record_id: str
    file_num: str
    title: str | None
    filed: date | None
    attachment_code: str | None
    ownership_related: bool
    read: bool
    filing_url: str


def _date(value: str | None) -> date | None:
    try:
        return datetime.strptime(value, "%m/%d/%Y").date() if value else None
    except ValueError:
        return None


def list_exhibits(con: duckdb.DuckDBPyConnection, file_num_or_frn: str) -> list[Exhibit]:
    """Exhibits of the filing(s) with this file number, or filed by this FRN, from the
    newest ownership snapshot. Ownership-related exhibits come first."""
    rows = con.execute(
        """
        WITH latest AS (
            SELECT source_id FROM sources WHERE title = 'owner.zip'
            ORDER BY snapshot_label DESC LIMIT 1
        ),
        t AS (
            SELECT r.record_id, r.raw FROM records r JOIN latest USING (source_id)
            WHERE json_extract_string(r.raw, 'record_type') = 'T'
        ),
        filers AS (
            SELECT json_extract_string(r.raw, 'unique_system_identifier') AS usi,
                   json_extract_string(r.raw, 'frn_filer') AS frn
            FROM records r JOIN latest USING (source_id)
            WHERE json_extract_string(r.raw, 'record_type') = 'O'
        )
        SELECT t.record_id,
               json_extract_string(t.raw, 'file_num'),
               json_extract_string(t.raw, 'attachment_desc'),
               json_extract_string(t.raw, 'attachment_date'),
               json_extract_string(t.raw, 'attachment_code'),
               json_extract_string(t.raw, 'unique_system_identifier'),
               EXISTS (SELECT 1 FROM exhibit_files x WHERE x.exhibit_record_id = t.record_id)
        FROM t LEFT JOIN filers f
          ON f.usi = json_extract_string(t.raw, 'unique_system_identifier')
        WHERE json_extract_string(t.raw, 'file_num') = ? OR f.frn = ?
        """,
        [file_num_or_frn, file_num_or_frn],
    ).fetchall()
    exhibits = []
    for record_id, file_num, title, filed, code, usi, read in rows:
        related = code in OWNERSHIP_CODES or bool(OWNERSHIP_WORDS.search(title or ""))
        exhibits.append((record_id, file_num, title, _date(filed), code, related, read, usi))
    # Numbers must not change when an exhibit is read, so read status isn't a sort key.
    exhibits.sort(key=lambda e: (not e[5], e[3] or date.min, e[0]))
    return [
        Exhibit(i + 1, rid, fn, title, filed, code, related, read, ULS_FILING.format(usi))
        for i, (rid, fn, title, filed, code, related, read, usi) in enumerate(exhibits)
    ]


def instructions(exhibit: Exhibit, target: str) -> str:
    """Download steps; `target` is the file number or FRN the list was made with."""
    return "\n".join([
        LIVE_LOOKUP_WARNING,
        f"1. Open the filing: {exhibit.filing_url}",
        "2. Click \"View All Attachments\".",
        f"3. Click \"{exhibit.title}\" ({exhibit.filed}) and save the file.",
        f"4. Run: python -m teleownermap.exhibits add {target} {exhibit.number} <saved file>",
    ])  # fmt: skip


def add_exhibit(
    con: duckdb.DuckDBPyConnection,
    exhibit: Exhibit,
    path: Path,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> tuple[int, int]:
    """Import a downloaded exhibit. Returns (pages, pages without text)."""
    path = Path(path)
    with path.open("rb") as f:
        if f.read(5) != b"%PDF-":
            raise ValueError(f"{path} is not a PDF; ULS may have saved an error page instead")
    digest = sha256_file(path)
    dest = data_dir / "fcc_exhibits" / exhibit.file_num / f"{digest}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copyfile(path, dest)
    source_id = f"fcc_exhibit/{digest}"
    now = datetime.now(UTC)
    con.execute(
        "INSERT INTO sources (source_id, source_type, publisher, title, url, retrieved_at, "
        "sha256, license, local_path) VALUES (?, 'fcc_exhibit', 'Federal Communications "
        "Commission (filed by the licensee)', ?, ?, ?, ?, 'filed with FCC; public record', ?) "
        "ON CONFLICT DO NOTHING",
        [source_id, exhibit.title, exhibit.filing_url, now, digest, str(dest)],
    )
    pages, blank = 0, 0
    with pymupdf.open(dest) as doc:
        for page in doc:
            pages += 1
            text = page.get_text("text", sort=True).strip()
            blank += not text
            con.execute(
                "INSERT INTO records (record_id, source_id, locator, raw, parser_version) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                [f"{source_id}:page{page.number + 1}", source_id, f"page {page.number + 1}",
                 json.dumps({"text": text, "has_text_layer": bool(text)}), PARSER_VERSION],
            )  # fmt: skip
    con.execute(
        "INSERT INTO exhibit_files VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
        [exhibit.record_id, source_id, pages, blank, now],
    )
    return pages, blank


def _print_list(exhibits: list[Exhibit], target: str) -> None:
    if not exhibits:
        print("No exhibits listed for that filing or FRN in the newest ownership snapshot.")
        return
    unread = sum(not e.read for e in exhibits if e.ownership_related)
    print(f"{len(exhibits)} exhibits; {unread} ownership-related exhibits not yet read.\n")
    for e in exhibits:
        mark = "read  " if e.read else "UNREAD"
        flag = " [ownership]" if e.ownership_related else ""
        print(f"{e.number:3d}. {mark} {e.filed}  {e.title}{flag}  (file {e.file_num})")
    first = next((e for e in exhibits if not e.read), None)
    if first:
        print(f"\nTo read exhibit {first.number}:\n{instructions(first, target)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="List and import Form 602/175 exhibits.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DATA_DIR / "teleownermap.duckdb")
    sub = parser.add_subparsers(dest="command", required=True)
    ls = sub.add_parser("list", help="list a filing's exhibits")
    ls.add_argument("target", help="FCC file number or filer FRN")
    add = sub.add_parser("add", help="import a downloaded exhibit")
    add.add_argument("target", help="file number or FRN used with `list`")
    add.add_argument("number", type=int, help="exhibit number from `list`")
    add.add_argument("file", type=Path)
    args = parser.parse_args()
    con = connect(args.db)
    exhibits = list_exhibits(con, args.target)
    if args.command == "list":
        _print_list(exhibits, args.target)
        return
    exhibit = next((e for e in exhibits if e.number == args.number), None)
    if exhibit is None:
        raise SystemExit(f"no exhibit {args.number} for {args.target}; run `list` first")
    pages, blank = add_exhibit(con, exhibit, args.file)
    note = f"; {blank} pages have no text layer (likely scanned)" if blank else ""
    print(f'Imported "{exhibit.title}": {pages} pages{note}.')


if __name__ == "__main__":
    main()
