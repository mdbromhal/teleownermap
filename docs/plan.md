# Plan

Deadline: paper + current tool state, first week of December 2026. Quality over speed; the web app may slip past the deadline. Decisions live in `decisions.md`; work done lives in `methodology.md`.

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
- [ ] Retry FCC bulk download through the tool (refused on 2026-10-29); if still refused, user decides on curl, else build guided manual download + import
- [ ] Optional: add a test job to the GitHub Actions workflow (currently lint only)
- [ ] Optional: open FCC 15-104 ¶¶ 14–17 to fill P4 row 7 (and get an FCC "found" de facto control label)

## Weeks 3–4 — Oct 26–Nov 8: FCC + GLEIF ingestion
- [x] FCC ULS download + parser (licensees, FRNs, dates; plus a_aatc transfers, sites, history)
- [x] Form 602 ownership disclosures parser (plus Form 175)
- [ ] Link each company's multiple FRNs with evidence ("possibly same"); records sharing one FRN are one entity
- [~] GLEIF bulk data + parent-relationship records (staging + promote built; full staging run unverified)
- [x] Source/evidence recorded for every ingested value; filing vs effective dates
- [ ] Timing events extracted (ULS application/grant, transfer of control, Form 602 filings, LEI registration/creation; check whether FRN registration date is public); evidence-only display of percentile gaps vs user-chosen comparison groups, linked pairs first, with group-size warnings

## Week 5 — Nov 9–15: Entity matching
- [ ] Splink model across FCC, Form 602, GLEIF records
- [ ] Transliteration-aware name comparison; name-frequency weighting
- [ ] "Possibly same" links with evidence for and against; ranked candidates; never auto-chained
- [ ] Revisit: cross-source entity-type conflicts (first source loaded currently wins) and which GLEIF columns staging keeps
- [ ] Hand-label a sample of match pairs; measure match accuracy
- [ ] Metrics with and without unverified top matches

## Week 6 — Nov 16–22: Evaluation
- [ ] Case-study reconstruction (owner-revealing documents hidden), held-out cases last
- [ ] Planted structures in a separate, clearly marked data copy
- [ ] Negative controls (large + small legitimate carriers)
- [ ] Results tables and figures for the paper

## Week 7 — Nov 23–29: Paper + library (Thanksgiving Nov 26)
- [ ] Write Methods (from `methodology.md`) and Results
- [ ] Limitations and AI-use disclosure
- [ ] Tidy Python library API: search by licensee/FRN and by person
- [ ] Draft `ASSUMPTIONS.md` from `decisions.md`

## Final — Dec 1–4: Polish + submit
- [ ] Revise paper; fix slide/paper inconsistencies ($113M vs $133M, "Afron", "O'Conner", "et. al.", Feamster attribution)
- [ ] Submit

## Stretch / after deadline
- [ ] Minimal web viewer (if ahead), then full web app (Cytoscape.js), Docker one-command setup, step-by-step `SETUP.md` for laypeople
- [ ] Audit-trail export of user match confirmations
- [ ] Change-over-time analysis: metrics across a case's history (e.g. P7 before/after 2007, P9's 2008 CITIC transfer) instead of one snapshot date
- [ ] OpenCorporates, state registries, ICIJ, national registries
- [ ] Red-flag overlay, "most suspicious" ranking, BODS export, possible GitHub Pages site
