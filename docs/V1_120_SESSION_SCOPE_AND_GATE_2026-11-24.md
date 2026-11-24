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


## Partial all-symbol audit — batches 8–17 (files 73–152 of 525)

Candidate window for all counts below: 2025-11-24 through 2026-11-23 (calendar dates, not verified exchange sessions). “Invalid” means the strict OHLC range relation failed; it does not by itself prove which source field is wrong.

| File | Total rows | Candidate-window rows | OHLC violations | Latest date |
|---|---:|---:|---:|---|
| EBLD85_OHLCV.csv | 558 | 175 | 0 | 2026-11-18 |
| EBLD86_OHLCV.csv | 566 | 144 | 0 | 2026-11-17 |
| EBLD91_OHLCV.csv | 422 | 259 | 0 | 2026-11-20 |
| EBLEB89_OHLCV.csv | 206 | 93 | 0 | 2026-11-03 |
| EBL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| ECL_OHLCV.csv | 76 | 76 | 0 | 2026-11-20 |
| EDBLPO_OHLCV.csv | 2 | 1 | 0 | 2026-08-06 |
| EDBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| EHPL_OHLCV.csv | 933 | 306 | 0 | 2026-11-20 |
| ENL_OHLCV.csv | 932 | 305 | 0 | 2026-11-20 |
| FMDBLP_OHLCV.csv | 6 | 1 | 0 | 2026-10-12 |
| FMDBL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| FOWADP_OHLCV.csv | 10 | 5 | 0 | 2026-07-17 |
| FOWAD_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GBBD85_OHLCV.csv | 751 | 236 | 0 | 2026-11-19 |
| GBBLPO_OHLCV.csv | 60 | 13 | 0 | 2026-09-29 |
| GBBL_OHLCV.csv | 931 | 301 | 0 | 2026-11-20 |
| GBD80~2F81_OHLCV.csv | 13 | 0 | 0 | outside candidate window |
| GBILD84~2F85_OHLCV.csv | 418 | 149 | 0 | 2026-11-18 |
| GBILD86~2F87_OHLCV.csv | 431 | 101 | 0 | 2026-11-19 |
| GBIMEP_OHLCV.csv | 119 | 40 | 0 | 2026-09-18 |
| GBIMESY2_OHLCV.csv | 388 | 303 | 0 | 2026-11-20 |
| GBIME_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GBLBS_OHLCV.csv | 871 | 277 | 0 | 2026-11-20 |
| GCIL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GFCL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| GHL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GIBF1_OHLCV.csv | 931 | 302 | 0 | 2026-11-20 |
| GILBPO_OHLCV.csv | 3 | 0 | 0 | outside candidate window |
| GILB_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GLBSL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GLH_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GMFBS_OHLCV.csv | 932 | 304 | 0 | 2026-11-20 |
| GMFILP_OHLCV.csv | 1 | 0 | 0 | outside candidate window |
| GMFIL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GMLI_OHLCV.csv | 589 | 304 | 0 | 2026-11-20 |
| GRDBLP_OHLCV.csv | 2 | 1 | 0 | 2026-07-25 |
| GRDBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GSY_OHLCV.csv | 581 | 304 | 0 | 2026-11-20 |
| GUFLPO_OHLCV.csv | 12 | 3 | 0 | 2026-08-26 |
| GUFL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GVL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| GWFD83_OHLCV.csv | 344 | 70 | 0 | 2026-11-19 |
| H8020_OHLCV.csv | 930 | 305 | 0 | 2026-11-20 |
| HATHY_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| HBLD83_OHLCV.csv | 157 | 40 | 0 | 2026-08-04 |
| HBLD86_OHLCV.csv | 284 | 92 | 0 | 2026-11-19 |
| HBLPO_OHLCV.csv | 41 | 13 | 0 | 2026-09-01 |
| HBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| HDHPC_OHLCV.csv | 1173 | 226 | 0 | 2026-11-19 |
| HDL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| HEIP_OHLCV.csv | 875 | 272 | 0 | 2026-11-20 |
| HEI_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| HFIN_OHLCV.csv | 199 | 199 | 0 | 2026-11-20 |
| HHL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| HIDCLP_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| HIDCL_OHLCV.csv | 2371 | 226 | 0 | 2026-11-19 |
| HIMSTAR_OHLCV.csv | 390 | 306 | 0 | 2026-11-20 |
| HLBSL_OHLCV.csv | 932 | 302 | 0 | 2026-11-20 |
| HLICF_OHLCV.csv | 323 | 304 | 0 | 2026-11-20 |
| HLIPO_OHLCV.csv | 17 | 0 | 0 | outside candidate window |
| HLI_OHLCV.csv | 774 | 226 | 0 | 2026-11-19 |
| HPPL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| HRL_OHLCV.csv | 653 | 226 | 1 | 2026-11-19 |
| HURJA_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| ICFCD83_OHLCV.csv | 343 | 66 | 0 | 2026-11-18 |
| ICFCD88_OHLCV.csv | 463 | 235 | 0 | 2026-11-20 |
| ICFCD89_OHLCV.csv | 154 | 154 | 0 | 2026-11-20 |
| ICFCPO_OHLCV.csv | 4 | 0 | 0 | outside candidate window |
| ICFC_OHLCV.csv | 933 | 303 | 0 | 2026-11-20 |
| IGIPO_OHLCV.csv | 7 | 1 | 0 | 2026-09-18 |
| IGI_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| IHL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| ILBSP_OHLCV.csv | 49 | 16 | 0 | 2026-11-20 |
| ILBS_OHLCV.csv | 933 | 306 | 0 | 2026-11-20 |
| ILI_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| JALPA_OHLCV.csv | 129 | 0 | 0 | outside candidate window |
| JBBD87_OHLCV.csv | 405 | 86 | 0 | 2026-11-04 |
| JBBLPO_OHLCV.csv | 43 | 14 | 0 | 2026-10-01 |
| JBBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |

Cumulative progress: 152/525 files (29.0%). One new candidate OHLC violation was detected in HRL on 2026-04-29, in addition to previously recorded API and BGWT cases. No raw file was changed.

### HRL 2026-04-29 discrepancy — external corroboration

The archive row is O/H/L/C = 685.5/685.0/676.1/679.2, which violates high >= open. Sun Securities' independently published HRL daily history reports 679.2/685.0/676.1/679.2 with volume 74,867 for 2026-04-29, which is internally valid and differs only in open. This is an externally corroborated candidate value, not an authorized rewrite of the archive. Preserve raw 685.5 and quarantine the source row pending primary NEPSE/floorsheet confirmation. Source: https://sunsecurities.com/company/HRL/price-history

Chart-provider check was attempted again for this discrepancy: Chukul Technical Desk URL is reachable but exposes no readable public chart data; NEPSE Alpha's chart route currently exposes a login/register form, not a candle. Therefore neither provider yielded a directly observed HRL 2026-04-29 chart candle in this run. Do not label the discrepancy as Chukul/NEPSE Alpha chart-verified. Public secondary OHLC confirmation is Sun Securities only at this stage.


## Partial all-symbol audit — batches 18–29 (files 153–240 of 525)

Candidate window: 2025-11-24 through 2026-11-23 (calendar dates, not verified exchange sessions). Counts are CSV rows, not exchange-session counts.

| File | Total | Window | OHLC violations | Latest |
|---|---:|---:|---:|---|
| JBLBP_OHLCV.csv | 45 | 20 | 0 | 2026-05-26 |
| JBLB_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| JFLPO_OHLCV.csv | 10 | 0 | 0 | outside window |
| JFL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| JHAPA_OHLCV.csv | 313 | 305 | 0 | 2026-11-20 |
| JOSHI_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| JSLBBP_OHLCV.csv | 5 | 0 | 0 | outside window |
| JSLBB_OHLCV.csv | 929 | 299 | 0 | 2026-11-20 |
| KAHL_OHLCV.csv | 87 | 87 | 0 | 2026-11-20 |
| KBLD86_OHLCV.csv | 211 | 40 | 0 | 2026-11-05 |
| KBLD89_OHLCV.csv | 283 | 82 | 0 | 2026-10-27 |
| KBLD90_OHLCV.csv | 153 | 40 | 0 | 2026-09-29 |
| KBLPO_OHLCV.csv | 97 | 25 | 0 | 2026-10-02 |
| KBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| KBSH_OHLCV.csv | 934 | 304 | 0 | 2026-11-20 |
| KDBY_OHLCV.csv | 980 | 224 | 1 | 2026-11-18 |
| KDL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| KEF_OHLCV.csv | 1286 | 223 | 1 | 2026-11-18 |
| KHPL_OHLCV.csv | 124 | 124 | 0 | 2026-11-20 |
| KKHC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| KLBSLP_OHLCV.csv | 5 | 0 | 0 | outside window |
| KLBSL_OHLCV.csv | 128 | 0 | 0 | outside window |
| KMCDBP_OHLCV.csv | 10 | 7 | 0 | 2026-06-09 |
| KMCDB_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| KPCL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| KRBL_OHLCV.csv | 296 | 0 | 0 | outside window |
| KSBBLD87_OHLCV.csv | 407 | 70 | 0 | 2026-10-29 |
| KSBBLP_OHLCV.csv | 28 | 4 | 0 | 2026-10-07 |
| KSBBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| KSY_OHLCV.csv | 850 | 294 | 0 | 2026-11-20 |
| LBBLD89_OHLCV.csv | 347 | 87 | 0 | 2026-11-18 |
| LBBLPO_OHLCV.csv | 6 | 2 | 0 | 2026-11-17 |
| LBBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| LBLD86_OHLCV.csv | 99 | 23 | 0 | 2026-11-04 |
| LBLD88_OHLCV.csv | 197 | 52 | 0 | 2026-09-30 |
| LEC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| LEMF_OHLCV.csv | 90 | 0 | 0 | outside window |
| LICN_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| LLBS_OHLCV.csv | 931 | 302 | 0 | 2026-11-20 |
| LSD92_OHLCV.csv | 29 | 29 | 0 | 2026-11-20 |
| LSH12_OHLCV.csv | 62 | 62 | 0 | 2026-11-20 |
| LSLPO_OHLCV.csv | 57 | 2 | 0 | 2026-10-29 |
| LSL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| LUK_OHLCV.csv | 910 | 292 | 0 | 2026-11-20 |
| LVF2_OHLCV.csv | 919 | 295 | 0 | 2026-11-20 |
| MABEL_OHLCV.csv | 326 | 306 | 0 | 2026-11-20 |
| MAKAR_OHLCV.csv | 934 | 304 | 0 | 2026-11-20 |
| MANDU_OHLCV.csv | 933 | 303 | 0 | 2026-11-20 |
| MATRIP_OHLCV.csv | 34 | 20 | 0 | 2026-11-20 |
| MATRI_OHLCV.csv | 773 | 305 | 0 | 2026-11-20 |
| MBJC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| MBLD2085_OHLCV.csv | 122 | 67 | 0 | 2026-08-06 |
| MBLD87_OHLCV.csv | 308 | 67 | 0 | 2026-11-04 |
| MBLEF_OHLCV.csv | 487 | 301 | 0 | 2026-11-20 |
| MBLPO_OHLCV.csv | 20 | 1 | 0 | 2026-07-02 |
| MBL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| MCHL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| MDBPO_OHLCV.csv | 11 | 3 | 0 | 2026-11-20 |
| MDB_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| MEHL_OHLCV.csv | 712 | 226 | 0 | 2026-11-19 |
| MEL_OHLCV.csv | 766 | 227 | 0 | 2026-11-20 |
| MEN_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| MEPDL_OHLCV.csv | 58 | 58 | 0 | 2026-11-20 |
| MERO_OHLCV.csv | 2211 | 227 | 1 | 2026-11-20 |
| MFILPO_OHLCV.csv | 6 | 3 | 0 | 2026-10-05 |
| MFIL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| MFLD85_OHLCV.csv | 350 | 88 | 0 | 2026-11-03 |
| MHCL_OHLCV.csv | 933 | 306 | 0 | 2026-11-20 |
| MHL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| MHNL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| MKCL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| MKHC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| MKHL_OHLCV.csv | 933 | 306 | 0 | 2026-11-20 |
| MKJC_OHLCV.csv | 928 | 303 | 0 | 2026-11-20 |
| MKLB_OHLCV.csv | 126 | 0 | 0 | outside window |
| MLBBLP_OHLCV.csv | 1 | 0 | 0 | outside window |
| MLBBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| MLBLD89_OHLCV.csv | 224 | 67 | 0 | 2026-11-20 |
| MLBLPO_OHLCV.csv | 28 | 16 | 0 | 2026-09-28 |
| MLBL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| MLBSLP_OHLCV.csv | 2 | 1 | 0 | 2026-01-20 |
| MLBSL_OHLCV.csv | 932 | 306 | 0 | 2026-11-20 |
| MLBSP_OHLCV.csv | 1 | 1 | 0 | 2026-05-18 |
| MLBS_OHLCV.csv | 931 | 301 | 0 | 2026-11-20 |
| MMF1_OHLCV.csv | 934 | 305 | 0 | 2026-11-20 |
| MMFDBP_OHLCV.csv | 1 | 0 | 0 | outside window |
| MMFDB_OHLCV.csv | 9 | 0 | 0 | outside window |
| MMKJL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |

Cumulative progress: 240/525 files (45.7%). Newly detected OHLC range violations in this segment: KDBY (2026-04-29), KEF (2026-04-28), MERO (2026-04-24). No source rows were changed.

### Additional anomaly investigation — secondary price-history sources

- KDBY 2026-04-29 archive O/H/L/C = 11.54/11.50/11.25/11.38, volume 23,420. ArthaKendra's page explicitly labels its columns Open/High/Low/Close and reports 11.25/11.50/11.25/11.38, same volume. This corroborates a candidate open of 11.25 from a secondary source, but raw archive remains unchanged and the row remains quarantined pending primary NEPSE/floorsheet evidence. Source: https://www.arthakendra.com/stock-market/company/KDBY/price-history
- KEF 2026-04-28 archive O/H/L/C = 10.89/10.80/10.70/10.79, volume 5,400. ArthaKendra reports the same values and volume, including the same invalid high-below-open relation. This is not independent validation of the candle; it may be a shared-source error. Keep unresolved and quarantined. Source: https://www.arthakendra.com/stock-market/company/KEF/price-history
- MERO 2026-04-24 archive O/H/L/C = 731.1/730/720/726, volume 1,671. Sun Securities reports the same O/H/L/C and volume for that date, so the secondary source corroborates the published values but not arithmetic validity. Keep raw row unchanged and quarantined; investigate the original NEPSE/floorsheet record. Source: https://sunsecurities.com/company/MERO/price-history

These secondary sources are not Chukul or NEPSE Alpha chart captures. The Chukul/NEPSE Alpha access limitation recorded above still applies; no claim of direct chart verification is made.


## Partial all-symbol audit — batches 30–39 (files 241–320 of 525)

Candidate window: 2025-11-24 through 2026-11-23 (calendar dates, not verified exchange sessions).

| File | Total | Window | OHLC violations | Latest |
|---|---:|---:|---:|---|
| MNBBLP_OHLCV.csv | 44 | 14 | 0 | 2026-10-27 |
| MNBBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| MND84~2F85_OHLCV.csv | 283 | 55 | 0 | 2026-10-14 |
| MNMF1_OHLCV.csv | 617 | 305 | 0 | 2026-11-20 |
| MNMF2_OHLCV.csv | 1 | 1 | 0 | 2026-11-20 |
| MPFLPO_OHLCV.csv | 4 | 0 | 0 | outside window |
| MPFL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| MSHL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| MSLBP_OHLCV.csv | 30 | 10 | 0 | 2026-07-23 |
| MSLB_OHLCV.csv | 935 | 306 | 0 | 2026-11-20 |
| NABBCP_OHLCV.csv | 13 | 0 | 0 | outside window |
| NABBC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NABILD2089_OHLCV.csv | 203 | 195 | 0 | 2026-11-20 |
| NABILD87_OHLCV.csv | 318 | 73 | 0 | 2026-11-20 |
| NABILP_OHLCV.csv | 3 | 2 | 0 | 2026-09-24 |
| NABIL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NADEP_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NBBD2085_OHLCV.csv | 165 | 63 | 0 | 2026-11-18 |
| NBF2_OHLCV.csv | 921 | 295 | 0 | 2026-11-20 |
| NBF3_OHLCV.csv | 931 | 305 | 0 | 2026-11-20 |
| NBLD82_OHLCV.csv | 227 | 58 | 0 | 2026-10-27 |
| NBLD85_OHLCV.csv | 475 | 83 | 0 | 2026-11-20 |
| NBLD87_OHLCV.csv | 559 | 141 | 0 | 2026-11-20 |
| NBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NCCD86_OHLCV.csv | 324 | 83 | 0 | 2026-11-04 |
| NESDO_OHLCV.csv | 934 | 304 | 0 | 2026-11-20 |
| NFSPO_OHLCV.csv | 2 | 0 | 0 | outside window |
| NFS_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| NGPL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NHDL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NHPC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NIBD2082_OHLCV.csv | 246 | 53 | 0 | 2026-06-16 |
| NIBD84_OHLCV.csv | 461 | 111 | 0 | 2026-11-04 |
| NIBLGF_OHLCV.csv | 916 | 299 | 0 | 2026-11-20 |
| NIBLSTF_OHLCV.csv | 840 | 304 | 0 | 2026-11-20 |
| NIBSF2_OHLCV.csv | 928 | 301 | 0 | 2026-11-20 |
| NICAD2091_OHLCV.csv | 264 | 217 | 0 | 2026-11-19 |
| NICAD8182_OHLCV.csv | 83 | 0 | 0 | outside window |
| NICAD8283_OHLCV.csv | 343 | 0 | 0 | outside window |
| NICAD85~2F86_OHLCV.csv | 312 | 83 | 0 | 2026-10-15 |
| NICAD~2085~2F86_OHLCV.csv | 2 | 0 | 0 | outside window |
| NICAP_OHLCV.csv | 8 | 4 | 0 | 2026-09-30 |
| NICA_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NICBF_OHLCV.csv | 832 | 253 | 0 | 2026-11-20 |
| NICD83~2F84_OHLCV.csv | 155 | 30 | 0 | 2026-08-24 |
| NICD88_OHLCV.csv | 354 | 82 | 0 | 2026-11-05 |
| NICFC_OHLCV.csv | 920 | 303 | 0 | 2026-11-20 |
| NICGF2_OHLCV.csv | 926 | 301 | 0 | 2026-11-20 |
| NICGF_OHLCV.csv | 351 | 0 | 0 | outside window |
| NICLBSL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NICLPO_OHLCV.csv | 1 | 0 | 0 | outside window |
| NICL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| NICSF_OHLCV.csv | 930 | 304 | 0 | 2026-11-20 |
| NIFRAGED_OHLCV.csv | 303 | 185 | 0 | 2026-11-20 |
| NIFRAP_OHLCV.csv | 8 | 0 | 0 | outside window |
| NIFRAUR85~2F86_OHLCV.csv | 232 | 45 | 0 | 2026-11-18 |
| NIFRA_OHLCV.csv | 1338 | 227 | 0 | 2026-11-20 |
| NILPO_OHLCV.csv | 2 | 0 | 0 | outside window |
| NIL_OHLCV.csv | 935 | 306 | 0 | 2026-11-20 |
| NIMBD90_OHLCV.csv | 420 | 110 | 0 | 2026-11-20 |
| NIMBPO_OHLCV.csv | 898 | 290 | 0 | 2026-11-20 |
| NIMB_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NLBBL_OHLCV.csv | 9 | 0 | 0 | outside window |
| NLG_OHLCV.csv | 933 | 303 | 0 | 2026-11-20 |
| NLICLP_OHLCV.csv | 9 | 3 | 0 | 2026-02-16 |
| NLICL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| NLICP_OHLCV.csv | 12 | 1 | 0 | 2026-02-11 |
| NLIC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NLO_OHLCV.csv | 43 | 10 | 0 | 2026-09-30 |
| NMB50_OHLCV.csv | 829 | 224 | 0 | 2026-08-26 |
| NMBD2085_OHLCV.csv | 119 | 36 | 0 | 2026-11-04 |
| NMBD87~2F88_OHLCV.csv | 338 | 66 | 0 | 2026-11-20 |
| NMBD89~2F90_OHLCV.csv | 167 | 54 | 0 | 2026-10-12 |
| NMBHF2_OHLCV.csv | 518 | 304 | 0 | 2026-11-20 |
| NMBMF_OHLCV.csv | 933 | 304 | 0 | 2026-11-20 |
| NMBPO_OHLCV.csv | 39 | 1 | 0 | 2026-08-26 |
| NMBUR93~2F94_OHLCV.csv | 33 | 33 | 0 | 2026-11-17 |
| NMB_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NMFBSP_OHLCV.csv | 45 | 14 | 0 | 2026-10-09 |
| NMFBS_OHLCV.csv | 935 | 306 | 0 | 2026-11-20 |

Cumulative progress: 320/525 files (61.0%). No new OHLC range violations were detected in files 241–320. The already recorded KDBY, KEF and MERO anomalies remain in the quarantine/investigation list; raw rows remain unchanged.


## Partial all-symbol audit — batches 40–66 (files 321–525 of 525)

Candidate window: 2025-11-24 through 2026-11-23 (calendar dates, not verified exchange sessions). Every one of the 525 stock CSV files in the repository's `03_stock_charts_ohlcv/` directory has now been fetched and checked for strict OHLC range relations within that window.

| File | Total | Window | OHLC violations | Latest |
|---|---:|---:|---:|---|
| NMIC_OHLCV.csv | 535 | 305 | 0 | 2026-11-20 |
| NMLBBLP_OHLCV.csv | 11 | 4 | 0 | 2026-11-18 |
| NMLBBL_OHLCV.csv | 860 | 306 | 0 | 2026-11-20 |
| NRICP_OHLCV.csv | 7 | 0 | 0 | outside window |
| NRIC_OHLCV.csv | 1493 | 227 | 0 | 2026-11-20 |
| NRM_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NRN_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| NSIF2_OHLCV.csv | 930 | 303 | 0 | 2026-11-20 |
| NSY_OHLCV.csv | 192 | 192 | 0 | 2026-11-20 |
| NTC_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| NUBL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| NWCL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| NYADI_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| OHL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| OMPL_OHLCV.csv | 509 | 305 | 0 | 2026-11-20 |
| PBD84_OHLCV.csv | 298 | 72 | 0 | 2026-11-06 |
| PBD85_OHLCV.csv | 381 | 64 | 0 | 2026-11-17 |
| PBD88_OHLCV.csv | 736 | 227 | 0 | 2026-11-05 |
| PBD93_OHLCV.csv | 40 | 40 | 0 | 2026-11-20 |
| PBLD84_OHLCV.csv | 379 | 82 | 0 | 2026-11-06 |
| PBLD86_OHLCV.csv | 129 | 19 | 0 | 2026-10-08 |
| PBLD87_OHLCV.csv | 316 | 88 | 0 | 2026-11-19 |
| PCBLP_OHLCV.csv | 113 | 26 | 0 | 2026-11-17 |
| PCBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| PCIL_OHLCV.csv | 170 | 170 | 0 | 2026-11-20 |
| PFLPO_OHLCV.csv | 1 | 0 | 0 | outside window |
| PFL_OHLCV.csv | 889 | 259 | 0 | 2026-11-20 |
| PHCL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| PMHPL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| PMLIP_OHLCV.csv | 80 | 17 | 0 | 2026-11-05 |
| PMLI_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| PPCL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| PPL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| PRIN_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| PROFLP_OHLCV.csv | 45 | 5 | 0 | 2026-10-15 |
| PROFL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| PRSF_OHLCV.csv | 928 | 305 | 0 | 2026-11-20 |
| PRVUPO_OHLCV.csv | 98 | 17 | 0 | 2026-10-09 |
| PRVU_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| PSF_OHLCV.csv | 931 | 305 | 0 | 2026-11-20 |
| PURE_OHLCV.csv | 485 | 304 | 0 | 2026-11-20 |
| RADHI_OHLCV.csv | 1972 | 227 | 1 | 2026-11-20 |
| RAWA_OHLCV.csv | 766 | 226 | 2 | 2026-11-19 |
| RBBD2088_OHLCV.csv | 300 | 203 | 0 | 2026-11-20 |
| RBBD83_OHLCV.csv | 292 | 78 | 0 | 2026-11-18 |
| RBBF40_OHLCV.csv | 249 | 249 | 0 | 2026-11-20 |
| RBCLPO_OHLCV.csv | 837 | 227 | 0 | 2026-11-18 |
| RBCL_OHLCV.csv | 931 | 304 | 0 | 2026-11-20 |
| RFPL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| RHGCL_OHLCV.csv | 957 | 226 | 0 | 2026-11-19 |
| RHPL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| RIDI_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| RLEL_OHLCV.csv | 182 | 182 | 0 | 2026-11-20 |
| RLFLPO_OHLCV.csv | 8 | 3 | 0 | 2026-04-08 |
| RLFL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| RMF1_OHLCV.csv | 932 | 306 | 0 | 2026-11-20 |
| RMF2_OHLCV.csv | 855 | 273 | 0 | 2026-11-19 |
| RNLI_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| RSDCP_OHLCV.csv | 1 | 1 | 0 | 2026-06-02 |
| RSDC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| RSML_OHLCV.csv | 222 | 222 | 0 | 2026-11-20 |
| RSY2_OHLCV.csv | 60 | 60 | 0 | 2026-11-20 |
| RSY_OHLCV.csv | 453 | 305 | 0 | 2026-11-20 |
| RURU_OHLCV.csv | 932 | 302 | 0 | 2026-11-20 |
| SABBL_OHLCV.csv | 221 | 221 | 0 | 2026-11-20 |
| SABSL_OHLCV.csv | 131 | 0 | 0 | outside window |
| SADBLP_OHLCV.csv | 41 | 4 | 0 | 2026-07-31 |
| SADBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SAEF2_OHLCV.csv | 62 | 62 | 0 | 2026-11-20 |
| SAEF_OHLCV.csv | 293 | 0 | 0 | outside window |
| SAGAR_OHLCV.csv | 320 | 305 | 0 | 2026-11-20 |
| SAGF_OHLCV.csv | 912 | 294 | 0 | 2026-11-20 |
| SAHAS_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SAIL_OHLCV.csv | 306 | 306 | 0 | 2026-11-20 |
| SALICOPO_OHLCV.csv | 8 | 1 | 0 | 2026-08-27 |
| SALICO_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SAMAJ_OHLCV.csv | 591 | 0 | 0 | outside window |
| SAND2085_OHLCV.csv | 249 | 73 | 0 | 2026-10-27 |
| SANIMA_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SANVI_OHLCV.csv | 432 | 305 | 0 | 2026-11-20 |
| SAPDBLP_OHLCV.csv | 5 | 0 | 0 | outside window |
| SAPDBL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SAPIL_OHLCV.csv | 57 | 57 | 0 | 2026-11-20 |
| SARBTM_OHLCV.csv | 920 | 305 | 0 | 2026-11-20 |
| SBCF_OHLCV.csv | 930 | 301 | 0 | 2026-11-20 |
| SBD87_OHLCV.csv | 408 | 93 | 0 | 2026-11-20 |
| SBD89_OHLCV.csv | 127 | 45 | 0 | 2026-10-15 |
| SBIBD86_OHLCV.csv | 204 | 42 | 0 | 2026-10-08 |
| SBID2090_OHLCV.csv | 153 | 140 | 0 | 2026-11-19 |
| SBID83_OHLCV.csv | 531 | 143 | 0 | 2026-11-19 |
| SBID89_OHLCV.csv | 483 | 118 | 0 | 2026-11-17 |
| SBI_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SBLD2082_OHLCV.csv | 191 | 3 | 0 | 2026-01-06 |
| SBLD2091_OHLCV.csv | 248 | 192 | 0 | 2026-11-17 |
| SBLD83_OHLCV.csv | 116 | 18 | 0 | 2026-09-01 |
| SBLD84_OHLCV.csv | 233 | 54 | 0 | 2026-11-03 |
| SBLD89_OHLCV.csv | 278 | 81 | 0 | 2026-11-19 |
| SBLPO_OHLCV.csv | 21 | 5 | 0 | 2026-09-30 |
| SBL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SCBD_OHLCV.csv | 288 | 73 | 0 | 2026-11-19 |
| SCB_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SDBD87_OHLCV.csv | 436 | 96 | 0 | 2026-11-17 |
| SDLBSL_OHLCV.csv | 131 | 0 | 0 | outside window |
| SEF2_OHLCV.csv | 63 | 63 | 0 | 2026-11-20 |
| SEF_OHLCV.csv | 916 | 300 | 0 | 2026-11-20 |
| SFCLP_OHLCV.csv | 2 | 2 | 0 | 2026-01-19 |
| SFCL_OHLCV.csv | 852 | 225 | 0 | 2026-07-09 |
| SFEF_OHLCV.csv | 917 | 295 | 0 | 2026-11-20 |
| SFMF_OHLCV.csv | 817 | 238 | 0 | 2026-11-20 |
| SGHC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SGHL_OHLCV.csv | 87 | 87 | 0 | 2026-11-20 |
| SGICP_OHLCV.csv | 26 | 2 | 0 | 2026-05-19 |
| SGIC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SHEL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SHINED_OHLCV.csv | 205 | 192 | 0 | 2026-11-20 |
| SHINEP_OHLCV.csv | 20 | 6 | 0 | 2026-06-28 |
| SHINE_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SHIVM_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SHLB_OHLCV.csv | 934 | 304 | 0 | 2026-11-20 |
| SHL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SHPC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SICLPO_OHLCV.csv | 5 | 0 | 0 | outside window |
| SICL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SIFCPO_OHLCV.csv | 8 | 1 | 0 | 2026-01-05 |
| SIFC_OHLCV.csv | 932 | 305 | 0 | 2026-11-20 |
| SIGS2_OHLCV.csv | 837 | 271 | 0 | 2026-11-20 |
| SIGS3_OHLCV.csv | 913 | 304 | 0 | 2026-11-20 |
| SIKLES_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SINDUP_OHLCV.csv | 2 | 1 | 0 | 2026-04-05 |
| SINDU_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SIPD_OHLCV.csv | 170 | 170 | 0 | 2026-11-20 |
| SJCL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SJLICP_OHLCV.csv | 4 | 1 | 0 | 2026-06-30 |
| SJLIC_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SKBBLP_OHLCV.csv | 10 | 0 | 0 | outside window |
| SKBBL_OHLCV.csv | 2927 | 226 | 0 | 2026-11-19 |
| SKHEL_OHLCV.csv | 181 | 181 | 0 | 2026-11-20 |
| SKHL_OHLCV.csv | 186 | 186 | 0 | 2026-11-20 |
| SLBBLP_OHLCV.csv | 16 | 14 | 0 | 2026-08-27 |
| SLBBL_OHLCV.csv | 935 | 306 | 0 | 2026-11-20 |
| SLBSL_OHLCV.csv | 860 | 304 | 0 | 2026-11-20 |
| SLCF_OHLCV.csv | 928 | 304 | 0 | 2026-11-20 |
| SMATAP_OHLCV.csv | 10 | 1 | 0 | 2026-04-29 |
| SMATA_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SMBPO_OHLCV.csv | 4 | 1 | 0 | 2026-07-16 |
| SMB_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SMFBS_OHLCV.csv | 931 | 302 | 0 | 2026-11-20 |
| SMHL_OHLCV.csv | 933 | 306 | 0 | 2026-11-20 |
| SMH_OHLCV.csv | 932 | 306 | 0 | 2026-11-20 |
| SMJC_OHLCV.csv | 821 | 226 | 0 | 2026-11-19 |
| SMPDAP_OHLCV.csv | 6 | 1 | 0 | 2026-09-17 |
| SMPDA_OHLCV.csv | 769 | 306 | 0 | 2026-11-20 |
| SNLI_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SNMAPO_OHLCV.csv | 13 | 5 | 0 | 2026-04-09 |
| SNORL_OHLCV.csv | 93 | 93 | 0 | 2026-11-20 |
| SOHL_OHLCV.csv | 161 | 161 | 0 | 2026-11-20 |
| SONA_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SOPL_OHLCV.csv | 111 | 111 | 0 | 2026-11-20 |
| SPC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SPDL_OHLCV.csv | 2153 | 227 | 1 | 2026-11-20 |
| SPHL_OHLCV.csv | 933 | 303 | 0 | 2026-11-20 |
| SPILPO_OHLCV.csv | 4 | 0 | 0 | outside window |
| SPIL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SPL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SRBLD83_OHLCV.csv | 250 | 65 | 0 | 2026-11-05 |
| SRD80_OHLCV.csv | 12 | 0 | 0 | outside window |
| SRLIP_OHLCV.csv | 34 | 12 | 0 | 2026-10-29 |
| SRLI_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SSHL_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| STC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| SWASTIK_OHLCV.csv | 314 | 305 | 0 | 2026-11-20 |
| SWBBLP_OHLCV.csv | 1 | 0 | 0 | outside window |
| SWBBL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| SWMFPO_OHLCV.csv | 50 | 14 | 0 | 2026-10-14 |
| SWMF_OHLCV.csv | 930 | 303 | 0 | 2026-11-20 |
| SYPNL_OHLCV.csv | 290 | 290 | 0 | 2026-11-20 |
| TAMOR_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| TPC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| TPKHL_OHLCV.csv | 97 | 97 | 0 | 2026-11-20 |
| TRH_OHLCV.csv | 934 | 304 | 0 | 2026-11-20 |
| TSHL_OHLCV.csv | 933 | 306 | 0 | 2026-11-20 |
| TTL_OHLCV.csv | 436 | 306 | 0 | 2026-11-20 |
| TVCL_OHLCV.csv | 931 | 304 | 0 | 2026-11-20 |
| UAILPO_OHLCV.csv | 7 | 1 | 0 | 2026-08-06 |
| UAIL_OHLCV.csv | 758 | 226 | 2 | 2026-11-19 |
| UHEWA_OHLCV.csv | 933 | 306 | 0 | 2026-11-20 |
| ULBSL_OHLCV.csv | 932 | 305 | 0 | 2026-11-20 |
| ULHC_OHLCV.csv | 713 | 227 | 0 | 2026-11-20 |
| UMHL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| UMRH_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| UNHPL_OHLCV.csv | 1651 | 227 | 1 | 2026-11-20 |
| UNLBP_OHLCV.csv | 7 | 0 | 0 | outside window |
| UNLB_OHLCV.csv | 935 | 306 | 0 | 2026-11-20 |
| UNL_OHLCV.csv | 845 | 259 | 0 | 2026-11-20 |
| UPCL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| UPPER_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| USHEC_OHLCV.csv | 936 | 306 | 0 | 2026-11-20 |
| USHL_OHLCV.csv | 930 | 304 | 0 | 2026-11-20 |
| USLB_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| VLBSPO_OHLCV.csv | 18 | 0 | 0 | outside window |
| VLBS_OHLCV.csv | 931 | 304 | 0 | 2026-11-20 |
| VLUCL_OHLCV.csv | 935 | 305 | 0 | 2026-11-20 |
| WNLBP_OHLCV.csv | 7 | 0 | 0 | outside window |
| WNLB_OHLCV.csv | 890 | 261 | 0 | 2026-09-03 |
| YMHL_OHLCV.csv | 97 | 97 | 0 | 2026-11-20 |

Cumulative result: **525/525 files inspected (100%)**. The strict OHLC range scan found **13 invalid rows across 11 symbols** in the candidate date interval. This is not a claim that all remaining rows are verified; the scan is only an arithmetic/range check and file coverage inventory. The interval still lacks an approved official session calendar and independent point-in-time publication provenance.

### Final anomaly register from the one-year candidate window

| Symbol | Date | Archive O/H/L/C | Independent secondary evidence | Current disposition |
|---|---|---|---|---|
| API | 2026-04-27 | 339.9/345/340/341 | Financial Notices and Sun Securities repeat 339.9/345/340/341; floorsheet mirror had two 331.8 contracts, timestamps blank | User-directed provisional working open 340.0 only; raw unchanged; unresolved/quarantined |
| BGWT | 2026-04-29 | 740/731/718/730 (adjusted archive) | Sun Securities, ArthaKendra and Financial Notices report unadjusted 720/731/718/730, volume 1,573 | Adjustment-basis mismatch; raw retained; canonical series must distinguish adjusted/unadjusted |
| HRL | 2026-04-29 | 685.5/685/676.1/679.2 | Sun Securities reports 679.2/685/676.1/679.2, volume 74,867 | Secondary candidate open differs; raw retained/quarantined pending primary proof |
| KDBY | 2026-04-29 | 11.54/11.50/11.25/11.38 | ArthaKendra reports 11.25/11.50/11.25/11.38, volume 23,420 | Secondary candidate open differs; raw retained/quarantined |
| KEF | 2026-04-28 | 10.89/10.80/10.70/10.79 | ArthaKendra repeats the same invalid OHLC and volume 5,400 | Shared-source error possible; unresolved/quarantined |
| MERO | 2026-04-24 | 731.1/730/720/726 | Sun Securities repeats same values and volume 1,671 | Secondary source corroborates invalid published values, not validity; unresolved/quarantined |
| RADHI | 2026-04-29 | 780/775/755/764.8 | ArthaKendra reports 775/775/755/764.8, volume 57,510 | Secondary candidate open differs; raw retained/quarantined |
| RAWA | 2026-04-27 | 648.7/645/625/630 | Sun Securities and ArthaKendra repeat same invalid values and volume 3,747 | Unresolved/quarantined |
| RAWA | 2026-04-29 | 615/610/587/610 | Sun Securities and ArthaKendra report 610/610/587/610, volume 2,840 | Secondary candidate open differs; raw retained/quarantined |
| SPDL | 2026-04-28 | 408/406.3/396/399 | Sun Securities reports same values and volume 64,356 | Secondary source corroborates invalid values, not validity; unresolved/quarantined |
| UAIL | 2026-04-24 | 449.9/449.8/440.5/445.1 | ArthaKendra repeats same values and volume 4,553 | Shared-source error possible; unresolved/quarantined |
| UAIL | 2026-04-29 | 446/444.9/438/438 | ArthaKendra reports 442.6/444.9/438/438, volume 9,360 | Secondary candidate open differs; raw retained/quarantined |
| UNHPL | 2026-04-29 | 487.9/487/475/475.4 | Financial Notices shows values 475.4/487.9/487/475 (published ordering appears to place close first) | Reproduces the same values; unresolved/quarantined |

All external price-history pages above are secondary sources, not Chukul or NEPSE Alpha chart screenshots. Chukul Technical Desk remained inaccessible without sign-in and its public fetch returned no readable chart data. NEPSE Alpha chart route exposed login/register, not a historical candle. Therefore none of the rows in this anomaly register is claimed as independently captured from Chukul or NEPSE Alpha. No raw OHLCV file has been modified.

### One-year audit gate status after full file scan

- **File inventory and strict OHLC range scan:** complete for all 525 ticker CSVs in this directory.
- **OHLC anomaly triage:** 13 candidate rows identified; no silent repairs. External secondary evidence recorded where available.
- **Coverage and listing lifecycle:** not yet complete. Zero-row-in-window and sparse files require security type, listing/issue dates, suspension/delisting and corporate-event review.
- **Session completeness:** not verified. Session calendar CSV remains header-only; no date-by-date primary NEPSE session register has been completed.
- **Point-in-time provenance:** not verified for all rows. Existing archive presence does not establish when each datum became publicly available or when it was retrieved.
- **Adjustment/corporate-action basis:** not yet normalized for every symbol. Adjusted/unadjusted series must remain separate.
- **Market index, sector and broker/floorsheet coverage:** separate audits remain pending.
- **V1 acceptance:** **not passed**. Do not mark one-year data gate complete. Keep six-month fallback as contingency only after the remaining one-year blockers are assessed; do not downgrade scope prematurely.


## Supplemental repository audit — market, broker, floorsheet and calendar inputs

After the 525/525 stock-file scan, the remaining SMC repository paths were inventoried (628 tracked blobs total; 525 are the stock-chart CSVs).

### Session calendar defect found and isolated

The main-branch `nepse_session_date.py` currently assumes Saturday/Sunday are non-trading days for every date. That is historically wrong for this V1 window: NEPSE traded Sunday–Thursday until the schedule change effective 2026-04-06, then moved to Monday–Friday. This can misassign a fallback date for a historical scrape and can also distort any weekend-only inferred session calendar.

A separate draft fix PR was opened:
- https://github.com/jaljala044/nepse-smc-data/pull/3
- Branch: `fix/historical-nepse-weekend-regime`
- Changes: date-aware weekend regime, unit tests at the 2026-04-06 boundary, focused GitHub Actions test workflow.
- The helper explicitly does not claim to know public holidays, exceptional closures or special sessions. A date-specific official NEPSE calendar is still required.
- PR is open/draft and has not been merged.

Schedule evidence: The Himalayan Times reported the change as effective April 6, 2026; ShareSansar reported NEPSE's public notice on April 8. Sources: https://thehimalayantimes.com/business/nepse-shifts-to-mondayfriday-trading-week and https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08

### Floorsheet collection and broker-flow coverage

- Repository currently contains 41 `scanner_inputs/broker_summary/YYYY-MM-DD.csv` partitions, dated 2026-07-24 through 2026-11-20. This is not 41 consecutive sessions and does not provide a full year of broker history.
- Coverage metadata is inconsistent and needs reconciliation before use as a certified count: `scanner_inputs/audit/source_coverage.json` describes 20 complete sessions from 2026-10-12 to 2026-11-20 and 980,072 trade rows; `audit/backfill_manifest_2026-11-22.json` says 20 sessions were added with 1,062,269 reconciled trades and 40 total repo sessions after update; README says the broker folder now has 41 reconciled sessions and describes 1,062,269 trades for the added set. The current directory has 41 dated partitions. Do not merge these counts into one claim until each partition's source and totals are re-reconciled.
- `floorsheet/` currently contains raw daily CSVs for November 20, 23 and 24 only; `02_floorsheet_daily/` contains November 19 and 20. This is useful recent evidence but not a one-year raw tape.
- The November 24 audit records 105 Chukul pages, 52,387 contracts, 14,670,177 shares, NPR 5,553,019,249.46 turnover and 350 securities, with all 350 per-security totals checked and a 500-contract Merolagani sample. This is one-session coverage, not historical coverage.
- Main-branch `github_floorsheet_pull.py` still saves collected rows after a pagination timeout or stalled page; it can publish an incomplete partial file. Draft PR #2 adds fail-closed pagination, retries, duplicate/schema checks, atomic CSV write and manifest, with tests passing, but no live Chukul pagination test. https://github.com/jaljala044/nepse-smc-data/pull/2
- Keep PR #2 open until live pagination and independent contract-count reconciliation are demonstrated.

### Daily market, index, sector and corporate-action coverage

- `00_daily_eod_prices/` has only three dated daily snapshots (2026-11-18, 2026-11-23 and 2026-11-24) plus static price/dividend/right-share exports. The 525 stock-chart files provide the historical bars; these three snapshots are not a substitute for historical daily EOD provenance.
- `market_summary_daily.csv` is documented as 195 sessions in 2026, but transaction counts appear only on tape-reconciled dates and breadth is populated only for November 20. Reconcile its session list against the official date calendar before using it as a complete daily market series.
- `benchmark_daily.csv` has 128 bars. Sector classification has 281 symbols; sector history has 1,534 bars across 12 sectors. README explicitly says historical sector memberships before November 20 remain unverified.
- `corporate_actions.csv` has only three documented events (LBBL bonus, DORDI rights, BNHC rights). The sample is incomplete and does not justify globally adjusted history. NLIC proposed split remains unverified; no split factor was imported.
- The November 24 index audit leaves multiple index opens unresolved/conflicting across ShareSansar and ShareHub; the daily index CSV has blank opens for NEPSE, Sensitive, Float, Sensitive Float, Banking, Hotels & Tourism, Hydro Power and Others. Index values must not be treated as full OHLC where opens are absent.
- The November 24 turnover differs by NPR 0.01 between the market/EOD reconciliation and the ShareHub live display. Preserve exact source-specific amounts and record the one-paisa discrepancy rather than forcing equality.

### Additional source quality exclusions already recorded in the repository

- Viking source: all 20 examined floorsheets had fewer trades than published session totals; none was accepted as fully reconciled.
- Pinned Aabishkar2 archive: 124 company files, 233,328 rows, 29,090 OHLCV/turnover check failures, 686 duplicate symbol-date rows, 104 out-of-sequence dates; latest date 2024-11-26. None of those raw files entered the scanner inputs.
- SocrateAI adjusted history: sampled rows do not establish a consistent adjustment methodology or event timing; do not mix adjusted and unadjusted prices.

### Updated gate interpretation

The stock-file arithmetic scan is complete (525/525), but one-year V1 data acceptance is still blocked by: official date-level session calendar; historical point-in-time publication/ingestion provenance; unresolved 13 OHLC anomaly rows; incomplete security lifecycle and corporate-action coverage; inconsistent broker coverage metadata; only partial historical raw floorsheet coverage; unresolved index OHLC opens; and incomplete historical sector membership. No release gate is passed by file-count completion alone.
