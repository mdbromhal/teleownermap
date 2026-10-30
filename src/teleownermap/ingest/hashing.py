"""Keyed hashes for addresses (see docs/decisions.md).

A person's street, address line 2, city and ZIP are never stored; only HMAC-SHA256 hashes
at three levels (full address, ZIP, city) are kept, so "same address as X" still works.
Addresses are standardized locally first, because hashes only match exactly. The key is
random per installation and lives outside `data/` and the database.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from pathlib import Path

KEY_ENV = "TELEOWNERMAP_HMAC_KEY_FILE"
DEFAULT_KEY_PATH = Path.home() / ".config" / "teleownermap" / "hmac.key"

# USPS Publication 28 abbreviations for common street suffixes, unit designators and
# directions. Applied word by word after punctuation is removed.
ABBREVIATIONS = {
    "ALLEY": "ALY",
    "APARTMENT": "APT",
    "AVENUE": "AVE",
    "BOULEVARD": "BLVD",
    "BUILDING": "BLDG",
    "CIRCLE": "CIR",
    "COURT": "CT",
    "DEPARTMENT": "DEPT",
    "DRIVE": "DR",
    "EXPRESSWAY": "EXPY",
    "FLOOR": "FL",
    "FREEWAY": "FWY",
    "HIGHWAY": "HWY",
    "LANE": "LN",
    "PARKWAY": "PKWY",
    "PLACE": "PL",
    "PLAZA": "PLZ",
    "ROAD": "RD",
    "ROOM": "RM",
    "SQUARE": "SQ",
    "STREET": "ST",
    "SUITE": "STE",
    "TERRACE": "TER",
    "TRAIL": "TRL",
    "NORTH": "N",
    "SOUTH": "S",
    "EAST": "E",
    "WEST": "W",
    "NORTHEAST": "NE",
    "NORTHWEST": "NW",
    "SOUTHEAST": "SE",
    "SOUTHWEST": "SW",
}
_PO_BOX = re.compile(r"\b(P O|POST OFFICE|PO) BOX\b")


def load_or_create_key(path: Path | None = None) -> bytes:
    """Read the installation's key, creating a random one (user-only permissions) if absent."""
    path = Path(os.environ.get(KEY_ENV, path or DEFAULT_KEY_PATH))
    if path.exists():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = os.urandom(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key


def standardize(text: str | None) -> str:
    """Uppercase, drop punctuation, collapse spaces, abbreviate per USPS."""
    if not text:
        return ""
    words = re.sub(r"[^A-Z0-9 ]", " ", text.upper()).split()
    out = " ".join(ABBREVIATIONS.get(w, w) for w in words)
    return _PO_BOX.sub("PO BOX", out)


def zip5(code: str | None) -> str:
    digits = re.sub(r"\D", "", code or "")
    return digits[:5] if len(digits) >= 5 else ""


def hash_value(key: bytes, kind: str, value: str | None) -> str | None:
    """Keyed hash of one standardized value (e.g. a phone number or coordinates)."""
    if not value:
        return None
    return hmac.new(key, f"{kind}|{value}".encode(), hashlib.sha256).hexdigest()


def standardize_phone(phone: str | None) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:] if len(digits) >= 10 else digits


@dataclass(frozen=True)
class AddressHashes:
    full: str | None
    zip: str | None
    city: str | None


def hash_address(
    key: bytes,
    *,
    street: str | None,
    street2: str | None,
    city: str | None,
    state: str | None,
    zip_code: str | None,
    country: str | None,
) -> AddressHashes:
    """Hash an address at three levels. A level whose parts are missing gets no hash, so a
    blank never matches another blank."""
    st, st2, ci = standardize(street), standardize(street2), standardize(city)
    sta, z = standardize(state), zip5(zip_code)
    co = standardize(country)
    if co in ("", "UNITED STATES", "USA", "UNITED STATES OF AMERICA"):
        co = "US"

    def h(level: str, *parts: str) -> str:
        msg = "|".join((level, *parts)).encode()
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    return AddressHashes(
        full=h("full", st, st2, ci, sta, z, co) if st and (ci or z) else None,
        zip=h("zip", z, co) if z else None,
        city=h("city", ci, sta, co) if ci else None,
    )
