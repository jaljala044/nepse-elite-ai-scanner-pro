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


## Chart-based OHLC discrepancy verification protocol (added 2026-11-24)

A numeric OHLC validation failure or a conflict between feeds must trigger a chart-level check before the row is classified as a bad raw-market candle:

1. Open the same symbol and exact date in Chukul's chart.
2. Record **adjusted** and **unadjusted** OHLC separately; never mix the two series.
3. Capture the chart/source URL, retrieval timestamp, selected adjustment mode, symbol, date, and displayed OHLC. Save a screenshot or other reproducible evidence when permitted.
4. If Chukul is unavailable or the discrepancy remains unresolved, inspect the same date on NEPSE Alpha and record its adjustment basis separately.
5. Compare chart observations with each CSV/API source. Do not silently replace source values. Keep raw source rows immutable and preserve each feed's adjustment basis.
6. If adjusted and unadjusted values differ, determine which series the archive is intended to represent before validating or promoting it. Corporate actions and adjustment methodology must be accounted for.
7. If the chart itself displays an arithmetically inconsistent candle, keep it quarantined and seek another independent source; a chart display is evidence, not automatic authority to repair.

### User-reported examples — pending independent evidence capture

- **BGWT, 2026-04-29:** user reports Chukul adjusted chart O/H/L/C = 740/731/718/730 and unadjusted chart = 720/731/718/730. The adjusted values violate high >= open; the unadjusted values pass the OHLC range rule. This suggests an adjustment-basis mismatch may explain the CSV anomaly. Do not call the unadjusted values canonical until chart evidence, archive adjustment basis, and corporate-action context are recorded.
- **API, 2026-04-27:** reported O/H/L/C = 339.9/345/340/341 remains inconsistent because open < low. The user reports the same values on adjusted and unadjusted charts; this requires a further chart/source check and remains unresolved.

These are user-provided chart observations, not yet independently captured by this audit. The two rows remain excluded from canonical promotion until this protocol is completed. Preserve original source rows unchanged.



## Same-pass source verification results — API and BGWT (2026-11-24)

### API — 2026-04-27

Independent daily OHLC pages from Sun Securities and Financial Notices both report:
- Open 339.9
- High 345
- Low 340
- Close 341
- Volume 206,969

References:
- https://sunsecurities.com/company/API/price-history
- https://www.financialnotices.com/stock-nepse.php?symbol=API

The archived floorsheet mirror at https://github.com/Shubhamnpk/yonepse/blob/main/data/floor_sheet/daily/2026-04-27.json was also filtered using its security master (API security ID 697). It contains 543 API-tagged contracts and total quantity 206,969, matching the daily OHLC page's volume. However, the transaction prices span **331.8 to 345**, not 340 to 345. Two contracts (quantities 6 and 2) are priced at 331.8. The lowest contract-number transaction is 345 and the highest contract-number transaction is 341; the file has no execution-time values in these rows, so contract-number order alone is not accepted as definitive open/close proof.

Therefore:
- High 345 and close 341 are consistent with the daily OHLC references and the observed floor data's max/last-contract price.
- The floorsheet mirror introduces an unresolved low-price conflict at 331.8. It does **not** independently confirm low=340.
- The daily OHLC record 339.9/345/340/341 is corroborated by two independent published daily-price pages, with matching total volume, but remains quarantined from canonical promotion until the two 331.8 floor records are reconciled against an exchange-origin floorsheet or another reliable contract-level source.
- Do not silently delete or alter the two floor contracts. Preserve them and flag the source mirror for investigation.

### BGWT — 2026-04-29

Two independent daily-price sources report the unadjusted candle:
- Open 720
- High 731
- Low 718
- Close 730
- Volume 1,573

References:
- https://sunsecurities.com/company/BGWT/price-history
- https://arthakendra.com/stock-market/company/BGWT/price-history

These agree with the user's Chukul unadjusted-chart observation and resolve the apparent OHLC violation as an adjustment-basis mismatch: the archive's 740 open is not the unadjusted traded open for this date. Retain the original adjusted/source record as received, but do not use it as a raw unadjusted OHLC candle. The unadjusted reference candle is 720/731/718/730. Preserve adjustment-basis metadata and corporate-action context when importing it.

### Evidence standard

These checks used public daily-price pages and a public floorsheet mirror, not direct logged-in Chukul chart captures or an exchange-signed floorsheet export. Record source identity and limitations. For future anomalies, check Chukul adjusted and unadjusted immediately, then cross-check at least one independent price-history source; use contract-level floorsheet evidence when available and reconcile any trade-price exceptions before release.


## Immediate external verification — API and BGWT (2026-11-24)

### API — 2026-04-27
- SMC source row: O/H/L/C/V = 339.9/345.0/340.0/341.0/206,969.
- Independent Financial Notices API history table reports the same O/H/L/C and volume for 2026-04-27.
- This reproduces the source values but does **not** resolve the arithmetic inconsistency (open 339.9 < low 340.0).
- The accessible project floorsheet archive currently contains only daily files for 2026-11-19, 2026-11-20, 2026-11-23 and 2026-11-24; it does not contain 2026-04-27. A separate public floorsheet dataset advertises daily files from 2024 onward, but its web viewer is failing schema conversion and the exact 2026-04-27 API contracts have not yet been retrieved. Therefore transaction-level open/close/high/low reconstruction is **pending**, not verified.
- Evidence URLs: https://www.financialnotices.com/stock-nepse.php?symbol=API ; https://huggingface.co/datasets/urekmazino69/Nepse-floorsheet-and-indices

### BGWT — 2026-04-29
- User-reported Chukul adjusted chart: O/H/L/C = 740/731/718/730; unadjusted chart: 720/731/718/730.
- Independent daily-history tables at Sun Securities and ArthaKendra both report 720/731/718/730, volume 1,573. Financial Notices reports the same values.
- This independently supports the **unadjusted** candle and indicates the earlier 740 open is an adjusted-series/chart value that must not be mixed with raw OHLC. Do not use the adjusted 740 open in the raw-market candle.
- Evidence URLs: https://sunsecurities.com/company/BGWT/price-history ; https://www.arthakendra.com/stock-market/company/BGWT/price-history ; https://www.financialnotices.com/stock-nepse.php?symbol=BGWT

The external daily-history tables are secondary sources, not the NEPSE transaction ledger. Raw archive values remain immutable; canonical selection must retain source and adjustment-basis provenance. The API record remains quarantined until the dated floorsheet is acquired and its transaction rates are fully reconciled.


## User-directed API open-value decision — 2026-11-24

For API on 2026-04-27, the user explicitly directed that the **working open value be marked as 340.0**. Record the resulting working OHLC as **340.0 / 345.0 / 340.0 / 341.0** (O/H/L/C) for downstream review. This makes the candle satisfy the basic OHLC range inequalities, but it is a **user-directed working correction**, not an independently verified exchange correction. Preserve the original SMC raw row unchanged as **339.9 / 345.0 / 340.0 / 341.0** with its source provenance and hash. Keep both values in the audit trail; do not overwrite raw source data. The contract-level floor-sheet mirror previously examined contains two API trades at 331.8, so the day's low and the open still require authoritative transaction-level reconciliation. Until that conflict is resolved, tag the working 340.0 open as provisional and exclude the row from strict verified-canonical OHLCV promotion.

## Partial all-symbol audit progress — batch 3 (files 33–40 of 525)

Eight additional files after BJHL in repository tree order were fetched and scanned for calendar dates 2025-11-24 through 2026-11-23. This remains a calendar-window scan, not verified-session completeness. See the batch table below; sparse instruments and any anomalies require lifecycle/source review. Cumulative progress: 40/525 files (7.6%).

| Symbol file | Total rows | Rows in candidate interval | Invalid OHLC | Latest date |
|---|---:|---:|---:|---|
| BNHC_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| BNL_OHLCV.csv | 605 | 173 | 0 | 2026-11-19 |
| BNT_OHLCV.csv | 909 | 279 | 0 | 2026-11-20 |
| BOKD86KA_OHLCV.csv | 103 | 23 | 0 | 2026-10-15 |
| BOKD86_OHLCV.csv | 411 | 82 | 0 | 2026-11-17 |
| BPCL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| BPW_OHLCV.csv | 3 | 0 | 0 | 2024-03-06 |
| BUNGAL_OHLCV.csv | 319 | 305 | 0 | 2026-11-20 |




## Partial all-symbol audit progress — batch 4 (files 41–48 of 525)

Eight additional files after BUNGAL in repository tree order were fetched and scanned for calendar dates 2025-11-24 through 2026-11-23. This is still a calendar-window scan, not verified-session completeness.

| Symbol file | Total rows | Rows in candidate interval | Invalid OHLC | Latest date |
|---|---:|---:|---:|---|
| C30MF_OHLCV.csv | 887 | 285 | 0 | 2026-11-20 |
| CBBLPO_OHLCV.csv | 9 | 5 | 0 | 2026-09-03 |
| CBBL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| CBLD88_OHLCV.csv | 555 | 139 | 0 | 2026-11-20 |
| CCBD88_OHLCV.csv | 484 | 121 | 0 | 2026-11-19 |
| CFCL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| CGH_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| CHCL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |



Cumulative partial scan: 48/525 files (9.1%). This is not a full-universe quality pass; security lifecycle and verified session-calendar checks remain outstanding.


## Session-calendar evidence update — 2026-11-24

A further contemporaneous report from ShareSansar (2026-04-08) explicitly states that NEPSE issued a public notice and that its Board decision of 22 Chaitra 2082 moved regular securities trading to Monday–Friday, including Friday, with Saturday and Sunday closed. This independently corroborates the schedule-regime change already identified. The report does not expose the underlying NEPSE notice PDF/image or its notice identifier in the inspected page, so the primary exchange artifact is still not captured. Do not mark individual dates as verified trading sessions from weekday rules alone; public holidays, special closures, and special sessions still require date-specific evidence.

Evidence: https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08

Calendar work therefore advances from “schedule regime unknown” to “weekday regime independently corroborated; primary notice and date-level holiday/session register still pending.”


## Partial all-symbol audit — batch 5 (files 49–56 of 525)

- CHDC_OHLCV.csv: 936 total rows; 306 rows in candidate calendar interval; 0 OHLC range violations; latest 2026-11-20.
- CHL_OHLCV.csv: 2069 total rows; 227 rows in candidate calendar interval; 0 OHLC range violations; latest 2026-11-20.
- CITY_OHLCV.csv: 935 total rows; 305 rows in candidate calendar interval; 0 OHLC range violations; latest 2026-11-20.
- CIT_OHLCV.csv: 936 total rows; 306 rows in candidate calendar interval; 0 OHLC range violations; latest 2026-11-20.
- CIZBD86_OHLCV.csv: 147 total rows; 51 rows in candidate calendar interval; 0 OHLC range violations; latest 2026-10-26.
- CIZBD90_OHLCV.csv: 394 total rows; 118 rows in candidate calendar interval; 0 OHLC range violations; latest 2026-11-20.
- CKHL_OHLCV.csv: 936 total rows; 306 rows in candidate calendar interval; 0 OHLC range violations; latest 2026-11-20.
- CLI_OHLCV.csv: 932 total rows; 306 rows in candidate calendar interval; 0 OHLC range violations; latest 2026-11-20.

Cumulative: 56/525 files (10.7%). Scan interval 2025-11-24 through 2026-11-23 is calendar-date scoped, not yet validated against the official session calendar. 


## Partial all-symbol audit — batch 6 (files 57–64 of 525)

- CMF1_OHLCV.csv: 357 total; 0 interval; 0 invalid; latest 2025-03-01
- CMF2_OHLCV.csv: 800 total; 193 interval; 0 invalid; latest 2026-07-02
- CORBLP_OHLCV.csv: 2 total; 2 interval; 0 invalid; latest 2026-08-12
- CORBL_OHLCV.csv: 936 total; 306 interval; 0 invalid; latest 2026-11-20
- CREST_OHLCV.csv: 534 total; 306 interval; 0 invalid; latest 2026-11-20
- CSY_OHLCV.csv: 220 total; 220 interval; 0 invalid; latest 2026-11-20
- CYCLP_OHLCV.csv: 15 total; 12 interval; 0 invalid; latest 2026-04-09
- CYCL_OHLCV.csv: 935 total; 305 interval; 0 invalid; latest 2026-11-20

Cumulative progress: 64/525 files (12.2%). Candidate date window 2025-11-24 through 2026-11-23 remains calendar-based pending verified session calendar. No new OHLC range violations in this batch.


## External chart and data-provider access check — 2026-11-24

Opened and inspected the public Chukul Technical Desk page, ShareHub Nepal home, ShareHub Price History and Floorsheet pages, and NEPSE Alpha chart page.

- Chukul Technical Desk page describes stock coverage using adjusted prices and says sign-in is required for access. The public page fetch returned no readable chart rows; no authenticated chart session was available in this audit. Therefore this is a provider capability/access check, not a captured API or BGWT chart observation. Source: https://chukul.com/technical-desk/details
- ShareHub public Price History page exposes symbol/date/high/low/open/close/volume/transactions columns, but the public extraction returned a blank dynamic table. ShareHub's documented data API includes per-symbol daily OHLCV price-history endpoints and floor-sheet services, but requires a provider-issued Bearer token, an allow-listed server IP and an enabled licence. No token or licence was supplied, so no private API call was attempted. Sources: https://sharehubnepal.com/nepse/stock-price-history ; https://sharehubnepal.com/data/nepse-data-documentation/
- ShareHub public Floorsheet page exposes date, symbol, buyer/seller broker, quantity, price, amount, trade time and contract ID filters, but the public page extraction returned no transaction rows. Source: https://sharehubnepal.com/nepse/floorsheet
- NEPSE Alpha chart page is reachable and exposes daily/hourly/weekly/monthly chart modes and indicator/scanner controls. Public extraction did not expose a selected-symbol OHLC candle or historical date query, so no specific chart candle has been verified. Source: https://nepsealpha.com/trading/chart

Conclusion: provider pages are now located and reachable, but a reproducible same-symbol/same-date adjusted/unadjusted candle capture is still unavailable from these public page extractions. Do not claim the API 2026-04-27 or BGWT 2026-04-29 chart discrepancy has been independently checked by these providers. For ShareHub API access, obtain an appropriately licensed account/token and server IP allow-list from the provider; do not place credentials in repository files or chat.


## Partial all-symbol audit — batch 7 (files 65–72 of 525)

| File | Total rows | Candidate-window rows | OHLC violations | Latest date |
|---|---:|---:|---:|---|
| CZBILP_OHLCV.csv | 36 | 13 | 0 | 2026-08-25 |
| CZBIL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| DDBL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| DHEL_OHLCV.csv | 324 | 306 | 0 | 2026-11-20 |
| DHPL_OHLCV.csv | 933 | 303 | 0 | 2026-11-20 |
| DLBS_OHLCV.csv | 929 | 302 | 0 | 2026-11-20 |
| DOLTI_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| DORDI_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |

Cumulative progress: 72/525 files (13.7%). No new OHLC range violations in this batch. Candidate window 2025-11-24 through 2026-11-23 is still calendar-based; official session completeness and listing lifecycle are separate checks.
