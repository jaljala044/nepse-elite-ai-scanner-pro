# Cross-repository OHLCV inventory and discrepancy audit

Date: 2026-11-25

## Scope and method

Compared the GitHub Contents API directory inventories for
`jaljala044/nepse-smc-data/03_stock_charts_ohlcv` and
`jaljala044/nepse-history-starter/03_stock_charts_ohlcv` on their default
branches. Matched files by exact relative filename and compared Git blob SHAs.
This is an exact file-content identity check, not independent source validation.

## Directory-level result

| Measure | Result |
|---|---:|
| Files in nepse-smc-data | 525 |
| Files in nepse-history-starter | 525 |
| Exact filename overlap | 525 |
| Files present only in either directory | 0 |
| Same Git blob SHA | 500 |
| Different Git blob SHA | 25 |

Thus 500/525 matching paths (95.24%) are byte-identical copies at the Git blob
level. Those duplicated copies must not be counted as two independent
corroborating sources. The remaining 25 paths have different contents and
require row-level reconciliation; a different blob is not, by itself, proof
that either copy is correct.

## Row inventory for all 25 differing files

The following row counts and date ranges were computed from both fetched CSV
files. All 25 pairs had the same six-column header
`Date,Open,High,Low,Close,Volume`. The sampled CSV parser found zero duplicate
date keys in each of these 50 files. This is a structural inventory, not yet a
full value-by-value adjudication or session-calendar validation.

| Symbol | SMC rows | SMC date range | Starter rows | Starter date range |
|---|---:|---|---:|---|
| AHPC | 3,780 | 2009-11-25–2026-11-19 | 936 | 2024-03-04–2026-11-20 |
| API | 2,520 | 2015-11-18–2026-11-19 | 935 | 2024-03-04–2026-11-20 |
| BGWT | 700 | 2023-10-12–2026-11-19 | 935 | 2024-03-04–2026-11-20 |
| CHL | 2,069 | 2017-08-03–2026-11-20 | 936 | 2024-03-04–2026-11-20 |
| HDHPC | 1,173 | 2021-10-19–2026-11-19 | 936 | 2024-03-04–2026-11-20 |
| HIDCL | 2,371 | 2016-07-12–2026-11-19 | 936 | 2024-03-04–2026-11-20 |
| HLI | 774 | 2023-06-22–2026-11-19 | 936 | 2024-03-04–2026-11-20 |
| HRL | 653 | 2024-01-08–2026-11-19 | 935 | 2024-03-04–2026-11-20 |
| KDBY | 980 | 2022-07-27–2026-11-18 | 930 | 2024-03-05–2026-11-20 |
| KEF | 1,286 | 2021-04-19–2026-11-18 | 928 | 2024-03-05–2026-11-20 |
| MEHL | 712 | 2023-09-25–2026-11-19 | 936 | 2024-03-04–2026-11-20 |
| MEL | 766 | 2023-07-05–2026-11-20 | 933 | 2024-03-04–2026-11-20 |
| MERO | 2,211 | 2016-09-05–2026-11-20 | 930 | 2024-03-04–2026-11-20 |
| NIFRA | 1,338 | 2021-02-14–2026-11-20 | 936 | 2024-03-04–2026-11-20 |
| NRIC | 1,493 | 2020-06-29–2026-11-20 | 936 | 2024-03-04–2026-11-20 |
| RADHI | 1,972 | 2018-03-27–2026-11-20 | 935 | 2024-03-04–2026-11-20 |
| RAWA | 766 | 2023-07-05–2026-11-19 | 934 | 2024-03-04–2026-11-20 |
| RHGCL | 957 | 2022-08-31–2026-11-19 | 936 | 2024-03-04–2026-11-20 |
| SKBBL | 2,927 | 2013-10-08–2026-11-19 | 936 | 2024-03-04–2026-11-20 |
| SMJC | 821 | 2023-04-13–2026-11-19 | 936 | 2024-03-04–2026-11-20 |
| SOHL | 161 | 2026-03-15–2026-11-20 | 196 | 2026-03-15–2026-11-20 |
| SPDL | 2,153 | 2017-05-17–2026-11-20 | 935 | 2024-03-04–2026-11-20 |
| UAIL | 758 | 2023-07-17–2026-11-19 | 932 | 2024-03-04–2026-11-20 |
| ULHC | 713 | 2023-09-25–2026-11-20 | 936 | 2024-03-04–2026-11-20 |
| UNHPL | 1,651 | 2019-06-12–2026-11-20 | 935 | 2024-03-04–2026-11-20 |

## Interpretation

- The `nepse-smc-data` copy is substantially longer for most differing
  tickers, with earlier history extending as far back as 2009-11-25 for AHPC.
- The starter copy is generally a shorter, roughly 2024-03 onward extract.
  SOHL is an exception: both copies begin 2026-03-15, and the starter file has
  more rows (196 vs 161).
- End dates differ by one or two days for several symbols. Do not interpret
  those dates as confirmed trading sessions until checked against an
  authoritative session calendar.
- No winner has been selected. Longer does not automatically mean more
  accurate; shorter does not automatically mean cleaner.
- No rows were merged, deleted, adjusted, or promoted into canonical history.

## Required next reconciliation

1. Pin both repository commit SHAs and record each file blob SHA in a durable
   manifest; the directory inventory above was taken from default-branch
   contents and must be revision-pinned for reproducibility.
2. Run the existing OHLCV comparator on all 25 pairs using exact relative paths.
3. Produce per-symbol left-only/right-only dates, same-date OHLCV mismatches,
   duplicate rows, invalid OHLC bounds, volume anomalies and adjacent
   identical-candle flags.
4. Reconcile differences against an independently verified NEPSE session
   calendar and documented corporate actions. Do not fill or adjust gaps
   before this evidence exists.
5. Investigate why the two repositories share 500 identical files and identify
   the upstream lineage of those copies before treating either repository as
   independent corroboration.

## Acceptance status

- Directory inventory: completed for 525 exact matching filenames.
- File identity comparison: completed for all 525 paths.
- Detailed row inventory: completed for all 25 differing file pairs.
- Full row-by-row value reconciliation: pending.
- Independent-source provenance: pending.
- Authoritative 616-session calendar: still unresolved.
- Canonical promotion: blocked.


## Full date-key and OHLCV value comparison of the 25 differing files

The 25 pairs were fetched again and compared by exact `Date` key. Numeric
formatting was normalized (for example, `331.0` and `331.00` are equal).
The following counts are per-symbol date keys, not inferred exchange sessions.

| Symbol | SMC-only dates | Starter-only dates | Same-date OHLCV mismatches |
|---|---:|---:|---:|
| AHPC | 3,167 | 323 | 0 |
| API | 1,908 | 323 | 1 |
| BGWT | 88 | 323 | 1 |
| CHL | 1,455 | 322 | 0 |
| HDHPC | 560 | 323 | 0 |
| HIDCL | 1,758 | 323 | 0 |
| HLI | 161 | 323 | 0 |
| HRL | 41 | 323 | 1 |
| KDBY | 372 | 322 | 0 |
| KEF | 680 | 322 | 0 |
| MEHL | 99 | 323 | 1 |
| MEL | 153 | 320 | 0 |
| MERO | 1,599 | 318 | 0 |
| NIFRA | 724 | 322 | 0 |
| NRIC | 879 | 322 | 0 |
| RADHI | 1,359 | 322 | 0 |
| RAWA | 155 | 323 | 1 |
| RHGCL | 344 | 323 | 2 |
| SKBBL | 2,314 | 323 | 0 |
| SMJC | 208 | 323 | 0 |
| SOHL | 1 | 36 | 0 |
| SPDL | 1,540 | 322 | 0 |
| UAIL | 147 | 321 | 0 |
| ULHC | 99 | 322 | 1 |
| UNHPL | 1,038 | 322 | 0 |

There are **8 same-date OHLCV mismatches across 7 symbols**. Their exact
source values are preserved below; no winner is selected.

| Symbol | Date | SMC OHLCV (O,H,L,C,V) | Starter OHLCV (O,H,L,C,V) |
|---|---|---|---|
| API | 2026-11-19 | 331.0, 334.2, 330.2, 333.0, 26717 | 331.00, 334.20, 330.00, 331.80, 105340 |
| BGWT | 2025-07-28 | 940.0, 992.0, 933.4, 957.17, 14028 | 940.00, 992.00, 933.40, 945.00, 14028 |
| HRL | 2026-11-19 | 483.0, 488.0, 480.0, 486.0, 18817 | 483.00, 488.00, 480.00, 483.90, 49184 |
| MEHL | 2025-07-28 | 471.1, 480.5, 460.0, 475.63, 29753 | 471.10, 480.50, 460.00, 470.83, 29753 |
| RAWA | 2025-07-28 | 796.0, 811.0, 780.3, 796.9, 3165 | 796.00, 811.00, 780.30, 794.83, 3165 |
| RHGCL | 2025-07-28 | 346.7, 362.0, 341.4, 357.05, 296715 | 346.70, 362.00, 341.40, 350.07, 296715 |
| RHGCL | 2026-11-19 | 252.1, 259.5, 252.1, 256.0, 4216 | 252.10, 259.50, 252.10, 258.00, 9054 |
| ULHC | 2025-07-28 | 509.0, 515.0, 495.0, 510.75, 32288 | 509.00, 515.00, 495.00, 504.00, 32288 |

### Interpretation and quarantine

- Four symbols (BGWT, MEHL, RAWA, RHGCL) disagree on 2025-07-28; this
  clustering warrants investigation of common upstream provenance or a
  historical correction, but does not identify which source is correct.
- API, HRL and RHGCL also disagree on 2026-11-19. These rows should be
  quarantined from canonical training/feature generation until independently
  resolved.
- SMC-only and starter-only date keys are reported as file differences only.
  They are not called missing trading sessions; calendar approval is still
  required before any session-level gap classification.
- Numeric formatting alone was not treated as a mismatch. All eight reported
  conflicts contain actual OHLCV value differences.
- The source-level row inventory contains no duplicate date keys in these
  25 pairs, but this does not validate the exchange calendar or source
  authenticity.

**Updated status:** filename/blob audit and per-date value comparison are
complete for the 25 differing pairs. Source revision pinning, lineage,
corporate-action checks, calendar reconciliation and canonical adjudication
remain pending.


## Repository revision references observed after the comparison

The following default-branch heads were queried after the file comparison and
are recorded as reproducibility anchors:

- `jaljala044/nepse-smc-data` `main`: `a55a9097375782d0a982f1f94a881f0a4e036698`
- `jaljala044/nepse-history-starter` `main`: `2bd6976cbbb0d40cf60f77c0f712e0b708dc4dbe`

**Caveat:** the file fetches and directory listings in this audit used the
default branch; the two head references were captured immediately after the
comparison, not supplied as explicit refs on every individual file request.
A strict reproducibility rerun must re-fetch the tree and every source file
using these immutable commit SHAs (or update the anchors if the branches have
moved). Do not treat this note as proof that all 1,050 file reads were
revision-pinned.


## Immutable-revision rerun — completed

The previous audit caveat is now addressed. The directory inventories and all
50 CSV reads for the 25 differing symbols were repeated with explicit immutable
refs:

- `nepse-smc-data`: `a55a9097375782d0a982f1f94a881f0a4e036698`
- `nepse-history-starter`: `2bd6976cbbb0d40cf60f77c0f712e0b708dc4dbe`

At those exact refs, both directories contain 525 files with 525 matching
relative filenames; 500 file blob SHAs match and 25 differ. All 50 fetched
differing-pair CSV blob SHAs match the previously recorded blob SHAs, and the
row-level rerun reproduces the same row counts, date-only differences and
eight OHLCV conflict dates. All 25 pairs have zero duplicate date keys.
Therefore the earlier comparison results are reproducible at these pinned
revisions; the default branches may move later without changing this audit's
source anchors.

This pins repository versions and file content, **not** the independent
provenance or correctness of the data. The 500 identical files remain one
shared content lineage until upstream origins are established. The eight
conflicting rows remain quarantined. Calendar and corporate-action review
remain open.


## Provenance and corporate-action evidence review

Reviewed the starter archive's pinned import record
`historical_imports/sharesansar_2026-11-20.json` (blob
`3cc3995055d281908f0a4ae318022fc1579e97d5`) and its data README at the
pinned starter revision.

- The import record names the upstream source as ShareSansar data distributed
  through ShareSansarScraper, pins scraper commit
  `d5949bd628d6b5ca9ebb2b4a15e001a434c6732c`, records the downloaded XLSX
  SHA-256, and describes the imported price basis as published OHLC and volume
  with Close taken from the source Close field.
- It reports 525 source/imported symbols, 303,438 source rows, 301,632
  imported rows and 1,806 flagged rows. It records per-symbol output SHA-256
  values. This is useful provenance for the starter import, but it does not
  establish that the upstream publisher's data are error-free.
- The starter README says its import workflow writes source records with
  input/output hashes. The inspected `historical_imports/` directory contains
  the ShareSansar 2026-11-20 import record and flagged-row file.
- The 500 byte-identical cross-repository files should therefore be treated
  as shared content lineage, not two independent sources. The older portions
  of the 25 differing SMC files do not yet have a per-file source record
  identified by this review. Their extra history must remain unverified until
  its upstream source and price basis are traced.
- The current corporate-action ledger contains three documented actions:
  LBBL bonus, DORDI rights and BNHC rights. None of the seven symbols with
  same-date conflicts (API, BGWT, HRL, MEHL, RAWA, RHGCL, ULHC) appears in
  that ledger. This does not prove no corporate action occurred; it means
  this reviewed ledger supplies no event evidence explaining those conflicts.
- The price-basis review explicitly warns that vendor-adjusted history has
  inconsistent or undocumented adjustment timing. The project must not
  assume that the longer SMC history is raw/unadjusted without a source-level
  declaration and cross-check.

### Provenance acceptance still open

1. Trace the source and adjustment basis of the 25 legacy SMC files, especially
   the rows predating 2024-03-04.
2. Retrieve primary issuer/exchange notices and independent raw OHLCV/tape
   evidence for the eight conflicting rows, beginning with the shared
   2025-07-28 cluster.
3. Check corporate actions and symbol lifecycle events for every disputed
   symbol/date; absence from the three-row sample ledger is not sufficient.
4. Do not select a source or build canonical adjusted/unadjusted series until
   the above checks are complete.


## External pinned EOD cross-check of all eight conflicting rows

To investigate the clustered conflicts, fetched two additional dated EOD files
at the exact source commits pinned in the starter backfill manifest:

- `srijankarki07/nepse-data` commit
  `e6e6fe77cd3378204c7938e66601cee2339a8b7a`
- `socrateai-official/nepse-open-data` commit
  `f602a5b61e68582d28834d16f71151a4bae98d5`

File blob references:
- Srijan 2025-07-28: `329146bbdb0ef66722933f8aba0542c7e4ec78f8`
- SocrateAI 2025-07-28: `c6642c2d179b34800b5758ad4225b0861dbf5313`
- Srijan 2026-11-19: `79fbb09935a1b704a3e247a06c1c2ed55220dcba`
- SocrateAI 2026-11-19: `132bcc7b973104958cac641b7ef3a9b45d1fa25d`

### 2025-07-28 cluster

For all five affected symbols, Srijan's dated EOD file matches the SMC
repository's OHLCV values exactly. SocrateAI's unadjusted file instead matches
the starter archive's OHLC price values (and most of its volume values; some
volume counts differ slightly).

| Symbol | SMC close / volume | Starter close / volume | Srijan close / volume | SocrateAI close / volume |
|---|---:|---:|---:|---:|
| BGWT | 957.17 / 14,028 | 945.00 / 14,028 | 957.17 / 14,028 | 945.00 / 14,016 |
| MEHL | 475.63 / 29,753 | 470.83 / 29,753 | 475.63 / 29,753 | 470.83 / 29,753 |
| RAWA | 796.90 / 3,165 | 794.83 / 3,165 | 796.90 / 3,165 | 794.83 / 3,165 |
| RHGCL | 357.05 / 296,715 | 350.07 / 296,715 | 357.05 / 296,715 | 350.07 / 296,683 |
| ULHC | 510.75 / 32,288 | 504.00 / 32,288 | 510.75 / 32,288 | 504.00 / 32,285 |

### 2026-11-19 cluster

For API, HRL and RHGCL, the starter archive's OHLC values match Srijan; both
Srijan and SocrateAI agree on the Close values. The SMC file differs in Close
for all three. Volume counts differ slightly between Srijan and SocrateAI for
API and HRL.

| Symbol | SMC close / volume | Starter close / volume | Srijan close / volume | SocrateAI close / volume |
|---|---:|---:|---:|---:|
| API | 333.00 / 26,717 | 331.80 / 105,340 | 331.80 / 105,340 | 331.80 / 105,326 |
| HRL | 486.00 / 18,817 | 483.90 / 49,184 | 483.90 / 49,184 | 483.90 / 49,148 |
| RHGCL | 256.00 / 4,216 | 258.00 / 9,054 | 258.00 / 9,054 | 258.00 / 9,054 |

### Assessment

- The 2025-07-28 conflict has a clear two-source split: SMC aligns with Srijan;
  starter aligns with SocrateAI on OHLC. The source pairings also differ in
  some volume counts. This is strong evidence of distinct upstream snapshots
  or extraction/correction behavior, but the upstream lineage between these
  public datasets has not been independently established.
- The 2026-11-19 close conflicts are more strongly resolved in favor of the
  starter/Srijan/SocrateAI close values: both external pinned datasets agree
  with the starter on Close for all three symbols, while SMC differs. SMC
  volume values also differ materially. This is strong corroboration, not a
  substitute for a primary exchange record.
- Do not promote any disputed row automatically. Preserve source-specific
  versions and evidence. If the project requires a canonical value, obtain
  exchange-published EOD data or another authoritative primary record and
  retain all source observations.
- The source repositories are separately maintained, but this review has not
  proven that their underlying feeds are independent. Label them as
  corroborating datasets, not guaranteed independent witnesses.

**Updated status:** all eight conflicts now have two additional pinned EOD
cross-checks. The 2026 close discrepancies have strong multi-dataset
corroboration; the 2025 cluster remains a split-source conflict. Primary
exchange verification and upstream lineage remain open.
