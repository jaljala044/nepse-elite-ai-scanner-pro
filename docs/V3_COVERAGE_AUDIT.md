# V3 warehouse-backed OHLCV coverage audit

## Purpose
The audit reads the existing DuckDB database directly. It does not require manually exporting OHLCV rows to CSV. It produces a JSON report with per-symbol coverage, missing exchange sessions, duplicate symbol/session keys, invalid OHLCV rows, and overall universe coverage.

## Required warehouse inputs
The operator must identify three existing DuckDB tables:
- OHLCV: one row per symbol and trading session; default columns `symbol,date,open,high,low,close,volume`.
- Authoritative symbol master: one canonical symbol per row; default column `symbol`.
- Verified NEPSE session calendar: one actual exchange session date per row; default column `session_date`.

The audit deliberately does not invent table names, infer an authoritative 309-stock universe, or synthesize a calendar. It fails clearly if any required table is absent or empty. It counts only sessions in the calendar that fall within the OHLCV table's observed date range.

## Run
From `backend/`:

```bash
python -m app.coverage_audit \
  --database /absolute/path/to/existing.duckdb \
  --ohlcv-table main.eod_price \
  --symbol-master-table main.symbol_master \
  --calendar-table main.nepse_sessions \
  --output ../artifacts/v3_coverage_report.json
```

Replace the three example table names with the actual tables in the warehouse. Column-name overrides are available through `--symbol-col`, `--date-col`, `--open-col`, `--high-col`, `--low-col`, `--close-col`, `--volume-col`, `--master-symbol-col`, and `--calendar-date-col`.

## Interpretation
- `pass`: every expected session is present exactly once and every OHLCV row passes basic range/value checks.
- `review`: one or more sessions are missing, duplicate, or invalid.
- Per-symbol missing session dates are listed explicitly.
- Overall coverage is observed symbol/session pairs divided by master-symbol count × verified-calendar sessions.
- A complete coverage result does not independently certify source authenticity, corporate-action adjustment, or economic correctness.

## Current limitation
This code is connected to DuckDB at runtime but has not yet been run against the real warehouse: the repository status report does not establish the actual persistent database path, canonical 309-symbol master table, or verified session-calendar table. No real coverage percentage is claimed until those inputs are identified and the command is run.


## API option using configured reference tables

The application also exposes `GET /v3/audit/coverage/strict`. Configure the database and the two reference tables in the API environment:

```bash
NEPSE_DUCKDB_PATH=/absolute/path/nepse-analytics.duckdb
NEPSE_SYMBOL_MASTER_TABLE=reference.symbol_master
NEPSE_SESSION_CALENDAR_TABLE=reference.nepse_sessions
```

The default OHLCV table is `ankit.eod_price`, using `symbol`, `business_date`, `open_price`, `high_price`, `low_price`, `close_price`, and `total_traded_quantity`. Override table and column names with the `NEPSE_OHLCV_*`, `NEPSE_MASTER_SYMBOL_COL`, and `NEPSE_CALENDAR_DATE_COL` environment variables when needed. The example reference table names above are placeholders, not claims that those tables already exist.

If reference-table settings are missing, the endpoint returns HTTP 503. It never falls back to a synthetic 309-symbol list or a calendar inferred from weekdays. Before using results as a completeness claim, verify the master and calendar publishers, their effective dates, provenance, permissions, and content hashes.
