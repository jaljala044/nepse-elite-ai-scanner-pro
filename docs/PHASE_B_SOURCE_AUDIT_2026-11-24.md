# Phase B — Historical archive acquisition and audit gate report
Generated: 2026-11-24
Status: partial execution; no canonical import authorized

## Executive status

The live Git tree inventories and a targeted row-level comparison are complete for the three owner-controlled Jaljala repositories and three public GitHub sources. This is not yet a full data acquisition or full archive audit. Binary bulk downloads, full row-level audits of all 500+ symbols, full floorsheet reconciliation, database dry-runs, and permission review for external datasets remain outstanding.

No source data has been promoted into the canonical database. Raw source archives remain source-separated.

## Live repository snapshots

The following are exact recursive Git tree snapshots from the GitHub API. The listed hashes are tree SHAs, not commit SHAs.

| Repository | Tree SHA | Files | Bytes | Inventory result |
|---|---|---:|---:|---|
| jaljala044/nepse-smc-data | 737ad091393656de6a8e866673012b6b5fc9bdbb | 622 | 39,541,608 | OHLCV, broker summaries, indices, EOD and selected floorsheets |
| jaljala044/nepse-history-starter | 227c2f5e7d6a0b9594b79718afb9a2c0c692492a | 602 | 35,557,130 | 525 OHLCV files plus scanner inputs/import examples |
| jaljala044/nepse-automation | 4cb97caa83912cdb56aca4238b10d99cf651c223 | 3 | 4,317 | Fetch script and two workflows; not a historical archive |
| socrateai-official/nepse-open-data | f602a5b61e68582d28834d16f71151a4bae98d5b | 14,460 | 3,173,510,750 | 658 floorsheet session files; EOD/adjusted/index files |
| SamirWagle/Nepse-All-Scraper | 144cecb36f110bedb741f5d147c7857cdb24c958 | 1,631 | 839,582,556 | 179 unique dated floorsheet sessions; company price/corporate-action files |
| srijankarki07/nepse-data | b8c34710c48a23efa9d0088c58781ab02a760c73 | 4,623 | 70,517,420 | Annual EOD and daily archives; data explicitly excluded from software MIT license |

All six Git trees returned complete (not truncated) responses.

## Jaljala OHLCV overlap audit

- Both `nepse-smc-data` and `nepse-history-starter` contain 525 OHLCV files.
- All 525 ticker paths overlap.
- 500 file blobs are byte-identical.
- 25 file blobs differ.
- The 25 differing files were fetched and compared by date after numeric normalization (so formatting such as `179.7` vs `179.70` is not treated as a market-data conflict).
- Across those files there are 14,856 shared ticker-date rows and 8 actual numeric OHLCV disagreements.
- These are unresolved source conflicts. Neither repository is automatically declared authoritative for these rows.

| Symbol | Date | SMC repository OHLCV | History Starter OHLCV | Conflict |
|---|---|---|---|---|
| API | 2026-11-19 | 331, 334.2, 330.2, 333, 26717 | 331, 334.2, 330, 331.8, 105340 | Low, close and volume |
| BGWT | 2025-07-28 | 940, 992, 933.4, 957.17, 14028 | 940, 992, 933.4, 945, 14028 | Close |
| HRL | 2026-11-19 | 483, 488, 480, 486, 18817 | 483, 488, 480, 483.9, 49184 | Close and volume |
| MEHL | 2025-07-28 | 471.1, 480.5, 460, 475.63, 29753 | 471.1, 480.5, 460, 470.83, 29753 | Close |
| RAWA | 2025-07-28 | 796, 811, 780.3, 796.9, 3165 | 796, 811, 780.3, 794.83, 3165 | Close |
| RHGCL | 2025-07-28 | 346.7, 362, 341.4, 357.05, 296715 | 346.7, 362, 341.4, 350.07, 296715 | Close |
| RHGCL | 2026-11-19 | 252.1, 259.5, 252.1, 256, 4216 | 252.1, 259.5, 252.1, 258, 9054 | Close and volume |
| ULHC | 2025-07-28 | 509, 515, 495, 510.75, 32288 | 509, 515, 495, 504, 32288 | Close |

The backfill report's previously published eight-row discrepancy count is consistent with this independent comparison. Before resolving any of the eight, compare against a third source and/or the original exchange record where available.

## Floorsheet coverage inventory

| Source | Dated files | Unique dated sessions | First path date | Last path date | Important caveat |
|---|---:|---:|---|---|---|
| Jaljala SMC | 4 raw CSV paths across two folders | 3 | 2026-11-19 | 2026-11-23 | Selected recent dates only; one date occurs in two folders |
| SocrateAI | 658 | 658 | 2024-01-01 | 2026-11-19 | About 3.12 GB; fetch selectively after session-set comparison |
| Samir scraper | 181 matching paths | 179 | 2026-02-22 | 2026-11-24 | Two additional matching paths do not create extra unique dates; upstream terms unresolved |

Calendar gaps in path dates are review flags, not proof of missing sessions. They must be compared with an authoritative NEPSE session calendar, holidays, historical weekday changes and market closure records.

## Jaljala automation security finding

`nepse-automation/fetch_floorsheet.py` explicitly calls `setTLSVerification(False)`. This disables certificate verification and is not acceptable for production collection. The script also names the output tab using the machine's local date rather than verified exchange-session metadata. Do not run it unchanged. Replace TLS bypass with normal certificate verification, pin dependencies, preserve the raw response, and derive the session date only from verified response metadata.

The automation repository contains no historical archive in its current tree. It is a workflow/reference source, not an additional historical dataset.

## Additional source selection and rights

1. **SocrateAI**: repository includes an MIT license and is the leading candidate for EOD/index supplements and selective floorsheet gap fills. Keep source attribution and license notice. Validate every file before use.
2. **Urekmazino69 Hugging Face**: publisher declares MIT and exposes a transaction-level floorsheet schema with broker codes, quantity, rate, amount and a time field that is often null. Use as a candidate for 2024–2026 floorsheet backfill; do not infer timestamps where null.
3. **AnkitSanjyal Hugging Face**: dataset license is listed as `other`. Keep in a research/quarantine lane until its data-use terms are clarified. Derived broker-flow is not raw order flow or beneficial-owner identity.
4. **SamirWagle**: use as an independent comparison candidate only until upstream rights and redistribution terms are established.
5. **srijankarki07/nepse-data**: its LICENSE excludes collected data from the software MIT license. Do not copy its data into the canonical archive based on the code license alone.

## Audit gates

| Gate | Status | Evidence / blocker |
|---|---|---|
| G0 Repository access and immutable tree snapshots | PASS | Six complete Git trees; tree SHAs recorded above |
| G1 Jaljala ticker-file overlap | PASS | 525/525 ticker paths overlap; 500 identical blobs; 25 differing blobs |
| G2 Targeted numeric row reconciliation | PASS WITH EXCEPTIONS | 14,856 shared dates; 8 numeric disagreements identified and listed |
| G3 Full OHLCV validation across all 525 tickers | FAIL / REVIEW REQUIRED | Run 45363122305 completed; 1,331 OHLCV invariant failures in SMC archive, zero in History Starter; no duplicates or out-of-order rows; see findings below |
| G4 Exchange-session calendar validation | BLOCKED | Need a verified historical NEPSE session/holiday calendar; weekday heuristic alone is insufficient |
| G5 Floorsheet schema, completeness and cross-source reconciliation | BLOCKED | Full bulk files not downloaded and audited; execution times may be absent |
| G6 Broker summary provenance and aggregation audit | BLOCKED | 41 daily summaries identified; raw source rows and calculation formulas need full verification |
| G7 Corporate-action reconciliation | BLOCKED | Need authoritative action dates/ratios and adjusted-vs-unadjusted lineage |
| G8 External data rights | PARTIAL | SocrateAI/Urek MIT claims recorded; Samir upstream rights and Ankit 'other' terms unresolved; Srijan data excluded |
| G9 Database dry-run and idempotency | NOT STARTED | No database import or write attempted |
| G10 Canonical promotion | NOT AUTHORIZED | Requires all relevant upstream gates and explicit rights approval |

## Engineering follow-up

1. Build a verified exchange session calendar with source and effective-date provenance.
2. Run the full 525-symbol OHLCV row audit against both Jaljala repositories, including duplicates, ordering, OHLC constraints, volumes, weekend/carry-forward rows and source overlaps.
3. Resolve the eight known disagreements only with independent evidence; otherwise preserve both candidates and mark the date conflicted.
4. Compare SocrateAI, Urek and Jaljala floorsheet session sets; fetch only missing/needed dates and retain immutable raw files with SHA-256.
5. Audit broker summaries against their raw inputs and retain buyer/seller broker codes as reported identifiers, not named institutions or beneficial owners.
6. Run import dry-runs with zero writes, then idempotency tests before any canonical promotion.

## Execution and CI status

- GitHub source-inventory workflow run 45360883376 completed successfully and uploaded artifact `nepse-github-source-inventory` (artifact SHA-256: `fe17dcf06bd5835cc48ff3903ee0b8fd3fb294f4d1f87a6cf69f944bb1053a0a`).
- Backend tests run 45360933245 completed successfully on the observed main-branch head.
- The HF inventory workflow has not yet been observed in the current recent-run listing.
- Successful CI validates the code/workflow job, not the completeness or correctness of the underlying market data.

## Non-actions

No bulk archive was downloaded in this phase. No database writes, source overwrites, adjusted-price transformations or scanner signal generation were performed.


## Phase B implementation added after initial report

- `backend/audit_ohlcv_archives.py`: pinned-commit, read-only OHLCV downloader/auditor for both Jaljala OHLCV archives. Records source commit/tree IDs, file SHA-256, row counts, date ranges, invalid OHLC, non-integer/negative volume, duplicate dates, ordering, repeated adjacent calendar rows and cross-source row conflicts. It never writes to the source repositories or database.
- `backend/tests/test_audit_ohlcv_archives.py`: parser tests for numeric formatting normalization, duplicate dates, ordering, OHLC constraints and volume validation.
- `.github/workflows/ohlcv-archive-row-audit.yml`: runs the pinned archive audit and uploads the JSON report as a workflow artifact.
- Backend test run `45363122243` completed successfully.
- OHLCV audit run `45363122305` is currently in progress. Its parser-test step completed successfully; the full repository download/audit step has not yet reported a result.


## Full OHLCV audit findings (run 45363122305)

The pinned audit downloaded and parsed all 525 ticker CSVs from each Jaljala repository with zero download errors.

| Repository | Files audited | Rows | Invalid OHLCV rows | Duplicate dates | Out-of-order transitions | Repeated adjacent calendar bars |
|---|---:|---:|---:|---:|---:|---:|
| jaljala044/nepse-smc-data | 525 | 314,712 | 1,331 | 0 | 0 | 94,421 |
| jaljala044/nepse-history-starter | 525 | 301,632 | 0 | 0 | 0 | 102,121 |

The 1,331 invalid rows are all in the SMC archive: 796 rows where High is below Open/Low/Close and 535 rows where Low is above Open/High/Close. They affect 15 symbols and 993 distinct dates, concentrated in older history (2009–2020) with 13 rows in 2026. The largest counts are AHPC (588), SKBBL (379), API (122), MERO (102), SPDL (53), CHL (45), and HIDCL (30). These records must remain quarantined pending independent evidence.

A spot-check against SocrateAI's MIT-licensed unadjusted EOD archive confirms that some Jaljala invalid fields are incorrect:
- AHPC, 2009-11-25: Jaljala SMC Open=408 while High/Low/Close=790; SocrateAI reports Open/High/Low/Close=790.
- API, 2015-11-18: Jaljala SMC Open=0 while the other fields indicate 301–307; SocrateAI reports Open=301, High=307, Low=301, Close=307.
- BGWT, 2026-04-29: Jaljala SMC Open=740 exceeds High=731; SocrateAI reports Open=720, High=731, Low=718, Close=730, but volume differs (1,549 vs 1,573).

The 94,421 and 102,121 repeated-adjacent counts are not automatically invalid. A KBSH sample shows identical full OHLCV rows carried from 2024-03-07 to 2024-03-08 and 2024-03-09; Friday/Saturday are non-session days in the then-current NEPSE week. Other repeated rows may represent holidays, no-trade sessions, or stale carry-forward records. They require the verified historical session calendar and should be tagged/quarantined, never counted as fresh trading observations without evidence.

## Targeted independent EOD cross-check

Added `backend/crosscheck_ohlcv_socrateai.py` and tests. The updated workflow `ohlcv-archive-row-audit` now fetches only SocrateAI unadjusted EOD daily files for dates implicated by OHLCV validation failures and cross-source conflicts. It compares source fields but never auto-selects a value. The updated run is `45363518640`; its result is pending at the time of this report update.

The first full audit artifact is available from run `45363122305` (artifact `nepse-ohlcv-row-audit`, SHA-256 `e76d32769e7347130a54e5b94473c9809ad9af8ac1799d98a66fea171bf2df4f`). The audit failed its quality gate by design and uploaded its report successfully.
