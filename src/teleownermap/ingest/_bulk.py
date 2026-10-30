"""Fast bulk inserts: row-by-row inserts run at ~2k rows/s, too slow for GLEIF's millions.

Rows go to temporary JSON-lines files that DuckDB reads in one INSERT, so every constraint
is checked exactly as with a normal INSERT. Columns no row mentions keep their defaults.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable
from datetime import date, datetime

import duckdb


def _default(value):
    if isinstance(value, date | datetime):
        return value.isoformat()
    raise TypeError(f"can't serialize {type(value).__name__}")


BATCH_ROWS = 50_000
LOW_MEMORY_BATCH_ROWS = 10_000  # ~40% slower; peak ~1.3 GB instead of ~1.6 GB on a_aatc


class TableSink:
    """Stream rows for several tables to temporary files, then insert them in a fixed order
    (parents before children), so large sources never sit in memory. Each table is split
    into batches of `batch_rows`, so DuckDB never reads one huge file at once."""

    def __init__(self, order: tuple[str, ...], batch_rows: int = BATCH_ROWS):
        self.order = order
        self.batch_rows = batch_rows
        self._files: dict[str, list[tuple[str, object, set[str]]]] = {}
        self.counts: dict[str, int] = {}

    def write(self, table: str, row: dict) -> None:
        if table not in self.order:
            raise KeyError(f"{table} is not in the insert order")
        n = self.counts.get(table, 0)
        if n % self.batch_rows == 0:
            fd, path = tempfile.mkstemp(suffix=f".{table}.jsonl")
            self._files.setdefault(table, []).append(
                (path, os.fdopen(fd, "w", encoding="utf-8"), set())
            )
        _, f, used = self._files[table][-1]
        f.write(json.dumps(row, default=_default) + "\n")
        used.update(row.keys())
        self.counts[table] = n + 1

    def insert(self, con: duckdb.DuckDBPyConnection, or_ignore: tuple[str, ...] = ()) -> None:
        """Insert everything written. `or_ignore` tables skip rows whose primary key already
        exists (e.g. an FRN seen in another file or snapshot)."""
        try:
            for table in self.order:
                for path, f, used in self._files.get(table, ()):
                    f.close()
                    _insert_file(con, table, path, used, table in or_ignore)
                    os.unlink(path)
        finally:
            self.close()

    def close(self) -> None:
        for batches in self._files.values():
            for path, f, _ in batches:
                f.close()
                if os.path.exists(path):
                    os.unlink(path)
        self._files.clear()


def _insert_file(con, table: str, path: str, used: set[str], or_ignore: bool) -> None:
    types = {name: typ for name, typ, *_ in con.execute(f"DESCRIBE {table}").fetchall()}
    unknown = used - types.keys()
    if unknown:
        raise KeyError(f"{table} has no column(s) {sorted(unknown)}")
    cols = ", ".join(c for c in types if c in used)
    spec = ", ".join(f"'{k}': '{v}'" for k, v in types.items() if k in used)
    verb = "INSERT OR IGNORE" if or_ignore else "INSERT"
    con.execute(
        f"{verb} INTO {table} ({cols}) SELECT {cols} FROM read_json(?, "
        f"format = 'newline_delimited', columns = {{{spec}}})",
        [path],
    )


def bulk_insert(
    con: duckdb.DuckDBPyConnection, table: str, rows: Iterable[dict], *, or_ignore: bool = False
) -> int:
    """Insert dicts (keys = column names; missing keys are NULL) in one statement."""
    sink = TableSink((table,))
    for row in rows:
        sink.write(table, row)
    sink.insert(con, (table,) if or_ignore else ())
    return sink.counts.get(table, 0)
