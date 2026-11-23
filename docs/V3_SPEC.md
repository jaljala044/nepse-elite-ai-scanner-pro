# V3 scanner — initial specification

## Goal
Build a modular, explainable NEPSE research scanner that can begin with approximately one year of daily OHLCV. V3 is a research and validation system, not an automated trading system and not a source of guaranteed predictions.

## Initial scope
1. Validate and normalize daily OHLCV input.
2. Calculate SMA20/SMA50, 20-session return, RSI14, ATR14 and volume expansion.
3. Describe trend/momentum/volatility conditions with explicit evidence.
4. Return an explicit insufficient-data or data-quality status rather than filling gaps.
5. Keep broker/floorsheet evidence as an optional, separately sourced module.
6. Preserve the legacy scanner and expose V3 as a separate module until parity and tests are established.

## Daily bar contract
Each observation must contain:
- `date`: ISO date string (`YYYY-MM-DD`) or a date object.
- `open`, `high`, `low`, `close`: finite positive numeric prices.
- `volume`: finite non-negative numeric quantity.

Rows must represent one symbol and one trading session per date. Duplicate dates are a data-quality error. The caller is responsible for source provenance, symbol mapping, corporate-action adjustment policy, and verified trading-calendar checks. V3 must not infer or fabricate missing sessions.

## Initial feature definitions
- SMA20/SMA50: arithmetic mean of the most recent 20/50 closes.
- Return20: close-to-close percentage change over 20 session intervals.
- RSI14: Wilder-smoothed relative strength using the latest 14 price changes.
- ATR14: Wilder-smoothed true range using prior close.
- Volume ratio20: latest volume divided by mean volume over the latest 20 sessions.
- Trend state: descriptive close/SMA alignment only; no claim of institutional intent.
- Volume expansion: ratio20 >= 1.5, a configurable observation threshold, not a buy/sell signal.

## Output and safety semantics
- Status is one of `ready`, `insufficient_data`, or `data_quality_error`.
- Every metric is accompanied by a stable rule/evidence label where applicable.
- Missing or invalid fields are reported; source rows are never silently repaired.
- No order placement, personalized financial recommendation, guaranteed accuracy, or claim of manipulation/accumulation from OHLCV alone.
- Broker IDs are execution-channel identifiers, not beneficial-owner identities. Flow claims require separately validated provenance and coverage.

## DuckDB coverage audit integration

- `GET /v3/audit/coverage` reads `ankit.eod_price` directly from the source-separated DuckDB warehouse in read-only mode.
- Default database path is `<repository-root>/data/warehouse/nepse-analytics.duckdb`; deployments can override it with `NEPSE_DUCKDB_PATH`.
- The endpoint streams query batches into the existing coverage auditor and supports an optional `as_of` cutoff and target universe count.
- It does not assume that a target count of 309 identifies the authoritative 309 symbols. Until an authoritative symbol master is supplied, missing-symbol names cannot be enumerated.
- It does not infer missing sessions without a verified exchange calendar. No data is inserted, updated, repaired, or deleted.

## Validation plan
- Unit tests for short history, duplicate dates, malformed OHLCV, flat prices, indicator calculations, and deterministic outputs.
- Compare features against an independent implementation on fixed fixtures.
- Run historical walk-forward evaluation with time-ordered splits, realistic costs, no look-ahead, and a held-out period.
- Report coverage and missingness per symbol before scanning the full universe.

## Planned modules
- `data_quality`: schema, duplicates, missing sessions, provenance.
- `market_regime`: NEPSE index and breadth.
- `price_volume`: trend, momentum, volatility, volume.
- `market_structure`: confirmed swings, BOS/CHoCH and liquidity references with delayed confirmation.
- `flow_intelligence`: floorsheet/broker observations only where validated.
- `scoring`: explainable evidence aggregation and later calibration.
- `backtest`: walk-forward research and audit outputs.

## Delivery gates
V3 remains development-only until the data coverage audit, independent indicator checks, and out-of-sample validation pass. The first release may report descriptive observations while suppressing any unvalidated composite score.
