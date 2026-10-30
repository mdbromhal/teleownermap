# Ground-Truth Cases: Hidden Telecom Ownership

> **AI-assisted research draft — NOTHING here is verified until the user checks each hop against the primary document.**

Compiled 2026-10-11 with AI assistance (Claude). Every hop has an unchecked `[ ] verified by user` box.

## How this was gathered (read first)

- **Network limits during research.** From this environment, fcc.gov, docs.fcc.gov, justice.gov, sec.gov and media.cadc.uscourts.gov failed DNS lookup every time. So no FCC order, DOJ document, SEC filing or D.C. Circuit official PDF was opened directly. The quotes come from primary documents read through these hosts instead:
  - **govinfo.gov (GPO)**: district court opinions, the Federal Register, and a Senate report.
  - **cases.justia.com**: PDF copies of D.C. Circuit slip opinions.
  - **caselaw.findlaw.com and case-law.vlex.com**: HTML copies of opinions.
- **Columns.** "Source read" is the URL actually opened. "Official URL (not opened)" is listed where it differs.
- **Quote checks.** Quotes from govinfo and Justia PDFs were extracted with `pdftotext` and string-matched against the text. Quotes from FindLaw and vLex came through a summarising fetch tool that caps quotes at about 125 characters, so they are fragments; check them against the official PDF.
- **Page numbers.** "p. X of Y" is the court's ECF page stamp. "slip op. p." is the page of the slip opinion PDF.
- **Allegations vs findings.** Many hops in the FCA cases are the court's restatement of the relators' complaint ("Compl. ¶ …"), not findings of fact. They are marked **(alleged)**. Structural equity facts (who holds which LP interest) were in the FCC filings and do not appear to be disputed, but confirm them in ULS.
- **UNSUPPORTED** means no primary-source quote was read for that hop, even where the fact is widely reported.

## Summary table

| ID | Case | Jurisdiction | Years | Exit node (licensee) | Entry node (ultimate owner / controller) | Hops quoted / UNSUPPORTED | In FCC/GLEIF data? | Held-out suitability |
|---|---|---|---|---|---|---|---|---|
| P1 | Advantage Spectrum, L.P. (Auction 97) — U.S. ex rel. O'Connor v. U.S. Cellular | US | 2014–2025 | Advantage Spectrum, L.P. | U.S. Cellular → TDS (90% LP; alleged de facto control) | 9 / 0 | Yes: ULS Form 175/601/602, SEC | **Strong** |
| P2 | Carroll / Barat / King Street Wireless (Auctions 58, 66, 73) — O'Connor v. U.S. Cellular (20-cv-2071) | US | 2004–2019 | Carroll Wireless L.P., Barat Wireless L.P., King Street Wireless L.P. | U.S. Cellular → TDS (LP; alleged control) | 7 / 1 | Yes: ULS, SEC | **Strong** (shares principals with P1, so hold out jointly) |
| P3 | Maritime Communications/Land Mobile (Auction 61, AMTS) — FCC 11-64 hearing designation | US | 2005–2011+ | Maritime Communications/Land Mobile, LLC | Sandra M. DePriest (disclosed); Donald R. DePriest (alleged hidden controller) | 10 / 0 | Yes: ULS, Form 602 (incl. MariTEL) | **Strong** (person/spouse link) |
| P4 | DISH / Northstar Wireless / SNR Wireless (Auction 97) | US | 2014–2022 | Northstar Wireless, LLC; SNR Wireless LicenseCo, LLC | DISH Network (85% indirect + de facto control) | 6 / 1 group | Yes: ULS long-form, SEC | Moderate (ownership was disclosed; control dispute) |
| P5 | U.S. ex rel. Taylor v. Gabelli (Lynch Interactive DEs) | US | late 1990s–2004 | 16 bidder LPs (e.g., Fortunet Wireless, High Country) | Mario Gabelli / "Gabelli-related entities" (alleged) | 4 / 1 | Partly: old ULS records, SEC | Moderate–weak |
| P6 | China Mobile International (USA) — FCC 19-38 denial | US/PRC | 2011–2019 | China Mobile International (USA) Inc. (Sec. 214 applicant) | PRC gov't / SASAC | 5 / 1 | Sec. 214 (IBFS/ICFS), not ULS; parents may be in GLEIF | Moderate (disclosed state ownership) |
| P7 | China Telecom (Americas) Corp. — FCC 21-114 revocation | US/PRC | 2001–2021 | China Telecom (Americas) Corp. | SASAC / State Council | 4 / 0 | Sec. 214, not ULS | Moderate |
| P8 | China Unicom (Americas) Operations Ltd. — 2022 revocation | US/HK/PRC | 2002–2022 | China Unicom (Americas) Operations Ltd. | SASAC (~98% of China Unicom) | 4 / 1 | Sec. 214, not ULS | Moderate (unnamed intervening holding companies make a good gap test) |
| P9 | Pacific Networks Corp. / ComNet (USA) LLC — FCC 22-22 revocation | US/HK/PRC | 1999–2022 | ComNet (USA) LLC; Pacific Networks Corp. | CITIC Group → PRC gov't | 6 / 0 (percentages conflict) | Sec. 214, not ULS | **Good** (5-hop, HK chain) |
| P10 | VimpelCom/VEON — Unitel (Uzbekistan), Takilant | UZ/US/NL | 2006–2016 | Unitel LLC | "Foreign Official" (reported: Gulnara Karimova) | 4 / 2 | No (SEC 20-F, DOJ, Gibraltar registry) | Good **after** DOJ SOF opened |
| P11 | Telia — Coscom/Ucell (Uzbekistan), Takilant | UZ/NL/US/SE | 2007–2017 | OOO Coscom (Ucell) | "Government Official A" (reported: Karimova) | 4 / 2 | No (annual reports, NL/GI registries) | Strong design **after** SEC order opened |
| P12 | MTS — Uzdunrobita (Uzbekistan), Swisdorn | UZ/US/CH | 2004–2012 | Uzdunrobita | "Government Official A" | 14 / 0 | No | **Strong** (nominee proxy reused across Takilant and KolorIt); held out with P10–P11 (Takilant) |
| — | Azercell (partial) | AZ/TR/NL | 2014 | Azercell Telekom | TeliaSonera/Turkcell + unnamed 42% holder | 5 / 1 | No | Partial only |
| — | Azerfon (in paper) | AZ/PA | 2011 | Azerfon | Aliyev daughters (secondary only) | 0 / all | No | **Not primary-sourced** — see section |

**Evaluation split (user-confirmed 2026-10-25):** held out (untouched until final evaluation) = P1, P2, P10, P11, P12; development = P3, P4, P5, P6, P7, P8, P9. Azercell is left out of the evaluation for now (its hidden-owner hop has no primary source, and it shares Telia with held-out P11).

**The U.S. Cellular bidding-credit figure is about $113 million, not $133 million.** The D.C. Circuit (No. 23-7041, decided **Sept. 26, 2025**) says "nearly $113 million in bid credits." The D.D.C. opinion of Mar. 31, 2022 (ECF 170, p. 5 of 14) gives the totals: bids of "$451,072,000" and a payment of "$338,304,000". The difference is $112,768,000. The D.D.C. opinion of Aug. 7, 2026 (ECF 224, p. 1 of 30) also says "nearly $113 million". The paper's "$133 million" looks like a typo. Also, the D.C. Circuit decision is dated Sept. 26, 2025; check citation [8].

---

## P1. Advantage Spectrum, L.P. (Auction 97) — U.S. ex rel. O'Connor v. U.S. Cellular

- **Jurisdiction:** US (FCC; D.D.C. No. 20-cv-2070 (TSC); D.C. Cir. No. 23-7041).
- **Years active:**
  - 2014: Advantage registered in Aug. 2014; Auction 97 closed Jan. 29, 2015.
  - 2016: licenses granted in July 2016.
  - 2025: the FCC approved transfer of control from Vail to U.S. Cellular (DA 25-604, July 2025, per secondary search; not opened).
  - Status: the case is pending. The motions to dismiss were denied on Aug. 7, 2026.
- **Exit node:** Advantage Spectrum, L.P. (124 AWS-3 licenses).
- **Relays:**
  - Frequency Advantage, L.P. (general partner, 10%)
  - Sunshine Spectrum, Inc. (51% of Frequency)
  - Nonesuch, Inc. (49% of Frequency)
  - USCC Wireless Investment, Inc. (limited partner, 90%)
- **Entry nodes:**
  - Disclosed: William Vail.
  - Equity / alleged controller: United States Cellular Corp. → Telephone and Data Systems, Inc.
  - Alleged proxy: Allison Cryor DiNardo.
- **Credit:** "nearly $113 million".

**Sources read**
- **D1:** D.D.C. Mem. Op., Mar. 31, 2022, ECF 170 — https://www.govinfo.gov/content/pkg/USCOURTS-dcd-1_20-cv-02070/pdf/USCOURTS-dcd-1_20-cv-02070-0.pdf
- **D2:** D.D.C. Mem. Op., Aug. 7, 2026, ECF 224 — https://www.govinfo.gov/content/pkg/USCOURTS-dcd-1_20-cv-02070/pdf/USCOURTS-dcd-1_20-cv-02070-2.pdf
- **C1:** D.C. Cir. No. 23-7041, Sept. 26, 2025 (Katsas, J.), read via FindLaw — https://caselaw.findlaw.com/court/us-dc-circuit/117755036.html
  - Official URL (not opened): https://media.cadc.uscourts.gov/opinions/docs/2025/09/23-7041-2137183.pdf

| # | From (child) | To (parent) | Jur. | Equity / control as stated | Date | Quote | Source | Page | |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Advantage Spectrum, L.P. | Frequency Advantage, L.P. | US | GP, 10% equity | 2014– | "Frequency Advantage, L.P. is the general partner and 10% equity holder in Defendant Advantage Spectrum, L.P (“Advantage”)." | D1 | p. 4 of 14 | [x] verified by user |
| 2 | Advantage Spectrum, L.P. | USCC Wireless Investment, Inc. | US | LP, 90% equity | 2014– | "USCCWI is the limited partner and 90% equity holder in Advantage Spectrum, L.P." | D1 | p. 4 of 14 | [x] verified by user |
| 3 | Frequency Advantage, L.P. | Sunshine Spectrum, Inc. | US | GP, 51% | 2014–Dec 2015 | "Sunshine Spectrum owns 51% of Frequency Advantage, L.P., while Nonesuch, Inc. owns 49% of Frequency Advantage, L.P." | D1 | p. 4 of 14 | [x] verified by user |
| 4 | Frequency Advantage, L.P. | Nonesuch, Inc. | US | LP, 49% (transferred to Vail in Dec. 2015, per D2 p. 25 of 30: "had transferred her entire indirect, minority, and non-controlling interest in Advantage" to Vail in December 2015 — DiNardo's own characterization) | 2014–Dec 2015 | same as #3 | D1; D2 | p. 4 of 14 | [x] verified by user |
| 5 | Sunshine Spectrum, Inc. | William Vail | US | 100% | 2014– | "general partner Sunshine Spectrum, Inc, which is wholly owned by William Vail." | D1 | p. 4 of 14 | [x] verified by user |
| 6 | Nonesuch, Inc. | Allison Cryor DiNardo | US (VA resident) | sole owner | 2014– | "Defendant Allison Cryor DiNardo is a Virginia resident who is the sole owner of Defendant Nonesuch, Inc." | D1 | p. 4 of 14 | [x] verified by user |
| 7 | USCC Wireless Investment, Inc. | United States Cellular Corp. | US | wholly owned | — | "US Cellular wholly owns and controls Defendant USCC Wireless Investment, Inc (“USCCWI”)." | D1 | p. 4 of 14 | [x] verified by user |
| 8 | United States Cellular Corp. | Telephone and Data Systems, Inc. | US | 84.26% **(as alleged in complaint; P2 opinion says "approximately 80%" — keep both)** | ~2020 | "Telephone and Data Systems, Inc. (“TDS”) is a publicly held corporation that owns 84.26% of Defendant United States Cellular Corporation" | D1 | p. 4 of 14 | [x] verified by user |
| 9 | Advantage Spectrum, L.P. | United States Cellular Corp. (and DiNardo) | US | **Alleged** de facto control (control edge, beyond the 90% equity). Look-through equity: "Vail owned 5.1% of Advantage, DiNardo owned 4.9%, and U.S. Cellular owned the remaining 90%" (D2 p. 5 of 30) | 2014– | "The core allegation is that U.S. Cellular controlled and had an attributable material relationship with Advantage" (fragment) | C1, Part I.C; D2 | D2 p. 5–6 of 30 | [x] verified by user |

- **Disclosure context:** Advantage's short-form and long-form applications stated that Vail, through Sunshine, had de facto and de jure control (D1 p. 5 of 14). That disclosed claim is the "cover story" the tool has to see through.
- **Pointer to raw data:** D1 p. 5–6 cites "Attachments to Advantage Spectrum, L.P. Auction 97 Application, FCC Universal Licensing System". D2 p. 6–7 says DiNardo sold her interest to Vail in Dec. 2015, before the license grant, "to further shield Advantage from FCC scrutiny" (alleged).
- **Data the tool needs:**
  - FCC ULS: Auction 97 Form 175 and long-form Form 601 ownership exhibits, and Form 602 for Advantage. These hold every equity hop.
  - SEC: TDS / U.S. Cellular 10-K Exhibit 21 for USCCWI.
  - State registries for Sunshine Spectrum, Inc. (FL?) and Nonesuch, Inc. (VA?). The states are UNSUPPORTED.
  - GLEIF: TDS and U.S. Cellular likely have LEIs. The small LPs probably do not.
  - People: the DiNardo link across P1 and P2 is the key cross-case signal.
- **Suitability:** **Strong.**
  - The equity chain is fully disclosed in FCC data, but the disclosed *controller* (Vail) differs from the alleged one.
  - This is the best test of "large minority LP plus a shared nominee across DEs."
- **Weaknesses:**
  - Control is alleged, not adjudicated. The case is still being litigated after the Aug. 2026 denial of the motions to dismiss.
  - The FCC granted the credits in 2016 and approved the 2025 transfer of control to U.S. Cellular.
  - Under the conservative label, the "ground truth" for control is "alleged." The equity truth (90% USCCWI) is solid.

## P2. Carroll / Barat / King Street Wireless (Auctions 58, 66, 73) — O'Connor v. U.S. Cellular, No. 20-cv-2071

- **Jurisdiction:** US (D.D.C. No. 20-cv-2071 (TSC); a predecessor FCA suit was No. 1:07-cv-00800-JDB).
- **Years active:**
  - Auctions: Auction 58 (2004), Auction 66 (2006), Auction 73 (2007/08).
  - Transfers of control to U.S. Cellular: Barat in Sept. 2012, Carroll in Dec. 2012.
  - Mergers into U.S. Cellular entities: 2018–2019.
- **Exit nodes:** Carroll Wireless, L.P.; Barat Wireless, L.P.; King Street Wireless, L.P. (152 700-MHz licenses).
- **Relays:** Carroll PCS, Inc.; Barat Wireless, Inc.; King Street Wireless, Inc. (the GPs); USCC Wireless Investment, Inc. (the LP).
- **Entry nodes:**
  - Disclosed GP owner: Allison Cryor DiNardo.
  - LP / alleged controller: U.S. Cellular → TDS.
- **Outcome:** **dismissed on Mar. 22, 2023** under the public-disclosure bar. Allegations were never adjudicated, and the FCC granted King Street's credits after an inquiry (D3 p. 6).
- **Source read (D3):** D.D.C. Mem. Op., Mar. 22, 2023, ECF 165 — https://www.govinfo.gov/content/pkg/USCOURTS-dcd-1_20-cv-02071/pdf/USCOURTS-dcd-1_20-cv-02071-0.pdf
- **Also (D1, from P1):** D.D.C. Mem. Op., Mar. 31, 2022, ECF 170, 20-cv-2070 — https://www.govinfo.gov/content/pkg/USCOURTS-dcd-1_20-cv-02070/pdf/USCOURTS-dcd-1_20-cv-02070-0.pdf (rows 9–11)

| # | From (child) | To (parent) | Jur. | Equity / control as stated | Date | Quote | Source | Page | |
|---|---|---|---|---|---|---|---|---|---|
| 1a | Carroll Wireless, L.P. | USCC Wireless Investment, Inc. | US | partner (LP role inferred from structure; no % stated) | 2004–2018 | "Carroll Wireless, L.P. was a limited partnership between USCC and Defendant (5) Carroll PCS, Inc. (“Carroll Wireless”), which is wholly owned by Defendant (6) Allison Cryor DiNardo." | D3 | p. 4 of 14 | [x] verified by user |
| 1b | Carroll Wireless, L.P. | Carroll PCS, Inc. | US | partner (GP role inferred from structure; no % stated) | 2004–2018 | same quote as above (1a) | D3 | p. 4 of 14 | [x] verified by user |
| 1c | Carroll PCS, Inc. | Allison Cryor DiNardo | US | wholly owned (100%) | — | same quote as above (1a) | D3 | p. 4 of 14 | [x] verified by user |
| 2a | Barat Wireless, L.P. | USCC Wireless Investment, Inc. | US | partner (no % stated) | 2006–2018 | "Barat Wireless, L.P. was a similar limited partnership between USCC and Defendant (8) Barat Wireless, Inc. (“Barat Wireless”), which is likewise wholly owned by DiNardo." | D3 | p. 4 of 14 | [x] verified by user |
| 2b | Barat Wireless, L.P. | Barat Wireless, Inc. | US | partner (no % stated) | 2006–2018 | same quote as above (2a) | D3 | p. 4 of 14 | [x] verified by user |
| 2c | Barat Wireless, Inc. | Allison Cryor DiNardo | US | wholly owned (100%) | — | same quote as above (2a) | D3 | p. 4 of 14 | [x] verified by user |
| 3a | King Street Wireless, L.P. | USCC Wireless Investment, Inc. | US | partner (no % stated) | 2007– | "King Street Wireless, L.P. was a limited partnership between USCC and Defendant (10) King Street Wireless, Inc. (“King Street”), which is also wholly owned by DiNardo." | D3 | p. 4 of 14 | [x] verified by user |
| 3b | King Street Wireless, L.P. | King Street Wireless, Inc. | US | partner (no % stated) | 2007– | same quote as above (3a) | D3 | p. 4 of 14 | [x] verified by user |
| 3c | King Street Wireless, Inc. | Allison Cryor DiNardo | US | wholly owned (100%) | — | same quote as above (3a) | D3 | p. 4 of 14 | [x] verified by user |
| 4 | Carroll / Barat L.P. | U.S. Cellular (formal transfer of control) | US | de jure control after transfer | Sept./Dec. 2012 | "Following the December 2012 transfer of control of Carroll Wireless, L.P. to U.S. Cellular, Carroll Wireless, L.P, merged with and was dissolved into USCC in December 2018." | D3 | p. 4 of 14 | [x] verified by user |
| 5 | USCC Wireless Investment | U.S. Cellular | US | wholly owned | — | "U.S. Cellular wholly owns and controls Defendant (3) USCC Wireless Investment, Inc (“USCC”)." | D3 | p. 4 of 14 | [x] verified by user |
| 6 | U.S. Cellular | TDS | US | "approximately 80%" (conflicts with 84.26% in P1/D1 — keep both, different dates/complaints) | — | "Telephone and Data Systems, Inc. (“TDS”) is a publicly held corporation that owns approximately 80% of Defendant (2) United States Cellular Corporation" | D3 | p. 4 of 14 | [x] verified by user |
| 7 | each DE | U.S. Cellular entities | US | **Alleged** sham / front (from the 2008 complaint, quoted by court) | 2004–2008 | "acted as fronts for the [U.S. Cellular entities] to acquire licenses to complement [their] existing wireless operating footprint" | D3 | p. 6 of 14 | [x] verified by user |
| 8 | Equity % of USCC in each LP | — | — | — | — | **UNSUPPORTED** (not stated in D3) | — | — | [x] verified by user |
| 9 | King Street, Inc. | Allison Cryor DiNardo | US (VA resident) | sole shareholder (D1 also calls her its "general partner", as written) | — | "Defendant Allison Cryor DiNardo is a Virginia resident who is the sole owner of Defendant Nonesuch, Inc. and the sole shareholder and general partner of Defendant King Street, Inc. Id. ¶16-17." | D1 (P1's opinion, 20-cv-2070) | p. 4 of 14 | [x] quote found by user in D1; status **alleged** (cites complaint ¶16-17), confirmed by user |
| 10 | King Street Wireless, L.P. | King Street, Inc. | US | general partner (no %) | — | "King Street, Inc. is the general partner in Defendant King Street Wireless, L.P. (“King Street, L.P.”), a limited partnership that obtained 152 spectrum licenses in the 700 MHz band in FCC Auction 73. Id." | D1 | p. 4 of 14 | [x] quote found by user in D1; status **alleged** (cites complaint), confirmed by user |
| 11 | King Street Wireless, L.P. | USCC Wireless Investment, Inc. | US | limited partner (no %) | — | "USCCWI is a limited partner in King Street, L.P. Id. ¶ 16." | D1 | p. 4 of 14 | [x] quote found by user in D1; status **alleged** (cites complaint ¶16), confirmed by user |

- **Rows 1–3 split into one hop per row (1a/1b/1c etc.).** D3 calls each L.P. "a limited partnership between USCC and" the Inc., but doesn't say which is general vs limited partner; the roles in 1a–3b follow the structure described elsewhere (D1 rows 10–11 for King Street). **Defined-term caution:** D3 writes "Carroll PCS, Inc. (“Carroll Wireless”)", "Barat Wireless, Inc. (“Barat Wireless”)" and "King Street Wireless, Inc. (“King Street”)", so later uses of those short names in D3 may mean the Inc., not the L.P.
- **Second source (found by user):** D1 (P1's D.D.C. opinion of Mar. 31, 2022, 20-cv-2070, p. 4 of 14) independently describes the King Street structure from rows 3 and 5. Rows 9–11 corroborate rows 3 and 5 from a different case's opinion.
- **Name discrepancy:** D1 names the GP "King Street, Inc."; D3 names it "King Street Wireless, Inc." Very likely the same company, but no document says so; treat the two as **possibly same** (separate records, linked), not merged.
- **Cross-case link in one document:** D1 places DiNardo as owner of the GP entities in both P1 (Nonesuch → Frequency Advantage → Advantage Spectrum) and P2 (King Street, Inc. → King Street Wireless, L.P.), with USCCWI as LP in both. This "reused principals" pattern is a key evaluation signal and confirms P1 and P2 must be held out together.

- **Amounts (D3 p. 5 of 14):**
  - Carroll paid "$129.7 million of the $151.8 million"
  - Barat paid "$127.1 million for its $169 million bid"
  - King Street paid "$300.4 million for its $400.6 million bid"
- **Raw-data pointer:** "FCC ULS File No. 0003379814" (King Street's response to the Bureau inquiry, D3 p. 6).
- **Data the tool needs:** FCC ULS (Form 175/601/602 for Auctions 58/66/73, plus the 2012 transfer-of-control applications) and SEC Exhibit 21. GLEIF is unlikely to cover the LPs.
- **Suitability:** **Strong for structure.** The repeated DiNardo-owned GP + USCCWI LP pattern across four DEs (with P1) is exactly a "relay reuse" signature. Hold out P1 and P2 together, or the tool learns the pattern from one and applies it to the other.
- **Weaknesses:**
  - The control claim was never adjudicated; the case was dismissed on public-disclosure grounds.
  - The LP percentages are not in this opinion.

## P3. Maritime Communications/Land Mobile, LLC (Auction 61, AMTS) — FCC 11-64 Hearing Designation Order

- **Jurisdiction:** US (FCC, EB Docket No. 11-71).
- **Years active:**
  - Short-form filed June 9, 2005.
  - Hearing designated Apr. 19, 2011.
  - Later ALJ and Commission outcome: **UNKNOWN** (not opened).
- **Exit node:** Maritime Communications/Land Mobile, LLC.
- **Relays:** S/RJW Partnership, Ltd.; Communications Investments, Inc.
- **Entry nodes:** Sandra M. DePriest (disclosed, 100%); Donald R. DePriest (her spouse; **alleged** real party in interest and de facto controller).
- **Credit:** "$2,737,000" on a "$7,820,000 winning bid" (p. 30155, ¶ 12).
- **Source read (F1):** FCC 11-64 as reprinted at 76 Fed. Reg. 30154–30168 (May 24, 2011), FR Doc. 2011-12792 — https://www.govinfo.gov/content/pkg/FR-2011-05-24/pdf/2011-12792.pdf (the FCC original was not opened).

| # | From | To | Jur. | Equity / control | Date | Quote | Page / ¶ | |
|---|---|---|---|---|---|---|---|---|
| 1 | MC/LM LLC | S/RJW Partnership, Ltd. | US | 100% membership | 2005 | "One hundred percent of the membership interests in Maritime Communications/Land Mobile, LLC are owned by S/RJW Partnership, Ltd." | p. 30161, ¶ 37 | [x] verified by user |
| 2 | S/RJW Partnership | Communications Investments, Inc. | US | general partner | 2005 | "The general partner in S/RJW Partnership, Ltd. is Communications Investments, Inc." | p. 30161, ¶ 37 | [x] verified by user |
| 3 | Communications Investments, Inc. | Sandra M. DePriest | US | 100% shares | 2005 | "One hundred percent of the shares in Communications Investments, Inc. are owned by Sandra M. DePriest." | p. 30161, ¶ 37 | [x] verified by user |
| 4 | S/RJW Partnership | Sandra M. DePriest | US | 100% partnership shares | 2005 | "One hundred percent of the partnership shares in S/RJW Partnership, Ltd. are owned by Sandra M. DePriest." | p. 30161, ¶ 37 | [x] verified by user |
| 5 | MC/LM | Donald R. DePriest | US | **alleged** real party in interest / de facto control; 0% disclosed equity | 2005– | "there is credible evidence suggesting that Donald DePriest was a real party in interest behind Maritime and exercised de facto control of Maritime" | p. 30155, ¶ 4 | [x] verified by user |
| 6 | MC/LM | Donald R. DePriest | US | undisclosed spousal interest | 2005 | "Maritime failed to list Sandra DePriest's spouse, Donald DePriest, as a disclosable interest holder, on either the short-form or the long-form applications" | p. 30155, ¶ 11 | [x] verified by user |
| 7 | MariTEL, Inc. (other licensee) | MCT Investors, LP | US | 58.3% voting / 26.1% total | Form 602, Mar. 13, 2001 | "MariTEL indicated that MCT Investors, LP held 58.3% of MariTEL’s issued and outstanding voting stock (and 26.1% of all stock, voting and non-voting), that MedCom Development Corporation was the sole general partner of MCT Investors, LP, and that Donald DePriest was the sole shareholder of MedCom Development Corporation. See, e.g., FCC File No. 0002080704 (filed Mar. 13, 2001)." | p. 30157–58, n.35 | [x] verified (stated: MariTEL’s own Form 602, FCC File No. 0002080704, as cited in n.35) |
| 8 | MCT Investors, LP | MedCom Development Corp. | US | sole GP | 2001 | same quote as above (7) | p. 30158, n.35 | [x] verified (stated: MariTEL’s own Form 602, FCC File No. 0002080704, as cited in n.35) |
| 9 | MedCom Development Corp. | Donald R. DePriest | US | sole shareholder | 2001 | same quote as above (7) | p. 30158, n.35 | [x] verified (stated: MariTEL’s own Form 602, FCC File No. 0002080704, as cited in n.35) |
| 10 | Charisma Broadcasting Co.; Bravo Communications, Inc.; Golden Triangle Radio, Inc. | Donald R. DePriest | US | controlled (undisclosed affiliates) | disclosed late | "Donald DePriest actually controlled three more entities: Charisma Broadcasting Co., Bravo Communications, Inc., and Golden Triangle Radio, Inc." | p. 30155, ¶ 5 | [x] verified by user |

- **Status labels (confirmed by user 2026-10-25):** rows 1–4 and 7–9 **stated**; rows 5, 6 and 10 **alleged**.
- **Raw-data pointer (found by user):** rows 7–9 come from MariTEL’s own Form 602, FCC File No. 0002080704 (filed Mar. 13, 2001), cited in n.35. Reading that filing directly in ULS would replace the FCC’s summary with the original.
- **Data the tool needs:** FCC ULS (Form 175/601/602; MariTEL Form 602) and state registries (MS/DE/VA, states UNSUPPORTED). The chain is mostly in FCC data, and GLEIF is unlikely to have it. The tool would need a person-to-person (spouse) link source, which is not in FCC data.
- **Suitability:** **Strong.**
  - The disclosed chain ends at Sandra DePriest, and the hidden controller is linked via marriage and his other FCC filings (MariTEL Form 602).
  - It is a good test of person-level entity resolution and "control without equity."
- **Weaknesses:**
  - A hearing designation order states issues and allegations, not findings.
  - The final disposition was not checked.

## P4. DISH / Northstar Wireless / SNR Wireless (AWS-3 Auction 97)

- **Jurisdiction:** US (FCC 15-104, 30 FCC Rcd 8887 (2015); FCC 20-160 (2020); SNR Wireless LicenseCo v. FCC, 868 F.3d 1021 (D.C. Cir. 2017); Northstar Wireless v. FCC, No. 18-1209 (D.C. Cir. 2022)).
- **Years active:** 2014–2022.
- **Exit nodes:** Northstar Wireless, LLC; SNR Wireless LicenseCo, LLC.
- **Relays:** Northstar Spectrum, LLC; Northstar Manager, LLC; SNR Wireless HoldCo, LLC; American AWS-3 Wireless II / III L.L.C. (DISH subsidiaries).
- **Entry node:** DISH Network Corp. (85% indirect equity; de facto control found by the FCC).
- **Amounts:** "$13,327,423,700" in bids and credits of "roughly $3.3 billion" (2017 slip op. p. 9).
- **Sources read:**
  - **J1:** D.C. Cir. No. 15-1330 (Aug. 29, 2017) — https://cases.justia.com/federal/appellate-courts/cadc/15-1330/15-1330-2017-08-29.pdf
  - **J2:** D.C. Cir. No. 18-1209 (June 21, 2022) — https://cases.justia.com/federal/appellate-courts/cadc/18-1209/18-1209-2022-06-21.pdf
  - FCC 15-104 (https://docs.fcc.gov/public/attachments/FCC-15-104A1.pdf) was **not opened**.

| # | From | To | Jur. | Equity / control | Date | Quote | Source | Page | |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Northstar Wireless; SNR LicenseCo | DISH (indirect) | US | 85% indirect | 2014 | "DISH acquired an (indirect) eighty-five percent ownership interest in each company." | J1 | slip op. p. 8 | [x] verified by user |
| 2 | both | DISH via wholly owned subsidiaries | US | 85% | 2015 Order | "DISH, which held an 85% stake in each company. See 2015 Order, 30 FCC Rcd. at 8893–8894 ¶¶ 14, 17; see also id. (noting that DISH holds its shares in the Companies through wholly owned subsidiaries)" | J2 | p. 8 | [x] verified by user |
| 3 | Northstar Spectrum, LLC | Northstar Manager, LLC; American AWS-3 Wireless II L.L.C. | US | parties to LLC agreement (no %) | June 7, 2018 | "Third Amended and Restated Limited Liability Company Agreement of Northstar Spectrum, LLC by and Between Northstar Manager, LLC and American AWS-3 Wireless II L.L.C. (June 7, 2018)" | J2 n.8 | pp. 17–18 | [x] verified by user |
| 4 | SNR Wireless LicenseCo | SNR Wireless HoldCo (guarantor); American AWS-3 Wireless III (lender) | US | credit relationship only — not equity | Oct. 13, 2014 | "Credit Agreement By and Among American AWS-3 Wireless III L.L.C. (as Lender) and SNR Wireless LicenseCo, LLC (as Borrower) and SNR Wireless HoldCo, LLC (as Guarantor)" | J2 n.12 | p. 26 | [x] verified by user |
| 5 | Northstar / SNR | DISH | US | financing-based control | 2015 | DISH "provided equity contributions and loans ... that account[ed] for approximately 98 percent of the [petitioners'] winning bid amounts" | J1 | pp. 18–19 | [x] verified by user |
| 6 | Northstar | DISH | US | "all but three percent" of common shares | late 2020 | "In late 2020, DISH acquired all but three percent of Northstar's outstanding common shares from Northstar's managing shareholders." | J2 | p. 17 | [x] verified by user |
| 7 | Northstar Wireless → Northstar Spectrum; Northstar Manager → Doyon, Ltd. (~40.1%?); SNR LicenseCo → SNR HoldCo → SNR Wireless Management / John Muleta (Atelum?); American II/III → DISH | | | | | **UNSUPPORTED** — likely in FCC 15-104 ¶¶ 14–17 (not opened); Doyon % only in secondary press. | — | — | [x] checked by user; still **UNSUPPORTED** (no primary quote) |

- **Data the tool needs:** FCC ULS (Form 175, long-form 601 ownership exhibits, Form 602) and DISH SEC filings. State registries (DE; AK for Doyon) would also be needed. GLEIF probably covers DISH but not the LLCs.
- **Suitability:** **Moderate.** The 85% DISH interest was *disclosed*, so it is not a hidden-owner case. Use it as a "control without majority-of-control equity / disclosed-but-disputed" case, or to test whether the tool flags DISH from the filings.
- **Weaknesses:** the inner hops are unsupported until FCC 15-104 is opened.

## P5. U.S. ex rel. Taylor v. Gabelli (Lynch Interactive designated entities)

- **Jurisdiction:** US (S.D.N.Y. No. 03 Civ. 8762 (SAS), 345 F. Supp. 2d 313 (July 29, 2004)).
- **Years active:** FCC auctions from the late 1990s to the early 2000s. A reported $130M settlement without admission is **secondary** knowledge only (the DOJ release was not opened).
- **Exit nodes:** bidder LPs, e.g., Fortunet Wireless, High Country, New England Wireless, Southeast Wireless, Aer Force, BAL/Rivgam, BCK/Rivgam, Betapage, PTPMS, PTPMS II, Theta.
- **Entry node:** Mario Gabelli / "Gabelli-related entities" (**alleged**).
- **Source read:** https://case-law.vlex.com/vid/u-s-ex-rel-887089102 (commercial reprint; reporter page numbers not shown). Official copy not found.

| # | From | To | Equity / control | Quote | Location | |
|---|---|---|---|---|---|---|
| 1 | each bidder LP | indirect owner / direct owner | 49.9% / 50.1% | "These bidders were organized as limited partnerships, held by "indirect" (49.9%) and "direct" (50.1%) owners." | Background | [x] verified by user |
| 2 | New England Wireless; High Country; Southeast Wireless; Fortunet Wireless; Aer Force B; Betapage/PTPMS/PTPMS II; BAL/Rivgam; BCK/Rivgam; Theta | Lynch PCS B / C / D / E / F; Lynch Paging; Rivgam LLC; Rivgam LMDS; Theta II (indirect owners) | ~49.9% | "Lynch PCS B (New England Wireless); Lynch PCS C (High Country); Lynch PCS D (Southeast Wireless); Lynch PCS E (Fortunet Wireless); Lynch PCS F (Aer Force B); Lynch Paging (Betapage, PTPMS, and PTPMS II); Rivgam LLC (BAL/Rivgam); Rivgam LMDS (BCK/Rivgam); and Theta II (Theta)." | Background | [x] verified by user |
| 3 | same bidders | FWCC, HCCC, NEWC, SWCC, Aer Force, Inc., Theta I/IA (direct owners) | ~50.1% | "FWCC (Fortunet Wireless); HCCC (High Country); NEWC (New England Wireless); SWCC (Southeast Wireless); Theta I (Theta)…" (fragment) | Background | [x] verified by user |
| 4 | bidders and their direct/indirect owners | Gabelli / Gabelli-related entities | **alleged** creator/controller | "Gabelli and the so-called Gabelli-related entities, which are alleged to have created "sham" bidding entities as well as direct and indirect owners of these bidders" | Background | [x] verified by user |
| 5 | Lynch PCS A–F / Lynch Paging | Lynch Interactive Corp. → Gabelli | — | **UNSUPPORTED** (not stated in the opinion as read) | — | n/a: gap, no primary source yet (nothing to verify) |

- **Data the tool needs:** historical ULS records (1990s–2000s), Lynch Interactive SEC Exhibit 21, and state registries.
- **Suitability:** **Moderate to weak.** The nominee "direct owner" 50.1/49.9 pattern is useful, but control is alleged only, the case settled without admission, the old data is sparse, and the top hop is unsupported.

## P6–P9. Chinese state-owned carriers (Section 214 authorizations)

- **Source for all four (S1):** U.S. Senate Permanent Subcommittee on Investigations staff report, *Threats to U.S. Networks: Oversight of Chinese Government-Owned Carriers* (June 9, 2020) — https://www.govinfo.gov/content/pkg/GOVPUB-Y4_G74_9-PURL-gpo142492/pdf/GOVPUB-Y4_G74_9-PURL-gpo142492.pdf
  - It is a primary government document, but it summarizes FCC and Executive Branch records.
  - Page numbers are the report's printed pages (PDF page = printed + 4, per the extraction).
  - Percentages marked "diagram" are read from embedded ownership charts and are approximate.
- **FCC orders not opened (DNS failure):**
  - FCC 19-38 (China Mobile USA): https://docs.fcc.gov/public/attachments/FCC-19-38A1.pdf
  - FCC 21-114 (CTA): https://docs.fcc.gov/public/attachments/FCC-21-114A1.pdf
  - China Unicom Americas revocation (2022, GN Docket 20-110): order number unconfirmed
  - FCC 22-22 (PacNet/ComNet): order number from search-result title only
- **Data the tool needs (all four):** these are Section 214 authorizations, **not in FCC ULS / Form 602**.
  - Ownership (≥10% holders under 47 CFR 63.18(h)) is in the FCC international filings database (IBFS/ICFS) and the revocation dockets.
  - Upper hops come from the parents' SEC 20-Fs (China Mobile Ltd, CTCL and China Unicom HK were NYSE-listed until ~2021) and HKEX annual reports.
  - GLEIF likely holds LEIs for the listed parents. No LEI or GLEIF relationship was verified.
- **Suitability:** these are good tests of recovering a foreign-state owner over 3–5 hops. They are **not concealment cases**: ownership was disclosed to the FCC.

### P6. China Mobile International (USA) Inc. — FCC 19-38 (May 10, 2019) denial
- **Exit node:** China Mobile International (USA) Inc. (Delaware; Section 214 applicant, never authorized).
- **Entry node:** PRC government / SASAC.

| # | From | To | Jur. | Equity / control | Date | Quote | Page | |
|---|---|---|---|---|---|---|---|---|
| 1 | China Mobile USA | China Mobile International | DE → (UNSUPPORTED) | subsidiary | May 2011 | "China Mobile USA, a subsidiary of China Mobile International, was registered in Delaware in May 2011" | p. 50 | n/a: gap, no primary source yet (nothing to verify) |
| 1b | China Mobile USA | China Mobile International (UK) Limited (immediate parent) | UK (from name only) | immediate parent; "majority controlled by China Mobile Communications Corporation" | Jan 2015 | "In January 2015, China Mobile (USA) alerted the FCC that its immediate parent company had been transferred to China Mobile International (UK) Limited, which was also majority controlled by China Mobile Communications Corporation." | p. 52, fn. 270 | [x] verified by user |
| 2 | China Mobile USA | China Mobile Limited | HK (listed) | wholly owned, indirect (diagram 100%) | — | "a wholly-owned subsidiary of China Mobile" (fragment) | p. 52 + diagram | [x] verified by user |
| 3 | China Mobile Ltd | China Mobile Communications Corp. (CMCC) | PRC | "more than 70 percent" (diagram 73%, indirect) | 2011 | "China Mobile Communications Corporation owned more than 70 percent of China Mobile." | p. 52 | [x] verified by user |
| 4 | CMCC | PRC government / SASAC | PRC | 100% direct | — | "The Chinese government holds a direct 100 percent ownership interest in China Mobile Communications Corporation." | p. 52 | [x] verified by user |
| 5 | Intermediates between China Mobile International and China Mobile Ltd (e.g., BVI holding companies) | | | | | **UNSUPPORTED** | — | n/a: gap, no primary source yet (nothing to verify) |

### P7. China Telecom (Americas) Corp. (CTA) — FCC 21-114 revocation (Oct. 2021)
- **Exit node:** CTA (Delaware; Section 214 authority since 2002).
- **Entry node:** SASAC / State Council.
- **Appeal:** the D.C. Cir. upheld the revocation (No. 21-1233, Dec. 2022). The opinion is listed as sealed on FindLaw and was not read.

| # | From | To | Jur. | Equity / control | Date | Quote | Page | |
|---|---|---|---|---|---|---|---|---|
| 1 | CTA | China Telecom Corporation Limited (CTCL) | DE → PRC | "full equity interest" (diagram 100%) | 2007– | "In 2007, China Telecom restructured its operations, with China Telecom Corporation Limited (“CTCL”)—also a Chinese company—acquiring full equity interest in CTA from China Telecom." | pp. 57–58; diagram p. 72 | [x] verified by user |
| 1-pre | CTA | China Telecommunications Corp. | PRC | "100% owned by [a People’s Republic of China] state-owned entity" | 2001–2007 | (FCC wording quoted by PSI) | p. 57 | [x] verified by user |
| 2 | CTCL | China Telecommunications Corp. ("China Telecom") | PRC | 70.89% (diagram; PSI's source is the Executive Branch recommendation, which was not opened) | ~2020 | diagram label "70.89%"; fn. 423 cites "Executive Branch Recommendation re CTA, supra note 56, at 33" | p. 72 | [x] verified by user |
| 3 | China Telecommunications Corp. | SASAC | PRC | control | — | "CTA is ultimately owned and controlled, through CTCL and China Telecom, by SASAC" | p. 71 | [x] verified by user |

### P8. China Unicom (Americas) Operations Ltd. (CUA) — FCC 22-9 revocation (adopted Jan. 27, 2022)
- **Exit node:** CUA. Its state of incorporation is UNSUPPORTED.
- **Entry node:** SASAC.

| # | From | To | Jur. | Equity / control | Date | Quote | Page | |
|---|---|---|---|---|---|---|---|---|
| 1 | CUA | China Unicom Global Limited | HK | 100% | 2017–2020 | "CUA is a wholly-owned subsidiary of China Unicom Global Limited" | p. 78 | [x] verified by user |
| 2 | China Unicom Global | China Unicom (Hong Kong) Limited | HK | 100% | same | "which is wholly-owned by China Unicom (Hong Kong) Limited" | p. 78 | [x] verified by user |
| 3 | China Unicom (HK) | China United Network Communications Group Co. Ltd., via unnamed intervening holding companies | PRC | "approximately 52.1 percent" | ~2020 | "Through multiple intervening holding companies, China Unicom owns approximately 52.1 percent of China Unicom Hong Kong." | p. 78 | [x] verified by user |
| 4 | China Unicom Group | SASAC | PRC | "approximately 98 percent" | ~2020 | "SASAC currently owns approximately 98 percent of China Unicom." | p. 77 | [x] verified by user |
| 5 | Names of the intervening holding companies in hop 3 | | | | | **UNSUPPORTED** | — | n/a: gap, no primary source yet (nothing to verify) |

### P9. Pacific Networks Corp. / ComNet (USA) LLC — FCC 22-22 revocation (adopted Mar. 16, 2022)
- **Exit nodes:** ComNet (USA) LLC (Delaware, formerly CM Tel (USA) LLC); Pacific Networks Corp.
- **Entry node:** CITIC Group Corp. → PRC government.
- **Appeal:** D.C. Cir. No. 22-1054 (2023), not read.

| # | From | To | Jur. | Equity / control | Date | Quote | Page | |
|---|---|---|---|---|---|---|---|---|
| 0 | ComNet (then CM Tel (USA) LLC) | CM Telecom International Limited | DE → HK | subsidiary | 1999–2009 | "ComNet (then CM Tel (USA) LLC) was incorporated in Delaware in July 1999. At that time, the company was a subsidiary of CM Telecom International Limited, a Hong Kong based company." | p. 84 | [x] verified by user |
| 1 | ComNet | Pacific Networks Corp. | US | 100% | 2009– | "CITIC made ComNet a wholly-owned subsidiary of Pacific Networks." | p. 85 | [x] verified by user |
| 2 | Pacific Networks | CITIC Telecom International Holdings Ltd (formerly CITIC 1616 Holdings) | HK | "indirectly wholly owned" (diagram 100%) | 2008 filing | "CITIC 1616 [Holdings Limited] will acquire CM Tel (USA) LLC through CITIC 1616’s indirectly wholly owned subsidiary, Pacific Networks Corp." | p. 85, fn. 531; diagram p. 95 | [x] verified by user |
| 3 | CITIC Telecom Intl | CITIC Limited | HK | approx. 58%, indirect (diagram) | ~2020 | diagram label "Approx. 58%" | p. 95 | [x] verified by user |
| 4 | CITIC Limited | CITIC Group Corp. | PRC | majority / approx. 58% (diagram) | ~2020 | "CITIC is majority-owned by CITIC Group Corporation (“CITIC Group”)" — note: in the text "CITIC" is defined as CITIC Telecom; the diagram inserts CITIC Limited between them (ambiguity in source) | p. 94; diagram p. 95 | [x] verified by user |
| 5 | CITIC Group | PRC government | PRC | 100% | — | "“a wholly state-owned company in the [People’s Republic of China].”" | p. 94 | [x] verified by user |

- **Conflicting figures (keep all):**
  - "14 percent indirect ownership (29 percent attributable interest)" (2007, p. 86)
  - "57.6 percent attributable interest" (2009 filing, fn. 556, p. 88)
  - ~58% × ~58% look-through (2020 diagram)
- **Change over time:** a 2008 transfer of control from CITIC Pacific Limited to CITIC Group (fn. 555, p. 88) means the intermediate entity changed. Use date-bounded edges.

## P10–P12 (and Azerfon). Uzbek bribery / Azerbaijan cases

**Status: the DOJ and SEC documents for these cases were found but NOT opened** (justice.gov and sec.gov failed DNS). Every hop that depends on them is UNSUPPORTED. Three primary documents *were* read. Their quotes were extracted with `pdftotext`; the Telia report has two-column layout, so its quotes run across columns. Page numbers are PDF page indexes.
- **[A] VimpelCom Ltd 2015 Form 20-F** (the company's own copy): https://www.veon.com/fileadmin/user_upload/investors/reports/2016/vimpelcom-ltd-2015-20-f.pdf. The EDGAR copy https://www.sec.gov/Archives/edgar/data/0001468091/000119312516525094/d194450d20f.htm was not opened.
- **[B] TeliaSonera Annual and Sustainability Report 2014:** https://www.teliacompany.com/assets/u5c1v3pt22v8/4IFBqoKS38IfsxEFOdXBLa/20e8e22a135d38ccef7fab1838ef0f5a/TeliaSonera_Annual_and_Sustainability_Report_2014_eng.pdf
- **[C] Telenor Group letter to the Norwegian Ministry of Trade (NFD), 2016-02-23:** https://www.telenor.com/wp-content/uploads/2014/12/160223-NFD_orientering-fra-Telenor-Group_VimpelCom.pdf. Telenor was a VimpelCom shareholder. This is a Norwegian-language summary of the DOJ/SEC resolutions, so treat it as **one step removed** from DOJ.

### P10. VimpelCom (VEON) / Unitel LLC, Uzbekistan — Takilant
- **Jurisdiction:** UZ / US (S.D.N.Y. 16-cr-137) / NL.
- **Years active:** 2006–2012. Resolved Feb. 18, 2016.
- **Exit node:** Unitel LLC.
- **Relays:** VimpelCom Ltd (Bermuda; jurisdiction UNSUPPORTED here) and Takilant Ltd (Gibraltar; UNSUPPORTED).
- **Entry node:** the "Foreign Official", reported as Gulnara Karimova (secondary only).

| # | From | To | Jur. | Equity / control | Date | Quote | Source | Page | |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Unitel LLC | VimpelCom group | UZ | 100% | 2014–2015 | `LLC "Unitel" . . . Uzbekistan Operating 100% 100%` (subsidiary table) | [A] | PDF p. 259 (F-45) | [x] verified by user |
| 2 | Unitel (indirect interest) | Takilant | GI? | indirect stake + option ($20M, exercised 2009 for $57.5M); **no %** | ~2007–2009 | "VimpelCom solgte en indirekte eierandel i Unitel til Takilant og inngikk samtidig en opsjonsavtale for 20 millioner USD som ble utøvet i 2009 for 57,5 millioner USD" | [C] | p. 2 | [x] verified by user |
| 2b | Buztel (later merged into Unitel) | Takilant | GI? | indirect ownership interest | 2006 | "kjøpet av Buztel, der Takilant hadde en indirekte eierandel, for 60 millioner USD" | [C] | p. 2 | [x] verified by user |
| 3 | Takilant | "Uzbek government official" | — | control | 2006–2012 | "VimpelCom kjente til at Takilant var kontrollert av en usbekisk myndighetsperson." | [C] | p. 2 | [x] verified by user |
| 4 | Hops 2–3 with exact % from DOJ / SEC | — | — | **UNSUPPORTED** (not opened) | — | — | DOJ SOF https://www.justice.gov/usao-sdny/file/826456/dl?inline= ; SEC https://www.sec.gov/files/litigation/complaints/2016/comp-pr2016-34.pdf | — | n/a: gap, no primary source yet (nothing to verify) |
| 5 | "Foreign Official" = Gulnara Karimova | — | — | **UNSUPPORTED** (anonymized in DOJ documents; named in DOJ forfeiture filings, which were not opened) | — | — | — | — | n/a: gap, no primary source yet (nothing to verify) |

- **Context:** [A] PDF p. 286 says: "including VimpelCom, Unitel and Takilant".
- **Data needed:** SEC 20-F, DOJ/SEC documents, Gibraltar registry. GLEIF may cover VEON (unconfirmed). Nothing here is in FCC.
- **Suitability:** good *after* the DOJ Statement of Facts is opened. The Takilant stake is missing from the company's own subsidiary table, which is the realistic "hidden" condition.

### P11. Telia / OOO Coscom (Ucell), Uzbekistan — Takilant
- **Jurisdiction:** UZ / NL / US / SE.
- **Years active:** 2007–2010+. Resolved Sept. 2017.
- **Exit node:** OOO Coscom (Ucell).
- **Relays:** TeliaSonera Uzbek Telecom Holding B.V. ("Uzbek Holding", NL); an unnamed minority holder (Takilant per DOJ/SEC, UNSUPPORTED).
- **Entry node:** "Government Official A" (reported as Karimova; secondary only).

| # | From | To | Jur. | Equity / control | Date | Quote | Source | Page | |
|---|---|---|---|---|---|---|---|---|---|
| 1 | OOO Coscom | Uzbek Holding | UZ→NL | parent | 2014 | "For Uzbek Holding, the parent company of the mobile operator OOO Coscom in Uzbekistan" | [B] | p. 132 | [x] verified by user |
| 2 | Uzbek Holding | TeliaSonera | NL→SE | 94% after 2010 | 2010 | "In 2010, TeliaSonera acquired 20 percent of the shares in Uzbek Holding resulting in a total holding of 94 percent." | [B] | p. 132 | [x] verified by user |
| 2b | Ucell | TeliaSonera | — | 94.0% owned / 100% consolidated | 2014 | `Ucell 94.0% 100% Mobile` | [B] | p. 10 | [x] verified by user |
| 3 | Uzbek Holding | **unnamed** non-controlling holder | ? | 26% (2007–2010) → 6% (put exercisable after Feb. 15, 2013) | 2007– | "in exchange for cash and a 26 percent interest in Uzbek Holding" … "The put option refers to 6 percent of the shares and is exercisable after February 15, 2013." | [B] | p. 132 | [x] verified by user |
| 4 | unnamed holder = Takilant | — | — | **UNSUPPORTED** (SEC Order 34-81669 https://www.sec.gov/files/litigation/admin/2017/34-81669.pdf and DOJ https://www.justice.gov/usao-sdny/press-release/file/997846/dl not opened) | — | — | — | — | n/a: gap, no primary source yet (nothing to verify) |
| 5 | Takilant | Government Official A | — | beneficial owner | — | **UNSUPPORTED** | — | — | n/a: gap, no primary source yet (nothing to verify) |

- **Suitability:** **strong design.** A primary company report shows an anonymous 26%/6% holder that the tool must resolve. Usable once the SEC order is opened.
- **Weaknesses:** the owner is anonymized in US documents, and the Swedish criminal trial ended in acquittal (secondary).

### P12. MTS / Uzdunrobita, Uzbekistan — Swisdorn, Takilant, KolorIt
- **Jurisdiction:** UZ / US (DOJ; SEC). Years: 2004–2012.
- **Exit node:** Uzdunrobita (MTS's Uzbek mobile operator).
- **Relays:** Swisdorn (to 2004); Takilant Ltd and Takilant's unnamed subsidiary (2008); KolorIt Design (2009); an unnamed proxy (nominee) of Government Official A.
- **Entry node:** "Government Official A" (unnamed in both documents; "her"; described as a relative of the Uzbek president). Identity in press reports is secondary only, so **don't name her in ground truth**.
- **Sources read by user:**
  - **M1:** DOJ Statement of Facts — https://www.justice.gov/archives/opa/press-release/file/1141616/dl ("first document")
  - **M2:** SEC Order, Rel. No. 34-85261 (2019) — https://www.sec.gov/files/litigation/admin/2019/34-85261.pdf ("second document")
- **Status labels:** hops from M1 are **admitted** (DOJ statement of facts admitted by MTS); hops from M2 are **settled findings** (SEC order; neither admitted nor denied).
- **Documents confirmed by user:** M1 = DOJ Statement of Facts, M2 = SEC Order 34-85261.

| # | From (child) | To (parent) | Jur. | Equity / control as stated | Date | Quote | Source | Page | |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Uzdunrobita | MTS | UZ → RU | 74%–100% of shares (range) | 2004–2012 | "From in and around 2004 to 2012, MTS held between 74% and 100% of the shares of Uzdunrobita." | M1 | p. 3 | [x] verified by user (quote supplied by user) |
| 2 | Uzdunrobita | Swisdorn | UZ | vehicle for Government Official A's 59% beneficial stake (Swisdorn's own registered % not separately stated) | before July 2004 | "At the time, Government Official A beneficially owned 59% of Uzdunrobita’s shares through Swisdorn and chaired Uzdunrobita’s supervisory board." | M2 | p. 3 | [x] verified by user (quote supplied by user) |
| 3 | Swisdorn | Government Official A | — | beneficial owner (59% of Uzdunrobita through Swisdorn) | before July 2004 | same quote as 2 | M2 | p. 3 | [x] verified by user (quote supplied by user) |
| 4 | Uzdunrobita | Government Official A | — | **control:** chaired supervisory board (0% direct equity stated) | before July 2004 | same quote as 2 | M2 | p. 3 | [x] verified by user (quote supplied by user) |
| 5 | Uzdunrobita | MTS (acquisition) | — | bought 74% for $121M: 33% from Swisdorn ($100M, mostly an illicit payment) and 41% from another seller | July 2004 | "In July 2004, MTS purchased 74% of the shares of Uzdunrobita for $121 million. MTS paid $100 million to Swisdorn for 33% of the shares of Uzdunrobita, which represented a significantly higher value per share than the amount paid to the other seller, which sold MTS 41% of the shares of Uzdunrobita." | M2 | p. 3 (¶ J) | [x] verified by user (quote supplied by user) |
| 6 | Uzdunrobita | Government Official A (via local manager) | — | **control (indirect):** managed by a local manager with a personal relationship to her | 2004–2012 | "From that point forward until 2012, Uzdunrobita was managed by a local manager who had a personal relationship with Government Official A." | M2 | p. 3 (¶ K) | [x] verified by user (quote supplied by user) |
| 7 | Takilant Ltd | Government Official A | — | beneficial owner | Aug. 2008 | "...a $30 million payment to Takilant Ltd, which was beneficially owned by Government Official A." | M2 | pp. 5–8 (¶ T) | [x] verified by user (quote supplied by user) |
| 8 | Takilant Ltd | Proxy of Government Official A (unnamed) | — | registered director **and** shareholder (no %) | 2008 | "...Takilant's certificates of incorporation and corporate registration, both of which identified a proxy of Government Official A as Takilant's director and shareholder." | M2 | pp. 5–8 (¶ X) | [x] verified by user (quote supplied by user) |
| 9 | Proxy of Government Official A | Government Official A | — | **nominee / proxy** relationship (the registered owner acts for the hidden one) | 2008–2009 | same quote as 8; also ¶ W: "Takilant's nominal owner had no telecommunications background and was a known proxy for Government Official A" | M2 | pp. 5–8 (¶¶ W, X) | [x] verified by user (quote supplied by user) |
| 10 | Takilant's subsidiary (unnamed; held 800 MHz rights) | Takilant Ltd | — | subsidiary (no %) | Aug. 2008 | "Takilant and an MTS subsidiary executed an agreement under which Takilant’s subsidiary would waive its rights to the 800 MHz frequencies" | M2 | pp. 5–8 (¶ U) | [x] verified by user (quote supplied by user) |
| 11 | KolorIt Design | Government Official A | UZ | **control:** "indirectly controlled" (before sale) | to Sept. 2009 | "Uzdunrobita and MTS acquired 100% of an Uzbek advertising company named KolorIt Design (\"KolorIt\") that Government Official A indirectly controlled." | M2 | pp. 5–8 (¶ CC) | [x] verified by user (quote supplied by user) |
| 12 | KolorIt Design | Proxy of Government Official A (same person as row 8) | UZ | one of two listed shareholders (no %) | 2009 | "The firm reported that one of KolorIt's two listed shareholders was the same proxy of Government Official A who had appeared in the records of Takilant." | M2 | pp. 5–8 (¶ DD) | [x] verified by user (quote supplied by user) |
| 13 | KolorIt Design | Uzdunrobita and MTS | UZ | 100% (combined; split not stated) | Sept. 2009 | same quote as 11 | M2 | pp. 5–8 (¶ CC) | [x] verified by user (quote supplied by user) |
| 14 | Uzdunrobita; KolorIt | "Executive 1" (unnamed MTS executive) | — | **control:** authority over MTS's foreign subsidiaries | 2007–2013 | "“Executive 1,” an individual whose identity is known to the United States, was a high-ranking executive of MTS who had authority over MTS’s foreign subsidiaries, including Uzdunrobita and KOLORIT, from in or around 2007 to 2013." | M1 | p. 3 | [x] verified by user (quote supplied by user) |

- **Exact pages for rows 7–13:** you gave pp. 5–8 for that passage; if you note which page each ¶ is on, I'll tighten the citations.
- **Possible error in M2 ¶ K:** "MTS’s Board of Directors approved the acquisition of 74% of Swisdorn" — every other sentence says MTS bought 74% of **Uzdunrobita**, so this is probably a typo in the order. Recorded as written; don't use it as a hop.
- **Not stated:** how much of Uzdunrobita Swisdorn kept after selling 33% (59% − 33% = 26% is arithmetic, not a source statement).
- **Supporting evidence, not a hop (¶ Y):** MTS's investigator reported that "Uzbek sources regard Takilant Ltd as being beneficially owned by the family of the Uzbek president." This is an anonymous-source report quoted inside the SEC order. Keep it as evidence, labeled as such.
- **Cross-case link:** **Takilant** also appears in P10 (VimpelCom) and P11 (Telia). If the documents for those cases tie Takilant to the same Government Official A or the same proxy, that's one shell reused across three carriers. **Hold out P10–P12 together.**
- **Nominee pattern:** rows 8, 9 and 12 are the textbook pattern the tool targets: a registered director/shareholder who is a known proxy, reused across two companies (Takilant and KolorIt). Row 9 uses the new "nominee for" link type, so the tool passes ownership through the proxy to Government Official A.
- **Data the tool needs:** none of this is in FCC data; it would come from Uzbek, Gibraltar and other foreign registries, which are out of MVP scope. Use P12 as a structural test case (hand-built graph), not an ingestion test.

### Azerfon (Azerbaijan) — already in the paper
- **All hops UNSUPPORTED from primary sources.**
- RFE/RL (https://www.rferl.org/a/azerbaijan_president_aliyev_daughters_tied_to_telecoms_firm/24248340.html, **secondary**) reports:
  - three Panama companies (Hughson, Gladwin, Grinnell Management) holding 24% each;
  - the Aliyev daughters as officers of those companies;
  - the rest held by a Nevis company and the state-owned Aztelekom.
  - RFE/RL attributes this to Azerbaijani Tax Ministry and Panama registry records, which were not obtained.
- The Helsinki Commission copy of Ismayilova's statement returned 404.
- **Data needed:** Azerbaijani tax registry and Panama Registro Público extracts. Neither is in FCC or GLEIF.
- **Recommendation:** cite it in the paper as journalist-documented. Don't use it as primary-sourced ground truth unless the registry extracts are obtained.

### Azercell (Azerbaijan) — partial case
- **Exit node:** Azercell Telekom.
- **Relays:** Azertel (Turkey) and Fintur Holdings B.V. (NL).
- **Owners:** TeliaSonera and Turkcell, plus an **unnamed 42% holder**.

| # | From | To | Equity / control | Quote | Source | Page | |
|---|---|---|---|---|---|---|---|
| 1 | Azercell | Azertel | wholly owned | "Azercell, now wholly-owned by Azertel" | [B] | p. 132 | [x] verified by user |
| 2 | Azertel | Fintur Holdings B.V. | deadlock control | "Should a deadlock regarding material decisions at the general assembly arise, the resolution supported by Fintur Holdings B.V will apply." | [B] | p. 132 | [x] verified by user |
| 3 | Azertel | unnamed largest NCI holder | 42% | "the largest holder of non-controlling interests the right to sell its 42 percent holding in Azertel to Fintur Holdings B.V.." | [B] | p. 132 | [x] verified by user |
| 4 | Fintur | TeliaSonera | 74.3% consolidated | "TeliaSonera consolidates 74.3 percent of Fintur." | [B] | p. 132 | [x] verified by user |
| 5 | 42% holder | unclear beneficial owner | — | "…unclear ownership of a minority shareholder in Azercell in Azerbaijan." | [B] | p. 72 | [x] verified by user |
| 6 | 42% holder | Aliyev family | — | **UNSUPPORTED** (OCCRP only, secondary, not opened) | — | — | n/a: gap, no primary source yet (nothing to verify) |

- **Also in [B] p. 10:** `Azercell 38.1% 69.5% Mobile` (ownership / consolidated).
- **Suitability:** partial. The primary source proves an opaque 42% node exists. The last hop is unsupported, so this is not a full held-out case.


---

## Negative controls

The evaluation answer key is `ground_truth/negative_controls.csv` (TDS excluded); edit that file, not this table, when a value changes.

**None of these were opened** except #16, because sec.gov and fcc.gov were unreachable. Each SEC URL was taken from a web-search result. Open each one to confirm the accession number and contents. Form 602 records were not reachable. Expected tool output for all of them: "no hidden owner" (the top controller is the disclosed one).

| # | Carrier (licensee) | Top parent / controller | Structure | Primary source (URL) | Opened? | Notes | |
|---|---|---|---|---|---|---|---|
| 1 | AT&T Mobility LLC, AT&T Corp., Bell cos. | AT&T Inc. (T) | public, widely held | FY2023 Ex. 21: https://www.sec.gov/Archives/edgar/data/732717/000073271724000009/ex-21ye2023.htm | No (search result) | very deep tree | [x] verified by user |
| 2 | Cellco Partnership d/b/a Verizon Wireless | Verizon Communications (VZ) | public | FY2020 Ex. 21: https://www.sec.gov/Archives/edgar/data/732712/000073271221000012/a2020q410-kxexhibit21.htm | No | partnership licensee | [x] verified by user |
| 3 | T-Mobile USA, Inc. | T-Mobile US (TMUS); Deutsche Telekom AG controls | transparent foreign control | FY2024 Ex. 21.1: https://www.sec.gov/Archives/edgar/data/1283699/000128369925000012/tmus12312024ex211.htm | No | **hard negative**; DT % only from secondary summary, so keep as range | [x] verified by user |
| 4 | Charter Communications Operating / Spectrum | Charter Communications (CHTR) | public; deep LLC chain | FY2020 Ex. 21.1: https://www.sec.gov/Archives/edgar/data/1091667/000109166721000022/chtr123120exh-211.htm | No | many-hop false-positive test | [x] verified by user |
| 5 | Comcast Cable Communications | Comcast Corp. (CMCSA) | public, dual class | FY2020 Ex. 21: https://www.sec.gov/Archives/edgar/data/1166691/000116669121000008/ex21-123120.htm | No | legit offshore subs | [x] verified by user |
| 6 | Qwest Corp., Level 3, CenturyLink ILECs | Lumen Technologies (LUMN) | public | FY2023 Ex. 21: https://www.sec.gov/Archives/edgar/data/18926/000001892624000016/lumn20231231ex21.htm | No | HK/BVI subs (legit offshore) | [x] verified by user |
| 7 | Frontier ILEC subs | Frontier Communications | public | Ex. 21 (2020): https://www.sec.gov/Archives/edgar/data/20520/000114036120007583/ex21.htm | No | check post-bankruptcy and Verizon acquisition dates | [x] verified by user |
| 8 | ~~TDS Telecom ILECs~~ **DROPPED 2026-10-25** (overlaps held-out P1/P2) | Telephone and Data Systems (TDS); TDS Voting Trust | family dual-class control | FY2019 Ex. 21: https://www.sec.gov/Archives/edgar/data/1051512/000105151220000014/tds201910-kexhibit21.htm | No | **hard negative**, but TDS/U.S. Cellular is the principal in P1/P2. Use only the ILEC side, or drop it. | [x] verified by user |
| 9 | CSC Holdings (Optimum), Cequel (Suddenlink) | Altice USA (ATUS); Patrick Drahi via Next Alt S.à r.l. | transparent individual/foreign control | FY2024 Ex. 21: https://www.sec.gov/Archives/edgar/data/1702780/000162828025005486/dec312024exhibit21.htm | No | **hard negative** | [x] verified by user |
| 10 | Cable One subs (Hargray, Fidelity) | Cable One (CABO) | public | FY2022 Ex. 21.1: https://www.sec.gov/Archives/edgar/data/1632127/000143774923004428/ex_443819.htm | No | acquired small ILECs nested | [x] verified by user |
| 11 | Shenandoah Telephone Co., Horizon | Shenandoah Telecommunications (SHEN) | public, mid-size | FY2024 Ex. 21: https://www.sec.gov/Archives/edgar/data/354963/000162828025006567/shenex2112312024.htm | No | simple tree | [x] verified by user |
| 12 | Consolidated Communications ILECs | Consolidated Communications Holdings | public then (later taken private, so check) | FY2017 Ex. 21: https://www.sec.gov/Archives/edgar/data/1304421/000155837018001412/cnsl-20171231ex216d97fba.htm | No | many state ILEC subs | [x] verified by user |
| 13 | Commnet Wireless, Alaska Communications | ATN International (ATNI) | public; majority-owned subs | FY2017 10-K: https://www.sec.gov/Archives/edgar/data/0000879585/000155837018001408/atni-20171231x10k.htm | No (Ex. 21 URL not found) | partial-ownership negative | [x] verified by user |
| 14 | Cogent Communications | Cogent Communications Holdings (CCOI) | public | FY2023 Ex. 21.1: https://www.sec.gov/Archives/edgar/data/1158324/000141057824000091/ccoi-20231231xex21d1.htm | No | many foreign subs | [x] verified by user |
| 15 | Hutchinson, Scott-Rice, Sleepy Eye telephone cos. | Nuvera Communications | small public rural ILEC holding company | Ex. 21: https://www.sec.gov/Archives/edgar/data/71557/000089710113000406/newulm125214_ex21.htm | No | small rural, two-level | [x] verified by user |
| 16 | Paul Bunyan Rural Telephone Cooperative (MN) | members | co-op, one member one vote | Bylaws: https://paulbunyan.net/?p=276 | **Yes** — Art. II §6: "Each member shall be entitled to only one vote upon each matter submitted to a vote at a meeting of the members." | simple rural; still needs ULS/Form 602 for the FRN link | [x] verified by user |
| 17 | Cricket/Denali Spectrum; Cingular/Salmon PCS (FCC-approved 85% DE investments) | Leap / Cingular (AT&T) | disclosed and approved 85% DE stakes | Referenced in J1 (D.C. Cir. 15-1330), slip op. pp. 25–26 | Yes (only the reference) | **hard negative** for P4-style structures. Underlying FCC orders not opened. | [x] verified by user |

Not used: LICT Corp. rural ILECs. The annual report URLs returned 404, and secondary sources disagree on the holder percentages.

---

## Rejected / couldn't support

- **Azerfon:** no primary document was obtained. The ownership chain (Panama companies holding 24% each, Aliyev daughters as officers) comes only from RFE/RL/OCCRP reporting of Azerbaijani Tax Ministry and Panama registry records. It is kept in the paper as journalist-documented, but **not usable as primary-sourced ground truth** until the registry extracts are obtained.
- **Dutch Takilant judgment (Rechtbank Amsterdam, 2016), Swiss and Swedish Karimova rulings:** no primary text was obtained (secondary reports only).
- **OCCRP-hosted document scans:** the host was unreachable and the document type is unknown.
- **Northstar/SNR inner hops** (Doyon ~40.1%, John Muleta/Atelum, sole-member links): FCC 15-104 was unreachable, so only secondary press supports them. These are listed as UNSUPPORTED inside P4 rather than dropped.
- **Vermont National Telephone v. Northstar (FCA):** the same DISH structure as P4, not an independent chain. Not researched.
- **Carolina PCS / Alpine PCS, NextWave, Council Tree, Pacific Light Cable Network (Team Telecom), FCC Enforcement Bureau unauthorized-transfer consent decrees:** not reached because fcc.gov and justice.gov were unreachable. These are candidates for a second pass.
- **MC/LM (P3) final outcome:** the later ALJ and Commission decisions were not opened, so the status is unknown. Kept as a case, but the control edge is "alleged."
- **Panama / Paradise / Pandora Papers telecom entities:** no primary document was found or read. Excluded per the rules.

## To-do for the user when fcc.gov / sec.gov / justice.gov are reachable

1. Open FCC 15-104 ¶¶ 14–17 to fill in the P4 inner hops.
2. Open FCC 19-38, 21-114, the CUA revocation order and 22-22 to replace the P6–P9 PSI-report citations with the FCC orders.
3. Open the official D.C. Cir. 23-7041 PDF and replace the FindLaw fragments in P1.
4. Pull the ULS ownership exhibits for Advantage Spectrum (Auction 97), King Street (ULS File No. 0003379814) and MC/LM (File No. 0002303355).
5. Confirm every Exhibit 21 URL in the negative controls.
