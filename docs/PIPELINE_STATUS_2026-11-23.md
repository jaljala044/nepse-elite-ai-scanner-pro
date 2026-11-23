# NEPSE data pipeline status — 2026-11-23

## Executive status

The repository has a tested ingestion foundation and successful bounded real-data validations. It is **not yet a complete historical database or production scanner**. No full archive has been normalized and reconciled, and the current scanner remains a basic OHLCV screen.

## Verified in GitHub Actions

### Floorsheet CSV.GZ sample — 2024-01-02

- Source: `urekmazino69/Nepse-floorsheet-and-indices`
- File: `2024-01-02.csv.gz`
- SHA-256: `6fc5025469411ce9fb64a2b4c56854d32a3da12528f6f0cf4584468ee5f66cbd`
- Rows seen / accepted / rejected: 85,435 / 85,435 / 0
- Silver output: `data/silver/floorsheet/date=2024-01-02/floorsheet.csv`
- Independent audit: 1 partition, 1 session, 85,435 rows, 0 duplicates, 0 date mismatches, 0 arithmetic errors.

### Sector-index CSV.GZ sample — 2024-01-02

- 16 rows accepted in the sample.
- Independent index audit completed successfully with no duplicate date/sector keys, date mismatches, or OHLC range errors.

### Hugging Face source inventory

Inventory-only scan (not a full download) measured the Urek archive:

| Dataset folder | Files | Compressed size | Path-date range |
|---|---:|---:|---|
| floorsheet | 603 | 723.767 MiB | 2024-01-02 to 2026-08-26 |
| indices | 6,429 | 4.257 MiB | 1997-07-20 to 2026-08-26 |
| Total | 7,032 | 728.024 MiB | 1997-07-20 to 2026-08-26 |

These are repository file inventory measurements, not row-level validation or proof of every expected exchange session.

### AnkitSanjyal Parquet inspection

GitHub Actions downloaded and inspected all 306 files in the bounded public dataset inventory. All 306 inspected; 0 file inspection failures; each table had one observed schema variant.

| Table | Files | Rows | Observed date range |
|---|---:|---:|---|
| eod_history_ext | 1 | 516,620 | 1995-07-20 to 2026-08-19 |
| eod_price | 277 | 93,859 | 2025-08-19 to 2026-11-20 |
| floorsheet | 7 | 330,978 | 2026-08-19 to 2026-11-20 |
| broker_flow_daily | 7 | 81,418 | 2026-08-19 to 2026-11-20 |
| bars_1m | 7 | 114,537 | 2026-08-19 to 2026-11-20 |
| daily_stats | 7 | 2,441 | 2026-08-19 to 2026-11-20 |

Important: the seven floorsheet/broker-flow partitions are not a continuous daily history. The long EOD table has not yet been independently reconciled against an authoritative NEPSE source. The Parquet inspection proves readable schemas and row counts, not semantic correctness or completeness.

### DuckDB warehouse and EOD overlap

A source-separated DuckDB loader has been added for all six Ankit Parquet tables. Its first real-data run loaded all six tables but correctly stopped at the initial OHLC gate. Findings from that run:

- Floorsheet: 330,978 rows, 399 symbols, 0 duplicate keys, 0 invalid trade values, 0 quantity × rate amount mismatches over NPR 1.
- Broker flow: 81,418 rows, 0 duplicate keys, 0 net-quantity mismatches, 0 net-value mismatches over NPR 1.
- 1-minute bars: 114,537 rows, 0 duplicate keys, 0 OHLC anomalies.
- Daily stats: 2,441 rows, 0 duplicate keys, 0 negative volume/turnover rows.
- EOD overlap: 75,671 matching symbol/date pairs; volume matched exactly in all 75,671; close matched within NPR 0.01 in 75,657; maximum absolute close difference NPR 60.
- The initial OHLC check flagged 578 rows in `eod_price` and 40,373 in `eod_history_ext`. These source rows were retained; they were not silently deleted or repaired.

The loader was then changed to preserve source OHLC rows and report anomalies as review warnings, with symbol-level examples. The post-change real-data workflow was started on 2026-11-23 and is awaiting its final result. Until that run passes, the DuckDB real-data load is not marked accepted.

### Automated tests and decimal serialization

- Backend unit tests: 21 passed in GitHub Actions on 2026-11-23, including a test that keeps the two EOD source tables separate and verifies overlap reconciliation.
- Decimal audit fix: broker turnover values are serialized as decimal strings, preserving precision.
- Post-fix floorsheet smoke test and audit passed.

## Remaining blockers — not marked complete

1. **Full Urek archive import:** 603 floorsheet and 6,429 index files are inventoried, but the complete archive has not been downloaded, normalized, and audited. The one-session sample must not be represented as full-history validation.
2. **Kaggle legacy archive:** the staging helper exists, but actual download requires the owner's locally configured Kaggle CLI/account. Dataset metadata describes coverage through 2019-10-10; the date field/schema must be validated before merging.
3. **Cross-source reconciliation:** overlap checks, trading-calendar-aware missing-session checks, corporate-action handling, symbol master mapping, and conflict resolution remain outstanding.
4. **Parquet warehouse acceptance:** the source-separated DuckDB loader is implemented and its first real-data run surfaced OHLC anomalies plus 14 close-price differences in the EOD overlap. The revised warning/reporting path is awaiting a successful real-data rerun. No canonical silver merge or CSV-source reconciliation has been approved.
5. **Broker-flow research:** broker IDs remain execution-channel identifiers, not beneficial-owner identities. Any accumulation/distribution score needs source provenance, aggregation-window validation, and independent backtesting.
6. **Scanner:** current `backend/app/scanner.py` computes only basic SMA20, 20-session change, and volume-vs-average metrics. It is not the requested 309-stock multi-module SMC/IPDA engine.
7. **Production product:** database persistence, complete web dashboard, Android app, authentication, deployment, monitoring, authorized live feeds, and scheduled scans are not yet implemented/verified.

## Safe next acceptance sequence

1. Run the full bounded Urek download in a persistent, adequately provisioned environment; retain raw files and source hashes.
2. Normalize every file and produce per-file/session manifests, quarantine reports, and independent audit summaries.
3. Obtain and stage the Kaggle archive using the account owner's local credentials; validate dates and schemas before any merge.
4. Inspect and normalize Parquet tables separately; reconcile overlapping sessions and symbol identities without silently overwriting conflicts.
5. Build a trading-calendar-aware coverage matrix and authoritative-source reconciliation report.
6. Only after data gates pass, implement and walk-forward test the research modules and 309-stock scanner.
7. Build/deploy the web and Android product only after the data and analytical interfaces are stable.

No fabricated dates, rows, broker identities, live prices, or scanner signals should be used to fill gaps.
