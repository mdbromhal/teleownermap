"""Database schema. Mirrors docs/data_model.md; keep the two in sync."""

from pathlib import Path

import duckdb

DATE_PRECISIONS = ("day", "month", "year")
END_STATUSES = ("ended", "ongoing", "unknown")
ENTITY_TYPES = ("company", "person", "government", "unknown_owner", "unclassified")
GRAPHS = ("equity", "control", "nominee", "none")
BASES = ("documented", "inferred")
ASSERTION_STATUSES = ("stated", "alleged", "admitted", "settled_finding", "found")
REVIEW_STATUSES = ("confirmed", "rejected", "unsure")


def _in(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


DDL = f"""
-- Provenance ---------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sources (
    source_id      VARCHAR PRIMARY KEY,
    source_type    VARCHAR NOT NULL,
    publisher      VARCHAR,
    title          VARCHAR,
    url            VARCHAR,
    retrieved_at   TIMESTAMP NOT NULL,
    sha256         VARCHAR NOT NULL,
    license        VARCHAR,
    snapshot_label VARCHAR,
    local_path     VARCHAR,
    pinned         BOOLEAN NOT NULL DEFAULT FALSE
);

-- Raw extracted rows/passages. Never edited. Sensitive values are never stored here.
CREATE TABLE IF NOT EXISTS records (
    record_id      VARCHAR PRIMARY KEY,
    source_id      VARCHAR NOT NULL REFERENCES sources (source_id),
    locator        VARCHAR NOT NULL,
    raw            JSON,
    parser_version VARCHAR NOT NULL
);

-- What sources say -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS entities (
    entity_id        VARCHAR PRIMARY KEY,
    entity_type      VARCHAR NOT NULL CHECK (entity_type IN {_in(ENTITY_TYPES)}),
    labels           VARCHAR[],
    unknown_owner_of VARCHAR REFERENCES entities (entity_id),
    CHECK ((entity_type = 'unknown_owner') = (unknown_owner_of IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS entity_records (
    entity_id VARCHAR NOT NULL REFERENCES entities (entity_id),
    record_id VARCHAR NOT NULL REFERENCES records (record_id),
    PRIMARY KEY (entity_id, record_id)
);

CREATE TABLE IF NOT EXISTS identifiers (
    entity_id     VARCHAR NOT NULL REFERENCES entities (entity_id),
    scheme        VARCHAR NOT NULL,
    value         VARCHAR NOT NULL,
    record_id     VARCHAR NOT NULL REFERENCES records (record_id),
    conflict_flag BOOLEAN NOT NULL DEFAULT FALSE
);

-- One row per statement; disagreeing sources produce multiple rows.
-- Sensitive fields: value is NULL and only keyed hashes are kept.
CREATE TABLE IF NOT EXISTS attributes (
    attribute_id         VARCHAR PRIMARY KEY,
    entity_id            VARCHAR NOT NULL REFERENCES entities (entity_id),
    name                 VARCHAR NOT NULL,
    value                VARCHAR,
    is_sensitive         BOOLEAN NOT NULL DEFAULT FALSE,
    hmac_full            VARCHAR,
    hmac_zip             VARCHAR,
    hmac_city            VARCHAR,
    valid_from           DATE,
    valid_from_precision VARCHAR CHECK (valid_from_precision IN {_in(DATE_PRECISIONS)}),
    valid_to             DATE,
    valid_to_precision   VARCHAR CHECK (valid_to_precision IN {_in(DATE_PRECISIONS)}),
    valid_to_status      VARCHAR CHECK (valid_to_status IN {_in(END_STATUSES)}),
    record_id            VARCHAR NOT NULL REFERENCES records (record_id),
    CHECK (NOT is_sensitive OR value IS NULL)
);

CREATE TABLE IF NOT EXISTS licenses (
    license_id    VARCHAR PRIMARY KEY,
    call_sign     VARCHAR,
    radio_service VARCHAR,
    market        VARCHAR,
    grant_date    DATE,
    expiry_date   DATE,
    effective_date    DATE,
    cancellation_date DATE,
    status        VARCHAR,
    auction_id    VARCHAR,
    record_id     VARCHAR NOT NULL REFERENCES records (record_id)
);

-- Transmitter sites. An individual licensee's site may be their home, so its address,
-- city, county and coordinates are then kept only as keyed hashes.
CREATE TABLE IF NOT EXISTS license_sites (
    site_id      VARCHAR PRIMARY KEY,
    license_id   VARCHAR NOT NULL REFERENCES licenses (license_id),
    address      VARCHAR,
    city         VARCHAR,
    county       VARCHAR,
    state        VARCHAR,
    latitude     DOUBLE,
    longitude    DOUBLE,
    tower_registration VARCHAR,
    is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    hmac_coords  VARCHAR,
    hmac_address VARCHAR,
    record_id    VARCHAR NOT NULL REFERENCES records (record_id),
    CHECK (NOT is_sensitive OR (address IS NULL AND city IS NULL AND county IS NULL
                                AND latitude IS NULL AND longitude IS NULL))
);

-- One row per source statement; ranges across sources are computed, not stored.
CREATE TABLE IF NOT EXISTS relationships (
    rel_id              VARCHAR PRIMARY KEY,
    interested_party_id VARCHAR NOT NULL REFERENCES entities (entity_id),
    subject_entity_id   VARCHAR REFERENCES entities (entity_id),
    subject_license_id  VARCHAR REFERENCES licenses (license_id),
    interest_type       VARCHAR NOT NULL,
    graph               VARCHAR NOT NULL CHECK (graph IN {_in(GRAPHS)}),
    title_as_written    VARCHAR,
    role_class          VARCHAR,
    share_min           DOUBLE CHECK (share_min BETWEEN 0 AND 1),
    share_max           DOUBLE CHECK (share_max BETWEEN 0 AND 1),
    start_date          DATE,
    start_precision     VARCHAR CHECK (start_precision IN {_in(DATE_PRECISIONS)}),
    end_date            DATE,
    end_precision       VARCHAR CHECK (end_precision IN {_in(DATE_PRECISIONS)}),
    end_status          VARCHAR CHECK (end_status IN {_in(END_STATUSES)}),
    filing_date         DATE,
    effective_date      DATE,
    basis               VARCHAR NOT NULL CHECK (basis IN {_in(BASES)}),
    assertion_status    VARCHAR NOT NULL CHECK (assertion_status IN {_in(ASSERTION_STATUSES)}),
    labels              VARCHAR[],
    record_id           VARCHAR REFERENCES records (record_id),
    CHECK ((subject_entity_id IS NULL) <> (subject_license_id IS NULL)),
    CHECK (share_min IS NULL OR share_max IS NULL OR share_min <= share_max),
    CHECK (basis = 'inferred' OR record_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS events (
    event_id   VARCHAR PRIMARY KEY,
    entity_id  VARCHAR REFERENCES entities (entity_id),
    license_id VARCHAR REFERENCES licenses (license_id),
    event_type VARCHAR NOT NULL,
    date       DATE NOT NULL,
    precision  VARCHAR NOT NULL CHECK (precision IN {_in(DATE_PRECISIONS)}),
    record_id  VARCHAR NOT NULL REFERENCES records (record_id),
    CHECK ((entity_id IS NULL) <> (license_id IS NULL))
);

-- Exhibit PDFs the user downloaded and imported, tied to the Form 602/175 attachment
-- record (T) that lists them. Each page's extracted text is a `records` row of the PDF's
-- source. Exhibit text is shown in full but left out of exports by default.
CREATE TABLE IF NOT EXISTS exhibit_files (
    exhibit_record_id  VARCHAR NOT NULL REFERENCES records (record_id),
    source_id          VARCHAR NOT NULL REFERENCES sources (source_id),
    pages              INTEGER NOT NULL,
    pages_without_text INTEGER NOT NULL,
    imported_at        TIMESTAMP NOT NULL,
    PRIMARY KEY (exhibit_record_id, source_id)
);

-- GLEIF staging: the whole golden copy, one row per CSV row, searchable. Only companies
-- connected to an FCC entity are promoted into the statement tables (docs/decisions.md).
-- A sole proprietor's street, city and postal code are kept only as keyed hashes.

CREATE TABLE IF NOT EXISTS gleif_entities (
    source_id          VARCHAR NOT NULL REFERENCES sources (source_id),
    lei                VARCHAR NOT NULL,
    line               INTEGER NOT NULL,
    legal_name         VARCHAR,
    other_names        VARCHAR[],
    legal_address      VARCHAR,
    legal_city         VARCHAR,
    legal_region       VARCHAR,
    legal_country      VARCHAR,
    legal_postal_code  VARCHAR,
    hq_address         VARCHAR,
    hq_city            VARCHAR,
    hq_region          VARCHAR,
    hq_country         VARCHAR,
    hq_postal_code     VARCHAR,
    legal_hmac_full    VARCHAR,
    legal_hmac_zip     VARCHAR,
    legal_hmac_city    VARCHAR,
    hq_hmac_full       VARCHAR,
    hq_hmac_zip        VARCHAR,
    hq_hmac_city       VARCHAR,
    jurisdiction       VARCHAR,
    category           VARCHAR,
    subcategory        VARCHAR,
    legal_form_code    VARCHAR,
    other_legal_form   VARCHAR,
    entity_status      VARCHAR,
    creation_date      DATE,
    registration_status VARCHAR,
    initial_registration_date DATE,
    last_update_date   DATE,
    next_renewal_date  DATE,
    managing_lou       VARCHAR,
    successor_leis     VARCHAR[],
    legal_entity_events JSON,
    is_sensitive       BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (source_id, lei),
    CHECK (NOT is_sensitive OR (legal_address IS NULL AND legal_city IS NULL
           AND legal_postal_code IS NULL AND hq_address IS NULL AND hq_city IS NULL
           AND hq_postal_code IS NULL))
);

CREATE TABLE IF NOT EXISTS gleif_relationships (
    source_id          VARCHAR NOT NULL REFERENCES sources (source_id),
    line               INTEGER NOT NULL,
    child_lei          VARCHAR NOT NULL,
    parent_id          VARCHAR NOT NULL,
    parent_id_type     VARCHAR,
    relationship_type  VARCHAR NOT NULL,
    relationship_status VARCHAR,
    periods            JSON,
    measurement_method VARCHAR,
    percentage         DOUBLE,
    accounting_standard VARCHAR,
    registration_status VARCHAR,
    initial_registration_date DATE,
    last_update_date   DATE,
    PRIMARY KEY (source_id, line)
);

CREATE TABLE IF NOT EXISTS gleif_exceptions (
    source_id  VARCHAR NOT NULL REFERENCES sources (source_id),
    line       INTEGER NOT NULL,
    lei        VARCHAR NOT NULL,
    category   VARCHAR NOT NULL,
    reasons    VARCHAR[],
    refs       VARCHAR[],
    PRIMARY KEY (source_id, line)
);

-- Computed on top (rebuildable) ---------------------------------------------------

CREATE TABLE IF NOT EXISTS match_links (
    match_id      VARCHAR PRIMARY KEY,
    entity_a      VARCHAR NOT NULL REFERENCES entities (entity_id),
    entity_b      VARCHAR NOT NULL REFERENCES entities (entity_id),
    model_version VARCHAR NOT NULL,
    score         DOUBLE NOT NULL,
    rank          INTEGER,
    CHECK (entity_a <> entity_b)
);

CREATE TABLE IF NOT EXISTS match_evidence (
    match_id   VARCHAR NOT NULL REFERENCES match_links (match_id),
    comparison VARCHAR NOT NULL,
    weight     DOUBLE NOT NULL,
    record_ids VARCHAR[]
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id VARCHAR PRIMARY KEY,
    rel_id      VARCHAR REFERENCES relationships (rel_id),
    match_id    VARCHAR REFERENCES match_links (match_id),
    kind        VARCHAR NOT NULL,
    detail      VARCHAR,
    commonness  INTEGER,
    record_ids  VARCHAR[],
    CHECK ((rel_id IS NULL) <> (match_id IS NULL))
);

-- The only user activity stored: deliberate decisions. Append-only.
CREATE TABLE IF NOT EXISTS reviews (
    review_id   VARCHAR PRIMARY KEY,
    target_type VARCHAR NOT NULL CHECK (target_type IN ('match', 'relationship')),
    target_id   VARCHAR NOT NULL,
    status      VARCHAR NOT NULL CHECK (status IN {_in(REVIEW_STATUSES)}),
    note        VARCHAR,
    created_at  TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id          VARCHAR PRIMARY KEY,
    code_version    VARCHAR NOT NULL,
    snapshot_labels VARCHAR[],
    parameters      JSON,
    created_at      TIMESTAMP NOT NULL
);
"""


# Resource caps so loading fits an 8 GB laptop (docs/decisions.md). DuckDB otherwise takes
# up to 80% of RAM and one thread per core.
MEMORY_LIMIT = "1GB"
LOW_MEMORY_LIMIT = "500MB"
THREADS = 4


def connect(
    path: str | Path = ":memory:", *, low_memory: bool = False
) -> duckdb.DuckDBPyConnection:
    """Open a database, cap its memory and threads, and create any missing tables."""
    con = duckdb.connect(str(path))
    con.execute(f"SET memory_limit = '{LOW_MEMORY_LIMIT if low_memory else MEMORY_LIMIT}'")
    con.execute(f"SET threads = {THREADS}")
    con.execute(DDL)
    return con
