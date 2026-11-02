# Plan

Deadlines: full paper draft due **Dec 1, 2026**; final paper (plus current tool state) due **Dec 7, 2026 at 17:00**. Quality over speed. Decisions live in `decisions.md`; work done lives in `methodology.md`.

## Week 1 — Oct 12–18: Ground truth + data model
- [x] Ground-truth research draft (AI-assisted) → `ground_truth/cases.md`
- [x] User verifies every hop against primary documents (P1–P12 done 2026-10-22; UNSUPPORTED rows relabeled as gaps)
- [x] Choose held-out cases vs development cases (held out: P1, P2, P10–P12; development: P3–P9; Azercell excluded)
- [x] Confirm negative-control carriers (large + small) and their sources (TDS dropped; answer key in `ground_truth/negative_controls.csv`)
- [x] Draft schema: entities, ownership/control edges (ranges, control types, dates, per-statement sources), evidence, "possibly same" links, user review log → `docs/data_model.md`
- [x] Discuss schema; log decisions
- [x] User reviews `docs/data_model.md` (approved 2026-10-25)
- [x] Repo setup: Python package layout, DuckDB, tests, linting

## Week 2 — Oct 19–25: Metrics
- [x] Hand-build development-case graphs from verified ground truth (`ground_truth/graphs/`; awaiting user review of judgment calls)
- [x] Absorbing Markov chain with "unknown owner" endpoint; documented-only equity view as special case
- [x] Shannon entropy, anonymity set size, path length distribution
- [x] Range handling: true lower/upper bounds over ranges (numerical search for entropy); optional labeled midpoint mode
- [x] Separate equity and control graphs; 0%-equity control annotations
- [x] Unit tests on hand-computed examples
- [x] User confirms the 8 metric modeling choices; logged in `decisions.md`
- [x] Nominee ("nominee for") links pass ownership/control through proxies; "admitted" and "settled finding" statement labels added
- [x] Revisit tentative timing-correlation decisions (settled 2026-10-25)

## Open items (as of 2026-10-25)
- [x] Held-out vs development split confirmed
- [x] P5 assigned to development; Azercell left out of the evaluation for now
- [x] Hand-build development-case graphs and run metrics on them → `results/dev_cases.md`
- [x] Graph judgment calls accepted; control reach searches the whole ownership chain
- [x] User OK on the "backed by its owners' equity" rule for control without equity
- [ ] Verify DISH, CITIC Telecom International and CITIC Limited were publicly traded at the snapshot dates
- [x] P3 status labels confirmed (rows 1–4, 7–9 stated; 5, 6, 10 alleged)
- [x] P2 rows 9–11 confirmed "alleged"
- [x] P7 row 2 reworded: fn. 423 cites the Executive Branch Recommendation re CTA at 33
- [x] Azercell rows 1–5 verified; row 6 is a gap
- [x] Negative controls marked verified (row notes' open issues remain)
- [x] TDS negative control dropped
- [x] Negative-control answer key stored as CSV
- [x] User reviewed `docs/data_model.md`
- [ ] Week 6: decide how to score case reconstruction given that FCC's bulk ownership file keeps only each filer's current filing (no 2001–2022 history); state it in Limitations
- [x] Retry FCC bulk download through the tool: still refused 2026-10-30; switched FCC downloads to curl (works)
- [x] Optional: add a test job to the GitHub Actions workflow
- [ ] Optional: open FCC 15-104 ¶¶ 14–17 to fill P4 row 7 (and get an FCC "found" de facto control label)

## Weeks 3–4 — Oct 26–Nov 2: FCC + GLEIF ingestion (finished a week early)
- [x] FCC ULS download + parser (licensees, FRNs, dates; plus a_aatc transfers, sites, history)
- [x] Form 602 ownership disclosures parser (plus Form 175)
- [x] GLEIF bulk data + parent-relationship records (staging + promote built; full staging verified 2026-11-02)
- [x] Rerun full GLEIF staging; record time, memory, disk; add `gleif` to the ingest command
- [x] Guided exhibit import: list exhibits read/unread with download steps, "add" a user-downloaded file, extract text with PyMuPDF
- [x] Source/evidence recorded for every ingested value; filing vs effective dates
- [x] Timing events extracted (ULS application/grant, transfer of control and consent/consummation, Form 602 filings, LEI registration/creation)
- [x] Check whether FRN registration dates are public in bulk (not published; excluded)
- [x] Timing percentile scoring as a library function (pair timing and lead time vs user-chosen comparison groups, with group size); display waits for week 5 links
- [x] Update `docs/architecture.md` for ULS and GLEIF ingestion
- [x] Optional: run tests in GitHub Actions

## Week 5 — Nov 2–8: Entity matching
- [ ] User: download the P3/P4 exhibits by hand and import them (`python -m teleownermap.exhibits`)
- [ ] Timing evidence display for linked pairs (needs week-5 links)
- [ ] Promote GLEIF companies matched to FCC entities (`gleif.promote`)
- [ ] Link each company's multiple FRNs with evidence ("possibly same"); records sharing one FRN are one entity (moved from weeks 3–4)
- [ ] Splink model across FCC, Form 602, GLEIF records
- [ ] Transliteration-aware name comparison; name-frequency weighting
- [ ] "Possibly same" links with evidence for and against; ranked candidates; never auto-chained
- [ ] Revisit: cross-source entity-type conflicts (first source loaded currently wins) and which GLEIF columns staging keeps
- [ ] Hand-label a sample of match pairs; measure match accuracy
- [ ] Metrics with and without unverified top matches

## Week 6 — Nov 9–15: Evaluation
- [ ] Case-study reconstruction (owner-revealing documents hidden), held-out cases last
- [ ] Planted structures in a separate, clearly marked data copy
- [ ] Negative controls (large + small legitimate carriers)
- [ ] Results tables and figures for the paper

## Week 7 — Nov 16–22: Web app + user-friendly deliverables
- [ ] Tidy Python library API: search by licensee/FRN and by person
- [ ] Web app (Cytoscape.js graph view): search, owner probabilities, evidence trail, "possible match, unverified" labels, toggle for unverified matches
- [ ] Docker one-command setup
- [ ] Step-by-step `SETUP.md` for non-technical users (8 GB RAM, ~20 GB disk)
- [ ] Draft `ASSUMPTIONS.md` from `decisions.md`

## Week 8 — Nov 23–29: Paper (Thanksgiving Nov 26)
- [ ] Update Methods (from `methodology.md`) and write Results (user has been writing throughout)
- [ ] Limitations and AI-use disclosure

## Buffer + submission — Nov 30–Dec 7 (draft due Dec 1; final due Dec 7, 17:00)
- [ ] Spare week for anything that slipped
- [ ] Submit full draft (Dec 1)
- [ ] Revise paper; fix slide/paper inconsistencies ($113M vs $133M, "Afron", "O'Conner", "et. al.", Feamster attribution)
- [ ] Submit final paper (Dec 7, 17:00)

## Stretch / after deadline
- [ ] Audit-trail export of user match confirmations
- [ ] Change-over-time analysis: metrics across a case's history (e.g. P7 before/after 2007, P9's 2008 CITIC transfer) instead of one snapshot date
- [ ] OpenCorporates, state registries, ICIJ, national registries
- [ ] Red-flag overlay, "most suspicious" ranking, BODS export, possible GitHub Pages site
