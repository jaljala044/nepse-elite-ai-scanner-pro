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
