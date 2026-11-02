# Data Model (draft)

**Status:** draft, under review. Items marked *(tentative)* may change.

## Principles
- **Store what each source said, exactly as it said it; never overwrite it.** Matches, inferred links and metrics are computed on top and can always be rebuilt.
- **Present evidence, don't conclude.** Conflicting values, ranges and possible matches are all kept, each with its source.
- **Every fact traces to a source record.** No value exists without a pointer to where it came from.
- **No hidden decisions.** Every modeling choice here will be listed publicly in `ASSUMPTIONS.md`.
- **Protect people.** Sensitive personal fields are stored only as keyed hashes; user activity isn't tracked.

## Provenance

### `sources`
A document or dataset we downloaded.

| Column | Meaning |
|---|---|
| source_id | ID |
| source_type | e.g. `fcc_uls_bulk`, `fcc_form_602`, `gleif_golden_copy`, `court_opinion`, `fcc_order` |
| publisher, title, url | Where it came from |
| retrieved_at | When we downloaded it |
| sha256 | File fingerprint; proves a local copy is unaltered |
| license | Source's license/terms (e.g. public domain, CC0, ODbL) |
| snapshot_label | Dated snapshot this file belongs to (data updates weekly) |
| local_path | Local copy (under gitignored `data/` or `ground_truth/sources/`) |
| pinned | Never delete (e.g. used in the paper's evaluation) |

### `records`
A raw row or passage extracted from a source. Never edited.

| Column | Meaning |
|---|---|
| record_id | ID |
| source_id | Source it came from |
| locator | Exact location: row number, page, paragraph, field |
| raw | The extracted content, **with sensitive personal values removed** (they exist only as hashes in `attributes`) |
| parser_version | Code version that extracted it |

## What sources say

### `entities`
A party as it appears in the data. Never merged across sources.

| Column | Meaning |
|---|---|
| entity_id | ID |
| entity_type | `company`, `person`, `government`, `unknown_owner`, `unclassified` |
| labels | e.g. `state_owned`, `trust`, `publicly_traded` (companies keep type `company`; a publicly traded company's unaccounted share is labeled "public shareholders" instead of "unknown owner") |
| unknown_owner_of | For `unknown_owner` only: the company whose unaccounted ownership it holds; never shown as a real party |

*(tentative)* Records sharing the same official ID from the same registry (an FCC FRN, or a GLEIF LEI) are one entity. Different FRNs/LEIs are always separate entities, connected only by evidence-backed links.

### `entity_records`
Which records make up each entity, so any record can be split off if an ID turns out wrong.

| Column | Meaning |
|---|---|
| entity_id, record_id | Link |

### `identifiers`

| Column | Meaning |
|---|---|
| entity_id | Entity |
| scheme | `FRN`, `LEI`, `state_file_number`, … |
| value | The ID |
| record_id | Source record |
| conflict_flag | Set when records under one ID have clearly conflicting details (possible ID error) |

GLEIF duplicate/successor LEI records become documented links between entities, not merges. *(tentative)*

### `attributes`
One row per statement. Disagreeing sources produce multiple rows.

| Column | Meaning |
|---|---|
| attribute_id | ID |
| entity_id | Entity |
| name | `name`, `address`, `birth_year`, `phone`, `email`, `citizenship`, … |
| value | Plain value; **null for sensitive fields** |
| is_sensitive | Residential address, birth date/year, personal phone/email |
| hmac_full, hmac_zip, hmac_city | Keyed hashes of the standardized value at several levels (sensitive fields only) |
| valid_from, valid_from_precision | Date and precision (`day`, `month`, `year`) |
| valid_to, valid_to_precision | Same |
| valid_to_status | `ended`, `ongoing`, `unknown` |
| record_id | Source record |

Sensitive values are standardized, then hashed with a per-installation random key stored outside the database; the original value is thrown away. The UI shows "same residential address (see source X, p. 3)" but never the value. Business info (registered office, company phone) is not sensitive and is shown normally.

### `licenses`

| Column | Meaning |
|---|---|
| license_id | ID |
| call_sign, radio_service, market | License details |
| grant_date, expiry_date, effective_date, cancellation_date | Dates |
| status | FCC license status code (A active, C canceled, E expired, T terminated, …) |
| auction_id | Auction the license was won in, if any |
| record_id | Source record |

### `license_sites`
Transmitter sites (ULS location records). Shared sites are evidence, weighted by how many licensees share them; registered towers are usually shared commercially.

| Column | Meaning |
|---|---|
| site_id | ID |
| license_id | License |
| address, city, county, state | Site address (**null except state for individual licensees**, whose site may be their home) |
| latitude, longitude | Decimal degrees (null for individual licensees) |
| tower_registration | Antenna Structure Registration number, if the site is a registered tower |
| is_sensitive | Individual licensee's site |
| hmac_coords, hmac_address | Keyed hashes of the coordinates (rounded to 5 decimals) and standardized address |
| record_id | Source record |

### `relationships`
Ownership, control and other links. One row per source statement; ranges across sources are computed, not stored.

| Column | Meaning |
|---|---|
| rel_id | ID |
| interested_party_id | Entity holding the interest |
| subject_entity_id / subject_license_id | What the interest is in |
| interest_type | `shareholding`, `voting_rights`, `board_seat`, `officer`, `license_holder`, `filing_author`, `registered_agent`, `legal_counsel`, `same_identifier_successor`, `nominee_for` (the registered party acts for the interested party), … |
| graph | `equity`, `control`, `nominee`, or `none` (agents and counsel are `none`: evidence only; `nominee` links are followed by both the equity and control analyses) |
| title_as_written | Exact title from the source, e.g. "Assistant Secretary" |
| role_class | Classification shown with the title, e.g. `(officer)`, `(director)` |
| share_min, share_max | Range as reported; equal when exact; null when not stated |
| start_date, start_precision | Date and precision |
| end_date, end_precision, end_status | `ended`, `ongoing`, `unknown` |
| filing_date, effective_date | Both kept when available |
| basis | `documented` or `inferred` |
| assertion_status | `stated` (the party's own filing), `alleged` (e.g. complaint), `admitted` (the party admitted it, e.g. a DOJ statement of facts), `settled_finding` (findings in a settlement the party neither admitted nor denied, e.g. many SEC orders), `found` (adjudicated court/agency finding) |
| labels | Notes on how to read the statement, e.g. `upper_bound` (FCC indirect percentages), `reported_0.00`, `filing_status:P`, `gleif_consolidation_pct` |
| record_id | Source record (documented links) |

### `events`
Dated events for timing analysis.

| Column | Meaning |
|---|---|
| event_id | ID |
| entity_id / license_id | What it's about |
| event_type | `incorporation`, `frn_registration`, `license_application`, `license_grant`, `transfer_of_control`, `form_602_update`, `officer_change`, … |
| date, precision | Date and precision |
| record_id | Source record |

### `exhibit_files`
Form 602/175 exhibit PDFs the user downloaded from ULS and imported (FCC blocks automated download). Each PDF is a `sources` row (`fcc_exhibit`); each page's extracted text is a `records` row (locator `page N`). Exhibit text is shown in full but excluded from exports by default, since free text can hold home addresses.

| Column | Meaning |
|---|---|
| exhibit_record_id | The attachment record (T) in the ownership file that lists this exhibit |
| source_id | The imported PDF |
| pages, pages_without_text | Page count, and pages with no text layer (likely scans; not OCR'd) |
| imported_at | When the user imported it |

## GLEIF staging
The whole GLEIF golden copy, one row per CSV row, so any company is searchable. Only companies connected to an FCC entity (a possible match plus its full parent chain) are promoted into `entities`, `relationships` and `attributes`.

- `gleif_entities`: LEI, legal and other names, legal and headquarters addresses (with keyed hashes for matching), jurisdiction, category, legal form, entity and registration status, key dates, managing LOU, successor LEIs and legal-entity events. A sole proprietor's street, city and postal code are null; only hashes are kept.
- `gleif_relationships`: child LEI, parent ID (an LEI, or another ID type), relationship type (directly/ultimately consolidated by, fund-managed by, sub-fund of, feeder to, international branch of), status, periods, the consolidation percentage when given, accounting standard, and registration status.
- `gleif_exceptions`: reporting exceptions: why no parent is reported (natural persons, non-consolidating, no known person, no LEI, non-public, opt-out reasons), with any references.

## Computed on top (rebuildable)

### `evidence`
Why an inferred link exists.

| Column | Meaning |
|---|---|
| evidence_id | ID |
| rel_id / match_id | What it supports |
| kind | `shared_agent`, `shared_counsel`, `shared_address`, `shared_contact`, `timing`, … |
| detail | Plain-language description |
| commonness | How many entities share this attribute (a boutique agent shared by 3 means more than one shared by 300,000) |
| record_ids | Source records |

### `match_links`
"Possibly same" pairs. Never chained automatically; never merged.

| Column | Meaning |
|---|---|
| match_id | ID |
| entity_a, entity_b | Pair |
| model_version | Matching model that produced it |
| score | Raw score (shown in the dropdown, not as a headline percentage) |
| rank | Rank among candidates for the same record |

### `match_evidence`
Breakdown of each match score.

| Column | Meaning |
|---|---|
| match_id | Match |
| comparison | e.g. `name_similarity`, `same_address_zip`, `different_state` |
| weight | Contribution, positive (for) or negative (against) |
| record_ids | Source records |

### `reviews`
User decisions on matches or inferred links. Append-only, stored locally and encrypted. This is the only user activity stored; there is no search history, click tracking or access logging.

| Column | Meaning |
|---|---|
| review_id | ID |
| target_type, target_id | Match or link reviewed |
| status | `confirmed`, `rejected`, `unsure` |
| note | User's note |
| created_at | Timestamp |

### `runs`
Reproducibility record for every metrics run.

| Column | Meaning |
|---|---|
| run_id | ID |
| code_version | Git commit |
| snapshot_labels | Data snapshots used |
| parameters | e.g. range mode (both ends / midpoint), comparison group, match inclusion setting |
| created_at | Timestamp |

## How metrics use this
- **Owner probabilities:** absorbing Markov chain over `relationships`, with share × edge confidence, plus an `unknown_owner` endpoint for unaccounted shares ("public shareholders" for publicly traded companies). The unconfident part of an inferred link also flows to `unknown_owner`. Documented-only links at full confidence reduce it to plain equity multiplication.
- **Nominees:** a person with a `nominee` link doesn't end the ownership walk; their holding passes on to the party they act for (share × confidence), and any remainder stays with the nominee as a possible real owner. Control through a proxy likewise reaches the hidden party.
- **Separate equity and control graphs** (`graph` column). The equity graph notes people with control links but 0% equity.
- **Ranges:** every metric is reported as a true lower and upper bound over all share values within their ranges (`share_min`–`share_max`, widened by disagreeing sources; unstated shares are 0–100%). Entropy bounds are refined numerically because entropy can peak mid-range. Optional labeled midpoint mode.
- **Discrepancies:** when sources disagree on a share or a link's confidence, the highest confidence is used and the disagreement is listed with the results.
- **Matches:** results shown both as "documented + your confirmations" and "including unverified top matches" (toggle hides the latter).
- **Timing:** `events` gaps (pair timing and lead time) scored as percentiles within a user-chosen comparison group, with group size shown; shown as evidence only, primarily for pairs already linked by other evidence.
