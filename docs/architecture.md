# Architecture and Software Engineering

**Status as of 2026-11-02.** Each item is marked **[built]** (in the repo, tested) or **[planned]** (decided in `docs/decisions.md`, not yet written). Data model details are in `docs/data_model.md`; the work log is `docs/methodology.md`.

## Overview
- `teleownermap` is an open-source Python package that treats a telecom ownership structure like an anonymity network: the FCC licensee is the exit node, shell companies are relays, and the ultimate owner is the entry node.
- It walks ownership upward from a licensee and measures how well the real owner is hidden, using anonymity metrics (owner probabilities, Shannon entropy, anonymity set size, hop distribution).
- Two delivery targets: a Python library for developers **[built, partial]** and a self-hosted web app for non-technical journalists **[planned for week 7, Nov 23–29]**.
- Design rule throughout: present evidence, don't conclude. The system never merges records, never invents precision, and every value traces back to a source.

## Pipeline (layers)
1. **Sources** **[built]**: download bulk files (FCC ULS license/application files, the Form 602/175 ownership file, the transfers file `a_aatc`, GLEIF's golden copy) as dated snapshots, keep unaltered local copies, and record URL, retrieval time, SHA-256 fingerprint and license for each. Form 602 exhibits are downloaded by the user in a browser and imported (FCC's firewall blocks automated download).
2. **Raw records** **[built]**: rows or passages pulled from each source, with an exact locator (file and line, or page) and parser version. Never edited after extraction; sensitive personal values and demographic fields are removed before storage.
3. **Statements** **[built]**: entities, identifiers, attributes, licenses, transmitter sites, relationships and events, one row per source statement. Disagreeing sources produce multiple rows rather than overwriting each other. GLEIF is held in staging tables and promoted for companies connected to FCC entities.
4. **Computed layer** **[partly built]**: timing percentiles **[built as a library function; display after week 5]**; entity matching ("possibly same" links with per-comparison score breakdowns) and inferred links with evidence **[planned, week 5]**. All of it can be rebuilt from layers 1–3.
5. **Metrics** **[built]**: absorbing Markov chain over equity and nominee links, plus a separate control-reachability analysis.
6. **Outputs** **[built: Markdown report; planned: library API, web UI]**: `results/dev_cases.md` today; later a search API (by licensee name/FRN or person) and a graph view.
7. **User review** **[planned]**: append-only, locally encrypted log of the user's match confirmations and rejections, exportable as an audit trail.

## Repository layout
- `src/teleownermap/`: the package (src layout).
  - `schema.py` **[built]**: DuckDB DDL mirroring `docs/data_model.md`; `connect()` opens a database and creates the tables.
  - `metrics/ownership.py` **[built]**: ownership probabilities and anonymity metrics.
  - `metrics/timing.py` **[built]**: pair-timing and lead-time percentiles against a user-chosen comparison group, with group size, small-group flag (< 30) and the "group may contain shells" caveat.
  - `ground_truth.py` **[built]**: loads hand-built case graphs, runs the metrics on them, writes the report.
  - `exhibits.py` **[built]**: lists a filing's exhibits (ownership-related first, read/unread, stable numbering) with download steps and the live-lookup warning; imports a user-downloaded PDF for one chosen exhibit and extracts page text with PyMuPDF.
  - `ingest/__main__.py` **[built]**: `python -m teleownermap.ingest fcc|gleif [--low-memory] [--no-download]`.
  - `ingest/download.py` **[built]**: downloads bulk files as dated snapshots with the honest User-Agent "teleownermap", at least 1 s apart, stopping on HTTP 403/429; FCC through `curl` (FCC refuses Python's client), GLEIF through Python.
  - `ingest/fcc_owner.py` **[built]**: Form 602/175 ownership file (direct holders as equity, officers/directors as control, indirect holders and holdings as upper-bound "named" links outside the metrics).
  - `ingest/fcc_uls.py` and generated `ingest/uls_columns.py` **[built]**: ULS license and application files (licenses, licensees, contacts, sites, history, applications, transfers and assignments with FCC consent/consummation dates).
  - `ingest/gleif.py` **[built]**: GLEIF staging (whole golden copy) and `promote()` of chosen LEIs plus their parent chains (runs once week-5 matching supplies the LEIs).
  - `ingest/hashing.py` **[built]**: local address/phone/email standardization and HMAC hashes; per-installation key in `~/.config/teleownermap/hmac.key`.
  - `ingest/_bulk.py` **[built]**: fast, memory-bounded inserts through temporary JSON-lines files in 50k-row batches (row-by-row inserts ran at ~2k rows/s).
- `tests/` **[built]**: pytest suites for the schema, metrics, ground-truth loader, downloads, hashing, all three parsers, exhibits and timing.
- `ground_truth/` **[built, public]**: verified cases (`cases.md`), hand-built case graphs (`graphs/*.csv`), and the negative-control answer key (`negative_controls.csv`). Source documents go in `ground_truth/sources/` (gitignored).
- `scripts/make_figures.py` **[built]**: paper figures (schema, architecture, pipeline) written as PDF and PNG to `results/figures/`. The schema figure reads tables and keys from the live DuckDB schema and fails if a table has no position assigned; the architecture and pipeline figures' built/planned labels are set by hand and need updating as stages are built.
- `results/`: generated outputs (`dev_cases.md`, `figures/`).
- `data/` (gitignored): bulk downloads (`snapshots/`), imported exhibits (`fcc_exhibits/`) and the local database `teleownermap.duckdb`.
- `docs/`: plan, decisions, work log, data model, this file.
- `.github/workflows/lint.yml`: CI.

## Data storage
- **DuckDB** **[built]** for local use: embedded, single file, no server, so journalists can run it without database setup. Postgres is planned for a hosted deployment **[planned]**.
- Relational tables were chosen over a graph database (Neo4j) because the metrics are custom Python anyway, entity resolution is tabular, and it's simpler to deploy.
- Tables: provenance (`sources`, `records`), statements (`entities`, `entity_records`, `identifiers`, `attributes`, `licenses`, `license_sites`, `relationships`, `events`), exhibits (`exhibit_files`), GLEIF staging (`gleif_entities`, `gleif_relationships`, `gleif_exceptions`), computed (`evidence`, `match_links`, `match_evidence`), user (`reviews`) and reproducibility (`runs`).
- Size and resources (measured 2026-10-30 to 11-02 on the full data): the FCC load takes ~13 min with a 2.66 GB memory peak; GLEIF staging ~7 min with 1.52 GB; the database is 7.9 GB and the downloads 0.9 GB. DuckDB is capped at 1 GB and 4 threads (`--low-memory`: 500 MB and 10k-row batches), so it fits an 8 GB laptop; ~20 GB of free disk leaves room for updates.
- Integrity rules are enforced by the database as `CHECK` constraints, not just application code, for example:
  - sensitive attributes, sites and sole-proprietor GLEIF rows must have null plain values (only HMAC hashes are stored);
  - documented relationships must cite a source record;
  - shares must be in [0, 1] with `share_min <= share_max`;
  - a relationship points to exactly one of an entity or a license;
  - an `unknown_owner` entity must name the company it belongs to;
  - enumerations (entity types, link graphs, legal status labels, date precisions) are fixed lists defined once in `schema.py`.
- The `runs` table (code version, snapshot labels, parameters) exists in the schema but isn't written to yet **[planned]**.

## Metrics engine (`metrics/ownership.py`)
- Input is a list of `Stake` dataclasses (owner, owned, share range, confidence, graph type, source IDs). `combine_statements` merges statements about the same link into one range covering every reported value, keeps the highest confidence, and records any disagreement.
- **Owner probabilities**: builds the transient-to-transient matrix Q and transient-to-absorbing matrix R and solves (I − Q)B = R with `numpy.linalg.solve` to get absorption probabilities. Handles cross-holding loops; a loop that nothing ever leaves raises `ClosedOwnershipLoopError`.
- Unaccounted shares go to a per-company "unknown owner" endpoint ("public shareholders" for publicly traded companies). The unconfident part of an inferred link (share × (1 − confidence)) also goes there.
- Nominee links pass ownership through a proxy to the party it acts for; any remainder stays with the nominee.
- **Outputs per run** (`OwnershipResult`): owner probabilities, unknown and public share, entropy over all endpoints and over known owners only, anonymity set size, hop distribution, expected hops, over-allocated companies, and source discrepancies.
- **Ranges** (`analyze_range`): probabilities, unknown share and hop counts change monotonically with each share, so all range-end combinations are evaluated (up to 4096; beyond that, a seeded random sample, flagged `exact=False`). Entropy can peak mid-range, so its bounds are refined with `scipy.optimize.minimize` (L-BFGS-B, bounded). An optional, labeled midpoint mode is available.
- **Control**: analyzed separately as unweighted reachability (`control_reach`, breadth-first search over the whole ownership chain) and `control_without_equity`, with no probabilities or entropy.
- Graph traversal is implemented directly with the standard library (`collections.deque`, `heapq`) rather than a graph library.

## Ground-truth harness (`ground_truth.py`)
- Each case graph is a CSV with one row per source statement (owner, owned, link type, share range, legal status label, disclosed yes/no, dates, citation, note), so the user can check it in a spreadsheet.
- The loader validates rows, loads them into DuckDB through the real schema (fingerprinting each CSV with SHA-256 as its `sources` row, so the schema is exercised end to end), filters to links valid on the case's snapshot date, and runs the metrics for two views: "disclosed" (companies' own filings) and "full" (plus links from court/FCC documents).
- `python -m teleownermap.ground_truth` writes `results/dev_cases.md`.
- Evaluation design **[planned]**: held-out case reconstruction (P1, P2, P10–P12 kept untouched until final evaluation), planted structures in a separate marked data copy, negative controls, and a hand-labeled sample for measuring entity-matching accuracy.

## Packages
- **Runtime dependencies** (declared in `pyproject.toml`):
  - `duckdb>=1.1`: embedded database and schema enforcement.
  - `numpy>=1.26`: Markov chain matrices and linear solve; seeded random sampling.
  - `scipy>=1.11`: bounded numerical optimization for entropy bounds.
  - `pymupdf>=1.24`: exhibit PDF text extraction (pip-only install; AGPL-3.0 like this project).
- **System tool**: `curl` for FCC downloads (ships with macOS, Windows 10+ and most Linux).
  - `networkx>=3.3`: declared but **not currently imported anywhere**; traversal is hand-written (see open questions).
- **Standard library** used heavily: `dataclasses`, `csv`, `zipfile`, `hashlib`/`hmac` (fingerprints and keyed hashes), `urllib`, `subprocess`, `itertools`, `collections`, `pathlib`, `datetime`, `calendar`.
- **Development tools** (`[dev]` extra): `pytest>=8` for tests, `ruff>=0.6` for linting and formatting.
- **Figures** (`[figures]` extra): `matplotlib>=3.8`, used only by `scripts/make_figures.py`, not by the library.
- **Build**: `hatchling` backend, wheel built from `src/teleownermap`.
- **Planned**: Splink (entity resolution, runs on DuckDB/Postgres tables, gives explainable per-comparison match weights), Cytoscape.js (web graph view), Docker (one-command self-hosted setup), Postgres (hosted storage). No other AI/ML is planned beyond Splink for now.
- Versions in the local environment as of this writing: Python 3.13, DuckDB 1.5.6, NumPy 2.5.4, SciPy 1.18.1.

## Code standards, testing and CI
- Python ≥ 3.11; ruff with a 100-character line length and rule sets E, F, I (import order), B (bugbear) and UP (pyupgrade).
- Tests verify metrics and timing percentiles against hand-computed examples (including cross-holding loops, nominees, ranges and over-allocation), schema constraints (that bad rows are rejected), the ground-truth loader, downloads against a local test server (both clients, refusal handling), and each parser on small hand-made files, including privacy checks that no plain personal address, phone, email or demographic field reaches the database.
- Local commands: `.venv/bin/pytest -q`, `.venv/bin/ruff check .`, `.venv/bin/ruff format`.
- GitHub Actions runs `ruff check` and `ruff format --check` (Python 3.11) and the test suite (Python 3.11 and 3.13) on every push and pull request.

## Reproducibility and provenance
- Every downloaded file gets a local copy, URL, retrieval time and SHA-256 fingerprint; downloads are kept as dated snapshots, and snapshots used in the paper are pinned.
- Raw records are never edited; every computed result can be rebuilt from them.
- Every relationship row carries its legal status label (stated, alleged, admitted, settled finding, found) as a filter, never as a confidence number.
- Source documents and bulk data are gitignored so they can't be committed by accident; ground-truth notes and citations are public in the repo so others can reproduce the evaluation.

## Privacy and security engineering
- Sensitive personal fields (people's addresses, phone, fax and email; individual licensees' transmitter sites; sole proprietors' GLEIF addresses) are standardized, hashed with HMAC (addresses at full, ZIP and city level), and kept out of the database as plain values **[built]**. The unaltered downloads stay in gitignored `data/` so snapshots can be rebuilt.
- Race, ethnicity and sex fields in ULS records are never stored, not even hashed **[built]**.
- The HMAC key is random per installation, stored outside the database with user-only permissions **[built]**.
- No search history, click tracking or web-server access logs; only deliberate user decisions are stored, locally and encrypted **[planned]**.
- Bulk downloads are preferred over per-entity live lookups; the exhibit guide shows the live-lookup warning before its link to the FCC filing **[built]**. Downloads identify the tool honestly and stop on refusal **[built]**.
- A short threat model will be written, including that adversaries can use the open method too **[planned]**.

## Licensing
- AGPL-3.0-only, no CLA or DCO, so anyone who modifies it, even to run it as a website, must publish their changes.

## Open questions and known gaps
- `networkx` is a declared dependency that nothing uses. Either drop it or use it (e.g. for subgraph extraction or export) — your call.
- Entity types across sources: the first source loaded sets an FRN's type (FCC license files first); cross-source conflicts are to be revisited in week 5.
- GLEIF companies often have non-Latin legal names (e.g. 株式会社NTTドコモ, with "NTT DOCOMO, INC." only as an other name), so matching must search other and transliterated names.
- The FCC bulk ownership file keeps only each filer's current filing; history before our first snapshot comes from the application files, `a_aatc` and documents.
- Exhibit text extraction doesn't OCR scanned pages; it counts them.
- `scripts/make_figures.py`'s architecture and pipeline figures still show ingestion as planned; their labels are set by hand.
- `README.md` is still a placeholder.
