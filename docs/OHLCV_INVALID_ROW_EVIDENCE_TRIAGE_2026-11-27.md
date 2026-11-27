# OHLCV invalid-row evidence triage — 2026-11-27

## Scope and source

This is a triage of the 1,331 invalid OHLC rows in the validated ledger artifact from workflow run `45933953438` (artifact `15169872483`). It uses the row-level SocrateAI unadjusted-EOD cross-check attached to the same artifact. SocrateAI is a secondary corroboration source, not NEPSE/CDSC exchange-origin evidence.

The exact pinned source audit scanned 525 files in each repository: 314,712 SMC rows and 301,632 History Starter rows. All 1,331 invalid rows originate in `jaljala044/nepse-smc-data`, across 15 symbols, from 2009-11-25 through 2026-04-29.

## Rule breakdown

| OHLC rule violation | Rows |
|---|---:|
| High below open, low or close | 796 |
| Low above open, high or close | 535 |
| **Total** | **1,331** |

The invalid rows are concentrated in AHPC (588), SKBBL (379), API (122), MERO (102), SPDL (53), CHL (45), and HIDCL (30); the remaining eight symbols account for 12 rows.

## Secondary-source triage

| Cross-check result | Rows | Interpretation |
|---|---:|---|
| External row present and OHLC geometry valid | 1,319 | Candidate for further source review only; not an accepted correction |
| External row present but OHLC geometry also invalid | 8 | Secondary source repeats or contains an invalid OHLC shape |
| No external row / file not published / symbol absent | 4 | Requires another source or remains unresolved |
| **Total** | **1,331** | |

Among the 1,327 rows with a matched external symbol, source-comparison classifications were 1,320 partial/conflicting, five full matches, and two where no source matched the external row. The five full matches are particularly important: external agreement does not make an invalid OHLC row valid. The external row itself is geometrically invalid for those cases.

Field differences overlap across rows: Open differs in 1,298 comparisons, Low in 25, High in 24, Volume in 16, and Close in nine. There are 1,282 rows with exactly one differing field, 35 with two, two with three, one with four, and two with five; nine comparisons show no field difference. The dominant Open differences are a useful review-priority signal, not proof of which value is correct.

## Highest-priority exceptions

### External row is also OHLC-invalid (8)

| Symbol | Date | SMC source CSV line | External classification |
|---|---|---:|---|
| AHPC | 2016-11-13 | 1491 | all sources match external |
| AHPC | 2018-11-06 | 1954 | partial/conflicting |
| API | 2016-09-12 | 197 | all sources match external |
| API | 2018-11-06 | 693 | partial/conflicting |
| HIDCL | 2016-07-21 | 9 | all sources match external |
| HIDCL | 2016-11-13 | 75 | all sources match external |
| HIDCL | 2018-11-06 | 540 | partial/conflicting |
| SPDL | 2017-06-18 | 22 | all sources match external |

### No external row available (4)

| Symbol | Date | SMC source CSV line | Reason |
|---|---|---:|---|
| API | 2016-09-03 | 190 | External daily file not published |
| MERO | 2017-03-20 | 21 | Symbol absent from external file |
| MERO | 2017-04-09 | 26 | Symbol absent from external file |
| UNHPL | 2020-06-29 | 165 | Symbol absent from external file |

### External row differs from both pinned sources (2)

| Symbol | Date | SMC source CSV line |
|---|---|---:|
| AHPC | 2010-02-10 | 42 |
| AHPC | 2011-06-20 | 304 |

These are candidates for independent primary-source retrieval, not resolved records.

## Recommended review order

1. Obtain NEPSE/CDSC-origin evidence for the 14 priority rows above (eight external-invalid, four external-missing, two external-no-match).
2. For the remaining 1,317 rows with a geometrically valid external row, batch-review the dominant Open-only differences, starting with AHPC and SKBBL; retain each original source row, external row, source line and hashes.
3. Resolve only where an authoritative source and date-specific identity are independently verified. Otherwise retain quarantine.

## Safety and disposition

No invalid row is resolved by this triage. All 1,331 remain `quarantined_unresolved`; all remain excluded from canonical ingestion and model training. SocrateAI agreement, including full matches, is not sufficient to repair or promote a row. No raw CSV has been modified.
