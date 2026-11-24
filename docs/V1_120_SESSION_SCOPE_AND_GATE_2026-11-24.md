# V1 historical-data scope and acceptance gate — 2026-11-24

## Release decision

App V1 targets **one year of reliable NEPSE historical data first**. If the full one-year window cannot pass the data-quality and provenance gates, evaluate **six months** as the fallback. The 2–3-year expansion is deferred to a later app version.

The window is an elapsed calendar period ending at the latest fully closed and published session, with eligible dates determined by an evidence-backed NEPSE session calendar. It is not a fixed number of calendar rows or an assumed session count.

The same target applies to market-wide indices, sector indices, and individual-stock OHLCV where available. Broker/floorsheet coverage is a separate data-family gate; it must not be implied by price coverage or fabricated.

## Trading calendar

NEPSE's weekly schedule changed in April 2026: reports state that the regular week moved from Sunday–Thursday to Monday–Friday effective 6 April 2026. This is secondary evidence pending capture of the primary NEPSE notice. Exceptional closures and special sessions must be evidenced individually; weekday rules are only a cross-check.

References:
- https://english.ratopati.com/story/57946/stock-market-now-trades-from-monday-to-friday
- https://english.ratopati.com/story/57517/stock-trading-closed-on-saturday-and-sunday-open-on-friday
- https://thehimalayantimes.com/business/nepse-shifts-to-mondayfriday-trading-week

## Cutoff and snapshot handling

The 24 November intraday snapshot is not an EOD bar. The official page was observed showing market summary through 23 November, but inspected stock-history samples did not have matching latest dates. Do not set the canonical cutoff until the latest completed EOD date is verified consistently for each required data family.

Official page: https://nepalstock.com.np/

## Repository inventory and sample evidence

A recursive Git tree of `jaljala044/nepse-smc-data` default branch was inspected. It contains **525 CSV files** under `03_stock_charts_ohlcv/`. This is an inventory count, not proof that all 525 securities have usable data in the candidate window. A full all-symbol, row-level one-year audit has not yet been completed.

Sample files previously inspected:
- SMC `API_OHLCV.csv`: 2,520 dated rows, latest 2026-11-19.
- SMC `AHPC_OHLCV.csv`: 3,780 dated rows, latest 2026-11-19.
- History Starter `API_OHLCV.csv`: 935 dated rows, latest 2026-11-20; repeated weekend/carry-forward dates are present.

A one-year sample-window check reported 229 rows/dates for each SMC sample, with one OHLC violation in API and zero in AHPC. The flagged SMC API record is:
`2026-04-27,339.9,345.0,340.0,341.0,206969.0`
It violates `low <= open`. History Starter API had no row for that date, so there is no independent corroboration or correction. Quarantine this row; do not guess a replacement.

The History Starter API sample had 64 Saturday/Sunday dates in the candidate interval. These cannot be counted as NEPSE sessions merely because they appear in a ticker file.

The scanner repository's `data/reference/nepse_session_calendar.csv` contains only its header:
`date,status,source_id,evidence_uri,verified_at_utc,notes`
Therefore it currently contains zero verified session rows.

## Historical anomalies and scope discipline

The earlier all-history audit found 1,331 invalid OHLC rows across the full SMC archive and eight source conflicts across the full archive. Those are **all-history counts**, not one-year or six-month findings. Recompute the counts within the final candidate window after calendar verification. Do not spend V1 effort on 2009 data.

Prior audit:
https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/HISTORICAL_OHLCV_AUDIT_2026-11-24.md

## Acceptance gates

1. Freeze the latest fully closed EOD cutoff; exclude intraday data.
2. Build an evidence-backed session calendar for the rolling one-year period, retaining primary notice/evidence links and verification timestamps.
3. Audit all 525 stock CSVs, the complete active/current security universe, listing lifecycle, missing dates, non-traded days, and suspended/delisted securities separately.
4. Validate OHLCV numeric parsing, positive/zero-volume policy, `low <= open/close <= high`, `low <= high`, duplicates, ordering, and plausible volume/turnover.
5. Reconcile source conflicts against authorized exchange-origin/licensed data where available; preserve source-specific records and quarantine unresolved conflicts.
6. Classify carry-forward rows only against the verified session calendar and security trading status.
7. Audit market and sector index data for date coverage, OHLC relationships, breadth/turnover integrity, and same-window completeness.
8. Audit broker/floorsheet coverage separately: session coverage, page/contract counts, pagination completeness, provenance, and limitations. Broker codes are identifiers, not proof of beneficial ownership or intent.
9. Preserve point-in-time provenance: source, source hash, observation/session date, retrieval and ingestion timestamps, publication/availability timestamp when known, and adjustment basis.
10. If one year fails, document exact failure reasons and independently evaluate six months. If six months also fails, do not label the dataset verified or promote it as canonical.
11. Keep quarantined rows out of canonical V1 analytics; never overwrite or silently correct raw records.

## Current status

- [x] V1 scope set to one year first, six months fallback.
- [x] 2–3-year expansion deferred.
- [x] April 2026 weekday-regime change identified; date-aware calendar required.
- [x] SMC repository tree inventory confirms 525 stock CSV files.
- [x] Sample check identifies one invalid SMC API OHLC row (2026-04-27), quarantined.
- [x] Scanner session calendar confirmed empty apart from header.
- [ ] Capture primary NEPSE notice for schedule change.
- [ ] Populate and verify the one-year session calendar.
- [ ] Complete all-symbol one-year audit across all 525 files.
- [ ] Reconcile the recent 20–23 November cutoff/coverage gap.
- [ ] Audit market/sector history and broker/floorsheet coverage.
- [ ] If required, independently assess six-month fallback.
- [ ] Build immutable canonical tables, manifest, quarantine register, and independent QA.

**Release status: BLOCKED.** This is a scope and evidence document, not a completed dataset or full-universe audit.



## Partial all-symbol audit progress (not a completion claim)

On 2026-11-24, the first 24 of the 525 SMC stock CSV files in tree order were fetched and parsed for the candidate calendar interval 2025-11-24 through 2026-11-23. This is a **calendar-window file-row scan**, not a verified-session completeness audit, because the exchange session register is still empty.

- 24/525 files inspected (4.6%); no fetch failures in this batch.
- One OHLC range violation was observed: API on 2026-04-27 (open 339.9 below low 340.0). No other OHLC range violation was observed in this first batch.
- Several files are clearly sparse or lifecycle-sensitive: examples include ADBLB86 (3 rows in the entire file), ADBLB87 (3), ADBLB (1), ACLBSLP (3), ALBSLP (12 total but no row in the candidate interval), and BENH (17 candidate-window rows). These must not be labelled data loss without checking listing/security lifecycle and whether the instrument is active.
- More established files in this batch commonly contain 305–306 candidate-window rows, but that row count is not a session count and does not establish full-session coverage.
- Latest dates in the inspected files range from 2026-09-28/2026-10-06/2026-10-15/2026-11-04 to 2026-11-20; the API and AHPC files end 2026-11-19. This supports a coverage-variance investigation, not a single global cutoff yet.

The audit must continue through all remaining 501 files, then reconcile the dates against the verified session calendar and security master. No canonical promotion is authorized from this partial batch.


## Partial all-symbol audit progress — batch 2 (files 25–32 of 525)

The next eight stock CSVs in repository tree order were fetched and scanned for calendar dates 2025-11-24 through 2026-11-23. All eight fetches succeeded. This remains a calendar-window scan, not a verified-session completeness audit.

| Symbol file | Total rows | Rows in candidate interval | Invalid OHLC | Latest date |
|---|---:|---:|---:|---|
| BFCPO | 19 | 1 | 0 | 2026-05-19 |
| BFC | 936 | 306 | 0 | 2026-11-20 |
| BGWT | 700 | 226 | 1 | 2026-11-19 |
| BHCL | 402 | 306 | 0 | 2026-11-20 |
| BHDC | 935 | 305 | 0 | 2026-11-20 |
| BHL | 936 | 306 | 0 | 2026-11-20 |
| BHPL | 936 | 306 | 0 | 2026-11-20 |
| BJHL | 189 | 189 | 0 | 2026-11-20 |

New quarantine candidate: BGWT on 2026-04-29 has open=740, high=731, low=718, close=730, violating high >= open. Preserve raw record; no automatic correction. BFCPO is sparse (only one candidate-window row), requiring lifecycle/status review before classifying as missing coverage.

Cumulative partial scan: 32/525 files (6.1%). Two invalid OHLC rows have been observed so far: API 2026-04-27 and BGWT 2026-04-29. This is a partial-sample count only, not a one-year archive-wide anomaly count. Continue remaining 493 files; do not promote canonical data.
