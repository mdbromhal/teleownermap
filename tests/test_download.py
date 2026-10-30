"""Tests for snapshot downloads, against a local HTTP server."""

import hashlib
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from teleownermap.ingest import download
from teleownermap.ingest.download import BlockedError, fetch, register
from teleownermap.schema import connect

BODY = b"HD|1|example\n"


class Handler(BaseHTTPRequestHandler):
    seen: list[tuple[str, str, str]] = []

    def _reply(self, with_body):
        Handler.seen.append((self.command, self.path, self.headers["User-Agent"]))
        if self.path.startswith("/blocked"):
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Last-Modified", "Sun, 25 Oct 2026 13:04:15 GMT")
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        if with_body:
            self.wfile.write(BODY)

    def do_GET(self):
        self._reply(True)

    def do_HEAD(self):
        self._reply(False)

    def log_message(self, *args):
        pass


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setattr(download, "DELAY_S", 0.0)
    Handler.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


@pytest.fixture(params=["urllib", "curl"])
def client(request):
    if request.param == "curl" and shutil.which("curl") is None:
        pytest.skip("curl not installed")
    return request.param


def get(base, tmp_path, path="/owner.zip", client="urllib"):
    return fetch(
        base + path,
        name="owner",
        source_type="fcc_uls_bulk",
        publisher="FCC",
        license="public domain",
        data_dir=tmp_path,
        client=client,
    )


def test_saves_fingerprinted_snapshot_labeled_by_publisher_date(server, tmp_path, client):
    d = get(server, tmp_path, client=client)
    assert d.snapshot_label == "2026-10-25"
    assert d.local_path == tmp_path / "snapshots/fcc_uls_bulk/2026-10-25/owner.zip"
    assert d.local_path.read_bytes() == BODY
    assert d.sha256 == hashlib.sha256(BODY).hexdigest()
    assert all(ua == download.USER_AGENT for _, _, ua in Handler.seen)


def test_existing_edition_is_not_downloaded_again(server, tmp_path):
    first = get(server, tmp_path)
    Handler.seen = []
    assert get(server, tmp_path) == first
    assert [m for m, _, _ in Handler.seen] == ["HEAD"]


def test_refusal_stops_the_download(server, tmp_path, client):
    with pytest.raises(BlockedError):
        get(server, tmp_path, "/blocked.zip", client=client)
    assert len(Handler.seen) == 1


def test_registered_once_in_sources(server, tmp_path):
    con = connect()
    d = get(server, tmp_path)
    register(con, [d])
    register(con, [d])
    assert con.execute("SELECT source_id, sha256 FROM sources").fetchall() == [
        ("fcc_uls_bulk/2026-10-25/owner", d.sha256)
    ]
