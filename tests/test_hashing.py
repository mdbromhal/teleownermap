"""Tests for address standardization and keyed hashes."""

import stat

from teleownermap.ingest.hashing import hash_address, load_or_create_key, standardize

KEY = b"k" * 32


def addr(key=KEY, **kw):
    base = dict(street="611 Valley Club Drive", street2=None, city="Hailey", state="ID",
                zip_code="83333-1234", country="United States")  # fmt: skip
    return hash_address(key, **{**base, **kw})


def test_standardize_uses_usps_abbreviations():
    assert standardize("611 Valley Club Drive, Suite #200") == "611 VALLEY CLUB DR STE 200"
    assert standardize("P.O. Box 12") == "PO BOX 12"


def test_formatting_differences_still_match():
    assert addr() == addr(street="611 valley club dr.", zip_code="83333", country="")


def test_levels_match_independently():
    other_street = addr(street="1 Main St")
    assert other_street.full != addr().full
    assert other_street.zip == addr().zip and other_street.city == addr().city


def test_missing_parts_give_no_hash():
    h = addr(street=None, zip_code=None)
    assert h.full is None and h.zip is None and h.city is not None


def test_different_key_gives_different_hashes():
    assert addr(key=b"x" * 32).full != addr().full


def test_key_is_created_once_with_user_only_permissions(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEOWNERMAP_HMAC_KEY_FILE", raising=False)
    path = tmp_path / "cfg" / "hmac.key"
    key = load_or_create_key(path)
    assert len(key) == 32 and load_or_create_key(path) == key
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
