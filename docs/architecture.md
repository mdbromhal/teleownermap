# Architecture and Software Engineering

**Status as of 2026-10-26.** Each item is marked **[built]** (in the repo, tested) or **[planned]** (decided in `docs/decisions.md`, not yet written). Data model details are in `docs/data_model.md`; the work log is `docs/methodology.md`.

## Overview
- `teleownermap` is an open-source Python package that treats a telecom ownership structure like an anonymity network: the FCC licensee is the exit node, shell companies are relays, and the ultimate owner is the entry node.
- It walks ownership upward from a licensee and measures how well the real owner is hidden, using anonymity metrics (owner probabilities, Shannon entropy, anonymity set size, hop distribution).
- Two delivery targets: a Python library for developers **[built, partial]** and a self-hosted web app for non-technical journalists **[planned, may come after the December deadline]**.
- Design rule throughout: present evidence, don't conclude. The system never merges records, never invents precision, and every value traces back to a source.

## Pipeline (layers)
1. **Sources** **[planned for real data; built for ground truth]**: download bulk files (FCC ULS, Form 602, GLEIF) as dated snapshots, keep local copies, and record URL, retrieval time, SHA-256 fingerprint and license for each.
2. **Raw records** **[built in schema]**: rows or passages pulled from each source, with an exact locator (row, page, paragraph) and parser version. Never edited after extraction.
3. **Statements** **[built in schema]**: entities, identifiers, attributes, licenses, relationships and events, one row per source statement. Disagreeing sources produce multiple rows rather than overwriting each other.
4. **Computed layer** **[planned]**: entity matching ("possibly same" links with per-comparison score breakdowns), inferred links with evidence, and timing evidence. All of it can be rebuilt from layers 1–3.
5. **Metrics** **[built]**: absorbing Markov chain over equity and nominee links, plus a separate control-reachability analysis.
6. **Outputs** **[built: Markdown report; planned: library API, web UI]**: `results/dev_cases.md` today; later a search API (by licensee name/FRN or person) and a graph view.
7. **User review** **[planned]**: append-only, locally encrypted log of the user's match confirmations and rejections, exportable as an audit trail.

## Repository layout
- `src/teleownermap/`: the package (src layout).
  - `schema.py` **[built]**: DuckDB DDL mirroring `docs/data_model.md`; `connect()` opens a database and creates the tables.
  - `metrics/ownership.py` **[built]**: ownership probabilities and anonymity metrics.
  - `ground_truth.py` **[built]**: loads hand-built case graphs, runs the metrics on them, writes the report.
  - `ingest/download.py` **[built]**: downloads FCC ULS and GLEIF bulk files as dated snapshots (honest User-Agent, rate-limited, stops on refusal), fingerprints them and registers them in `sources`.
  - `ingest/fcc_owner.py` **[built]**: Form 602/175 ownership file into the statement tables (direct holders as equity, officers/directors as control, indirect holders and holdings as upper-bound "named" links outside the metrics).
  - `ingest/hashing.py` **[built]**: local address standardization and HMAC hashes at full/ZIP/city level; per-installation key in `~/.config/teleownermap/hmac.key`.
  - `ingest/_bulk.py` **[built]**: fast inserts through temporary JSON-lines files (row-by-row inserts ran at ~2k rows/s).
  - `ingest/` parsers **[planned]**: FCC license/application files and GLEIF.
- `tests/` **[built]**: pytest suites for the schema, metrics and ground-truth loader (42 tests, all passing).
- `ground_truth/` **[built, public]**: verified cases (`cases.md`), hand-built case graphs (`graphs/*.csv`), and the negative-control answer key (`negative_controls.csv`). Source documents go in `ground_truth/sources/` (gitignored).
- `scripts/make_figures.py` **[built]**: paper figures (schema, architecture, pipeline) written as PDF and PNG to `results/figures/`. The schema figure reads tables and keys from the live DuckDB schema and fails if a table has no position assigned; the architecture and pipeline figures' built/planned labels are set by hand and need updating as stages are built.
- `results/`: generated outputs (`dev_cases.md`, `figures/`).
- `data/` (gitignored): bulk downloads and local DuckDB files.
- `docs/`: plan, decisions, work log, data model, this file.
- `.github/workflows/lint.yml`: CI.

## Data storage
- **DuckDB** **[built]** for local use: embedded, single file, no server, so journalists can run it without database setup. Postgres is planned for a hosted deployment **[planned]**.
- Relational tables were chosen over a graph database (Neo4j) because the metrics are custom Python anyway, entity resolution is tabular, and it's simpler to deploy.
- Tables: provenance (`sources`, `records`), statements (`entities`, `entity_records`, `identifiers`, `attributes`, `licenses`, `relationships`, `events`), computed (`evidence`, `match_links`, `match_evidence`), user (`reviews`) and reproducibility (`runs`).
- Integrity rules are enforced by the database as `CHECK` constraints, not just application code, for example:
  - sensitive attributes must have a null plain `value` (only HMAC hashes are stored);
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
  - `networkx>=3.3`: declared but **not currently imported anywhere**; traversal is hand-written (see open questions).
- **Standard library** used heavily: `dataclasses`, `csv`, `hashlib` (SHA-256 fingerprints), `itertools`, `collections`, `pathlib`, `datetime`, `calendar`.
- **Development tools** (`[dev]` extra): `pytest>=8` for tests, `ruff>=0.6` for linting and formatting.
- **Figures** (`[figures]` extra): `matplotlib>=3.8`, used only by `scripts/make_figures.py`, not by the library.
- **Build**: `hatchling` backend, wheel built from `src/teleownermap`.
- **Planned**: Splink (entity resolution, runs on DuckDB/Postgres tables, gives explainable per-comparison match weights), Cytoscape.js (web graph view), Docker (one-command self-hosted setup), Postgres (hosted storage). No other AI/ML is planned beyond Splink for now.
- Versions in the local environment as of this writing: Python 3.13, DuckDB 1.5.6, NumPy 2.5.4, SciPy 1.18.1.

## Code standards, testing and CI
- Python ≥ 3.11; ruff with a 100-character line length and rule sets E, F, I (import order), B (bugbear) and UP (pyupgrade).
- Tests verify metrics against hand-computed examples (including cross-holding loops, nominees, ranges and over-allocation), schema constraints (that bad rows are rejected), and the ground-truth loader.
- Local commands: `.venv/bin/pytest -q`, `.venv/bin/ruff check .`, `.venv/bin/ruff format`.
- GitHub Actions runs `ruff check` and `ruff format --check` on Python 3.11 on every push and pull request. Tests don't run in CI yet (optional item in `docs/plan.md`).

## Reproducibility and provenance
- Every downloaded file gets a local copy, URL, retrieval time and SHA-256 fingerprint; downloads are kept as dated snapshots, and snapshots used in the paper are pinned.
- Raw records are never edited; every computed result can be rebuilt from them.
- Every relationship row carries its legal status label (stated, alleged, admitted, settled finding, found) as a filter, never as a confidence number.
- Source documents and bulk data are gitignored so they can't be committed by accident; ground-truth notes and citations are public in the repo so others can reproduce the evaluation.

## Privacy and security engineering
- Sensitive personal fields (residential address, birth date/year, personal phone/email) are standardized, hashed with HMAC at several levels (full, ZIP, city), and the original value is discarded **[built in schema; hashing code planned]**.
- The HMAC key is random per installation and stored outside the database **[planned]**.
- No search history, click tracking or web-server access logs; only deliberate user decisions are stored, locally and encrypted **[planned]**.
- Bulk downloads are preferred over per-entity live lookups, and users are warned before any live lookup, so queries don't leave a trail on outside servers **[planned]**.
- A short threat model will be written, including that adversaries can use the open method too **[planned]**.

## Licensing
- AGPL-3.0-only, no CLA or DCO, so anyone who modifies it, even to run it as a website, must publish their changes.

## Open questions and known gaps
- `networkx` is a declared dependency that nothing uses. Either drop it or use it (e.g. for subgraph extraction or export) — your call.
- CI lints on Python 3.11 while the local environment is 3.13, and CI doesn't run the tests.
- `ingest/` is empty; FCC and GLEIF ingestion is weeks 3–4 of the plan.
- `README.md` is still a placeholder.
