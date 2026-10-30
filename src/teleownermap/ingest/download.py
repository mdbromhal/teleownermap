"""Download bulk source files as dated snapshots (see docs/decisions.md).

Every file is kept unaltered under `data/snapshots/<source>/<label>/`, fingerprinted with
SHA-256 and registered as a `sources` row. The snapshot label is the publisher's date for
the file (FCC: the server's Last-Modified date; GLEIF: the golden copy's publish date), so
everyone who downloads the same edition gets the same label.

Requests identify the tool honestly and are spaced at least `DELAY_S` apart. Any refusal
(HTTP 403/429) stops the download; we never disguise the client to get around a block.

Run `python -m teleownermap.ingest.download fcc|gleif [--data-dir DIR]`.
"""

from __future__ import annotations

import argparse
import email
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import duckdb

USER_AGENT = "teleownermap"
DELAY_S = 1.0
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data"

FCC_BASE = "https://data.fcc.gov/download/pub/uls/complete/"
# owner.zip holds Form 602 and Form 175; l_* are licenses, a_* applications.
FCC_FILES = (
    "owner",
    "l_market",
    "a_market",
    "l_cell",
    "a_cell",
    "l_paging",
    "a_paging",
    "l_coast",
    "a_coast",
    "a_aatc",  # assignments and transfers of control, all services
)
GLEIF_LATEST = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest"
GLEIF_FILES = ("lei2", "rr", "repex")


class BlockedError(RuntimeError):
    """The server refused us. Stop rather than retry or disguise the request."""


@dataclass(frozen=True)
class Downloaded:
    source_id: str
    source_type: str
    publisher: str
    title: str
    url: str
    retrieved_at: datetime
    sha256: str
    license: str
    snapshot_label: str
    local_path: Path


_last_request = 0.0


def _open(url: str, method: str = "GET", client: str = "urllib"):
    """Send one request with the honest label. `client` is "urllib" (Python) or "curl".

    FCC's bulk server began refusing Python's requests on 2026-10-29 while accepting curl
    with the same label, so FCC downloads use curl (docs/decisions.md). Either way the
    label is the same and any refusal stops the download.
    """
    global _last_request
    wait = _last_request + DELAY_S - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    if client == "curl":
        return _CurlResponse(url, method)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method=method)
    try:
        return urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise BlockedError(f"{url} refused the request (HTTP {e.code}); stopping") from e
        raise


class _CurlResponse:
    """Run curl into a temporary file and expose `.headers` and `.read()` like urllib."""

    def __init__(self, url: str, method: str):
        if shutil.which("curl") is None:
            raise RuntimeError("curl is not installed; see the setup guide")
        self._dir = tempfile.TemporaryDirectory()
        head, body = Path(self._dir.name, "headers"), Path(self._dir.name, "body")
        cmd = ["curl", "--silent", "--show-error", "--location", "--max-time", "3600",
               "--user-agent", USER_AGENT, "--dump-header", str(head), "--output", str(body),
               "--write-out", "%{http_code}"]  # fmt: skip
        if method == "HEAD":
            cmd.append("--head")
        done = subprocess.run([*cmd, url], capture_output=True, text=True, check=False)
        if done.returncode != 0:
            self.close()
            raise RuntimeError(f"curl failed for {url}: {done.stderr.strip()}")
        status = int(done.stdout.strip() or 0)
        if status in (403, 429):
            self.close()
            raise BlockedError(f"{url} refused the request (HTTP {status}); stopping")
        if status >= 400:
            self.close()
            raise RuntimeError(f"{url} returned HTTP {status}")
        # With redirects, curl writes one header block per response; keep the last.
        blocks = head.read_text(encoding="latin-1").replace("\r\n", "\n").strip().split("\n\n")
        self.headers = email.message_from_string(blocks[-1].split("\n", 1)[-1])
        self._body = body.open("rb") if body.exists() else io.BytesIO()

    def read(self, n: int = -1) -> bytes:
        return self._body.read(n)

    def close(self) -> None:
        if getattr(self, "_body", None):
            self._body.close()
        self._dir.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _save(resp, dest: Path) -> str:
    """Stream a response to `dest` (via a temporary file) and return its SHA-256."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    digest = hashlib.sha256()
    with tmp.open("wb") as f:
        while chunk := resp.read(1 << 20):
            digest.update(chunk)
            f.write(chunk)
    tmp.replace(dest)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(
    url: str,
    *,
    name: str,
    source_type: str,
    publisher: str,
    license: str,
    data_dir: Path,
    label: str | None = None,
    client: str = "urllib",
) -> Downloaded:
    """Download `url` into its snapshot folder unless that edition is already there.

    Without `label`, the label is the Last-Modified date the server reports.
    """
    filename = url.rsplit("/", 1)[-1]
    folder = data_dir / "snapshots" / source_type
    from_headers = label is None
    if from_headers:
        with _open(url, method="HEAD", client=client) as head:
            label = _label_from_headers(head.headers.get("Last-Modified"))
    if saved := _load_meta(folder / label / filename):
        return saved
    with _open(url, client=client) as resp:
        retrieved_at = datetime.now(UTC)
        if from_headers:
            # The file may have been republished between the HEAD and the GET.
            label = _label_from_headers(resp.headers.get("Last-Modified"))
        dest = folder / label / filename
        digest = _save(resp, dest)
    meta = dest.with_name(filename + ".json")
    got = Downloaded(
        source_id=f"{source_type}/{label}/{name}",
        source_type=source_type,
        publisher=publisher,
        title=filename,
        url=url,
        retrieved_at=retrieved_at,
        sha256=digest,
        license=license,
        snapshot_label=label,
        local_path=dest,
    )
    record = {**got.__dict__, "retrieved_at": retrieved_at.isoformat(), "local_path": str(dest)}
    meta.write_text(json.dumps(record, indent=2))
    return got


def _load_meta(dest: Path) -> Downloaded | None:
    meta = dest.with_name(dest.name + ".json")
    if not (dest.exists() and meta.exists()):
        return None
    saved = json.loads(meta.read_text())
    saved["retrieved_at"] = datetime.fromisoformat(saved["retrieved_at"])
    saved["local_path"] = Path(saved["local_path"])
    return Downloaded(**saved)


def _label_from_headers(last_modified: str | None) -> str:
    if not last_modified:
        raise ValueError("server gave no Last-Modified date; can't label the snapshot")
    return parsedate_to_datetime(last_modified).astimezone(UTC).date().isoformat()


def download_fcc(data_dir: Path = DEFAULT_DATA_DIR) -> list[Downloaded]:
    return [
        fetch(
            FCC_BASE + f"{name}.zip",
            name=name,
            source_type="fcc_uls_bulk",
            client="curl",
            publisher="Federal Communications Commission",
            license="US government work (public domain)",
            data_dir=data_dir,
        )
        for name in FCC_FILES
    ]


def download_gleif(data_dir: Path = DEFAULT_DATA_DIR) -> list[Downloaded]:
    with _open(GLEIF_LATEST) as resp:
        latest = json.load(resp)["data"]
    label = latest["publish_date"][:10]
    return [
        fetch(
            latest[name]["full_file"]["csv"]["url"],
            name=name,
            source_type="gleif_golden_copy",
            publisher="Global Legal Entity Identifier Foundation",
            license="CC0 1.0",
            data_dir=data_dir,
            label=label,
        )
        for name in GLEIF_FILES
    ]


def register(con: duckdb.DuckDBPyConnection, files: list[Downloaded]) -> None:
    """Add each file to `sources` (once)."""
    for d in files:
        con.execute(
            "INSERT INTO sources (source_id, source_type, publisher, title, url, retrieved_at,"
            " sha256, license, snapshot_label, local_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT DO NOTHING",
            [
                d.source_id,
                d.source_type,
                d.publisher,
                d.title,
                d.url,
                d.retrieved_at,
                d.sha256,
                d.license,
                d.snapshot_label,
                str(d.local_path),
            ],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", choices=("fcc", "gleif"))
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(args.data_dir).free < 10 * 2**30:
        print("warning: less than 10 GB free; GLEIF unzips to several GB")
    files = (download_fcc if args.source == "fcc" else download_gleif)(args.data_dir)
    for d in files:
        print(f"{d.snapshot_label}  {d.sha256[:12]}  {d.local_path}")


if __name__ == "__main__":
    main()
