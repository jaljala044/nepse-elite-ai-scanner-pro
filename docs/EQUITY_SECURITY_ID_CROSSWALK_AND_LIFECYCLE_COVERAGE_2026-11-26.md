# Equity security-ID crosswalk and lifecycle coverage gate — 2026-11-26

## Current snapshot crosswalk

The 281-symbol equity candidate set was reconciled against `data/reference/nepse_security_id_snapshot_2026-11-25.csv`.

Results:
- 281 candidate equity symbols reconciled.
- 281/281 symbols have a matching security ID in the 2026-11-25 snapshot.
- 281/281 snapshot rows are marked active (`A`).
- 0 symbol-to-ID mismatches; 0 missing snapshot matches.
- 281/281 rows report an OHLCV file present in the snapshot inventory. This is file-presence evidence only, not proof of valid rows, complete date coverage, or canonical promotion.
- The original target-universe candidate file contains 278 equity rows and 47 mutual-fund rows. The additional three equities are NESDO, ULBSL and YMHL, separately supported by the Priority 94 classification review.
- The three additions' snapshot IDs are NESDO/8041, ULBSL/8063 and YMHL/9342.

Derived crosswalk:
`data/reference/nepse_equity_security_id_crosswalk_2026-11-26.csv`

The crosswalk retains the current-snapshot IDs and status; it does not recover predecessor IDs, infer historical continuity, or splice OHLCV.

## Lifecycle coverage finding

The current snapshot is an as-of identity snapshot, not a lifecycle registry. It does not establish a reliable `valid_from` for all 281 securities. Therefore, the system must not manufacture a first-trading date from file presence or the earliest row in a potentially incomplete archive.

Only YMHL currently has an explicitly cited listing/trading-start event in the existing Priority 94 evidence review (NEPSE listing 2026-06-19; trading commenced 2026-06-22). This does not resolve lifecycle dates for the other 280 securities.

## Coverage-engine hardening

Updated `backend/build_security_coverage_report.py`:
- Blank `valid_from` is now represented as `unverified_missing_valid_from`.
- Securities with unknown lifecycle starts are excluded from expected-session denominators and are not falsely reported as missing-session failures.
- Their observed rows are not misclassified as outside the effective interval solely because the start date is unknown.
- Per-source output now reports lifecycle-unverified counts and symbols.
- Duplicate in-scope symbols with an unknown start date fail closed because non-overlapping lifecycle intervals cannot be established.

Regression tests added for the unknown-lifecycle case and ambiguous duplicate-symbol overlap. The existing explicit-session-only denominator and per-publisher separation remain intact.

## Current disposition

- **Identity mapping:** snapshot-level match 281/281; high confidence for the dated snapshot only.
- **Lifecycle completeness:** insufficient evidence; low confidence.
- **OHLCV coverage:** 281 files present, but session coverage cannot be validly computed for securities lacking verified lifecycle starts and the complete official session calendar.
- **Canonical promotion:** not allowed.
- **Training:** not allowed.

The next data task is to collect independently evidenced listing/trading-start and delisting/suspension intervals, then reconcile OHLCV rows against verified exchange sessions. The 2026-11-25 current-snapshot policy remains in force; former merger tickers are not reintroduced.

## CI

Full backend unit-test discovery passed on the crosswalk commit: [run 45833462850](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45833462850) — 736 tests passed.


## Lifecycle input artifact

Added `data/reference/nepse_equity_lifecycle_coverage_input_2026-11-26.csv` for all 281 equities:
- YMHL has a verified-secondary notice-based first trading date of 2026-06-22 (listing notice dated 2026-06-19).
- The other 280 `valid_from` values are intentionally blank and marked `unverified`; no earliest-archive-row inference was used.
- The file is a coverage input, not a claim that only YMHL has a known listing date. It reflects only the lifecycle evidence already captured in this repository.


## First-trade date reconciliation update — 2026-11-26

A dated cross-check in `jaljala044/nepse-smc-data/reference/first_trade_boundary_reconciliation_2026-11-26.md` reconciled eight additional equities using secondary published first-trade/debut reports and matching first positive-volume archive rows: APHL (2026-06-10), KHPL (2026-05-26), SKHL (2026-03-25), BJHL (2026-03-22), SOHL (2026-03-15), HFIN (2026-03-12), SABBL (2026-02-16), and RSML (2026-02-16). The dates were added to the lifecycle input with status `verified_secondary_first_trade_archive_match`, source URI and limitation notes. Together with YMHL (2026-06-22), 9/281 lifecycle starts are populated; 272 remain unknown. These are secondary evidence, not exchange-authenticated raw floorsheet records.

## OHLCV archive audit implementation

The data repository's read-only audit script now reports per-symbol file presence, SHA-256, archive boundaries, first/last positive-volume observations, malformed rows, duplicate dates, out-of-order dates, OHLC-bound violations, non-positive volume, adjacent identical OHLCV rows, and calendar status counts. It emits `summary.csv`, `row_flags.csv` and `totals.json` as workflow artifacts. It does not infer listing dates from archive boundaries or treat candidate weekdays as confirmed sessions. Script commit: [711e4e2](https://github.com/jaljala044/nepse-smc-data/commit/711e4e2162c886bf1506f18967073dbc42bd30b9).

**Current status:** implementation committed; full 281-security workflow artifact not yet verified. Existing comparison matches 276/281 equities; NESDO, SYPNL, ULBSL, USLB and YMHL are missing from compared OHLCV filenames. Calendar remains partial (225 sampled observed-open dates, 150 closed dates, 26 candidate weekdays). Canonical promotion and training remain blocked.
