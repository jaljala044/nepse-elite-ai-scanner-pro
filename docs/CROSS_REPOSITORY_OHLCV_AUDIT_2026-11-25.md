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
