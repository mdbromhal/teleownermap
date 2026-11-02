"""Tests for listing and importing Form 602 exhibits."""

import zipfile

import pymupdf
import pytest

from teleownermap import exhibits
from teleownermap.ingest import fcc_owner
from teleownermap.ingest.fcc_owner import COLUMNS
from teleownermap.schema import connect

USI = "2572134"


def line(rtype, **values):
    fields = {"record_type": rtype, "form_num": "602", "filing_type": "C", "filing_status": "1",
              "unique_system_identifier": USI, "file_num": "0002081616", **values}  # fmt: skip
    return "|".join(fields.get(c, "") for c in COLUMNS[rtype])


@pytest.fixture
def con(tmp_path):
    path = tmp_path / "owner.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("_O.dat", line("O", frn_filer="0004122032", filer_name="AT&T Wireless"))
        zf.writestr(
            "_T.dat",
            "\r\n".join(
                [
                    line(
                        "T",
                        attachment_code="O",
                        attachment_desc="05/17/2002 OWNERSHIP FILING",
                        attachment_date="08/19/2003",
                    ),
                    line(
                        "T",
                        attachment_code="I",
                        attachment_desc="Ex. A: Description of Indirect Ownership Interests",
                        attachment_date="09/30/2002",
                    ),
                    line(
                        "T",
                        attachment_code="O",
                        attachment_desc="Waiver request",
                        attachment_date="09/30/2002",
                    ),
                ]  # fmt: skip
            ),
        )
    con = connect()
    con.execute(
        "INSERT INTO sources (source_id, source_type, title, retrieved_at, sha256, "
        "snapshot_label) VALUES ('s', 'fcc_uls_bulk', 'owner.zip', now(), 'x', '2026-10-25')"
    )
    fcc_owner.load(con, path, "s", b"k" * 32)
    return con


def make_pdf(path, pages):
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    doc.save(path)
    return path


def test_list_puts_ownership_exhibits_first_and_finds_by_frn(con):
    by_file = exhibits.list_exhibits(con, "0002081616")
    assert [e.title for e in by_file][0] == "Ex. A: Description of Indirect Ownership Interests"
    assert by_file[-1].title == "Waiver request" and not by_file[-1].ownership_related
    assert [e.title for e in exhibits.list_exhibits(con, "0004122032")] == [
        e.title for e in by_file
    ]
    assert all(not e.read for e in by_file)
    assert "applId=2572134" in by_file[0].filing_url


def test_instructions_include_privacy_warning_and_add_command(con):
    ex = exhibits.list_exhibits(con, "0002081616")[0]
    text = exhibits.instructions(ex, "0002081616")
    assert text.startswith(exhibits.LIVE_LOOKUP_WARNING)
    assert "exhibits add 0002081616 1 <saved file>" in text


def test_add_extracts_text_counts_blank_pages_and_marks_read(con, tmp_path):
    ex = exhibits.list_exhibits(con, "0002081616")[0]
    pdf = make_pdf(tmp_path / "attachmentViewRD", ["DCM Capital USA (UK) Limited holds 16%", ""])
    pages, blank = exhibits.add_exhibit(con, ex, pdf, data_dir=tmp_path)
    assert (pages, blank) == (2, 1)
    [(text,)] = con.execute(
        "SELECT json_extract_string(raw, 'text') FROM records WHERE locator = 'page 1' "
        "AND source_id LIKE 'fcc_exhibit/%'"
    ).fetchall()
    assert "DCM Capital" in text
    assert exhibits.list_exhibits(con, "0002081616")[0].read
    copies = list((tmp_path / "fcc_exhibits" / "0002081616").glob("*.pdf"))
    assert len(copies) == 1


def test_add_twice_is_harmless(con, tmp_path):
    ex = exhibits.list_exhibits(con, "0002081616")[0]
    pdf = make_pdf(tmp_path / "a.pdf", ["text"])
    exhibits.add_exhibit(con, ex, pdf, data_dir=tmp_path)
    exhibits.add_exhibit(con, ex, pdf, data_dir=tmp_path)
    assert con.execute("SELECT count(*) FROM exhibit_files").fetchone()[0] == 1


def test_non_pdf_is_rejected(con, tmp_path):
    ex = exhibits.list_exhibits(con, "0002081616")[0]
    page = tmp_path / "attachmentViewRD"
    page.write_text("<html>Access Denied</html>")
    with pytest.raises(ValueError, match="not a PDF"):
        exhibits.add_exhibit(con, ex, page, data_dir=tmp_path)
