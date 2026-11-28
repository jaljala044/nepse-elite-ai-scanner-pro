# P4.38 — broker / price / volume / sector context

## Delivered implementation slice

This branch ports the P4.38 research-only implementation onto the current mainline without retargeting the older PR #216. It adds:

1. A deterministic broker/price/sector context calculator.
2. A server-owned session-calendar and quarantine gate.
3. A read-only daily broker-ledger adapter with manifest/payload integrity checks.
4. Conservative effective-dated lifecycle exclusions.
5. Concentration and comparable-window sector participation metrics.
6. Swing (5-session) and positional (21-session) research wrappers.
7. Stock-wise and broker-wise descriptive leaderboards.
8. A token-protected request perimeter with body-size and per-process rate limits.
9. API routes for context, mode, concentration, rotation, leaderboards and ledger coverage.
10. A browser research panel and focused backend regression suite.

## Calendar admission

The current calendar contains 3,630 `project_accepted_open` archive-derived dates, 40 `verified_closed` dates and one `verified_exceptional_closed` date. It contains no `verified_open` or `verified_exceptional_open` records. Project-accepted dates are explicitly not exchange-certified.

The server therefore returns `insufficient_evidence / calendar_project_accepted_not_exchange_verified` for these sessions. It does not silently upgrade the archive baseline to exchange verification. A future verified calendar record must include a valid UTC verification timestamp and pass the server-owned calendar check before a broker context can be calculated.

## Research-only controls

- Broker IDs remain execution-channel identifiers, not beneficial ownership.
- Incomplete sessions, missing prices, invalid OHLCV, ambiguous effective-dated sector membership, late evidence and quarantine overlap are withheld.
- Gross buy/sell sides are not collapsed into net flow; matched turnover is reconciled before concentration calculations.
- Sector rotation compares only identical broker/security scopes and non-overlapping windows.
- Ledger ingestion is read-only and does not publish per-security profiles until historical identity clearance is independently supported.
- ICT engine claims are rejected unless a separately versioned engine identifier and evidence digest are supplied; no combined score is calculated.
- All routes remain descriptive-only. `production_eligible=false`, `signals_enabled=false`; no BUY/SELL recommendation or order execution.

## API access

Set `NEPSE_BROKER_RESEARCH_TOKEN` in the API environment and supply it as a Bearer token. The middleware limits the listed research POST endpoints to 5 MiB and 30 requests per process per 60 seconds. This is a local process budget, not distributed rate limiting or user identity authentication.

The ledger adapter additionally requires `NEPSE_BROKER_LEDGER_PATH` pointing to the approved read-only DuckDB store. If unavailable, it returns `insufficient_evidence`.

## Acceptance status

This is a code and contract-test slice, not an evidence promotion or production deployment. The current calendar blocks live profile calculations until exchange-verified open-session evidence exists. Source payload authentication is not performed by the manual JSON context endpoint; its response explicitly records that limitation.

No source data was modified, no missing session was zero-filled, and no historical record was promoted to canonical or training data.
