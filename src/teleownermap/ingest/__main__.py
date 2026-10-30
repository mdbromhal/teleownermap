"""Download the newest bulk files and load them into the local database.

    python -m teleownermap.ingest fcc [--db data/teleownermap.duckdb] [--low-memory]
                                      [--no-download]

Needs about 8 GB of RAM (`--low-memory`: about 4 GB, slower) and about 20 GB of free disk.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from teleownermap.ingest import fcc_owner, fcc_uls
from teleownermap.ingest._bulk import BATCH_ROWS, LOW_MEMORY_BATCH_ROWS
from teleownermap.ingest.download import (
    DEFAULT_DATA_DIR,
    FCC_BASE,
    FCC_FILES,
    _load_meta,
    download_fcc,
    register,
)
from teleownermap.ingest.hashing import load_or_create_key
from teleownermap.schema import connect

# License files first: their entity types come from FCC's documented Applicant Type Code,
# and the first source to describe an FRN sets its entity type.
LOAD_ORDER = ("l_market", "l_cell", "l_paging", "l_coast", "a_market", "a_cell", "a_paging",
              "a_coast", "a_aatc", "owner")  # fmt: skip


def _latest_downloads(data_dir: Path):
    folder = data_dir / "snapshots" / "fcc_uls_bulk"
    found = []
    for name in FCC_FILES:
        editions = sorted(folder.glob(f"*/{name}.zip"))
        if not editions:
            raise FileNotFoundError(f"no download of {name}.zip; see {FCC_BASE}")
        found.append(_load_meta(editions[-1]))
    return found


def ingest_fcc(db: Path, data_dir: Path, *, low_memory: bool, download: bool) -> None:
    files = download_fcc(data_dir) if download else _latest_downloads(data_dir)
    by_name = {Path(d.local_path).stem: d for d in files}
    con = connect(db, low_memory=low_memory)
    register(con, files)
    key = load_or_create_key()
    batch = LOW_MEMORY_BATCH_ROWS if low_memory else BATCH_ROWS
    for name in LOAD_ORDER:
        d = by_name[name]
        start = time.monotonic()
        if name == "owner":
            report = fcc_owner.load(con, d.local_path, d.source_id, key)
        else:
            report = fcc_uls.load(con, d.local_path, d.source_id, key, batch_rows=batch)
        rows = sum(report.rows.values())
        note = f", {len(report.malformed)} malformed rows skipped" if report.malformed else ""
        print(f"{d.source_id}: {rows} rows in {time.monotonic() - start:.0f} s{note}")
    con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", choices=("fcc",))
    parser.add_argument("--db", type=Path, default=DEFAULT_DATA_DIR / "teleownermap.duckdb")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--low-memory", action="store_true", help="for 4 GB machines; slower")
    parser.add_argument("--no-download", action="store_true", help="use the newest downloads")
    args = parser.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    ingest_fcc(args.db, args.data_dir, low_memory=args.low_memory, download=not args.no_download)


if __name__ == "__main__":
    main()
