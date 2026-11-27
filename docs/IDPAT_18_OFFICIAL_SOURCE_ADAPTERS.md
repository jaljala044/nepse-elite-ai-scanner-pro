# IDPAT-18 — NEPSE source dataset adapters

## Delivered
- Added strict schema adapters for OHLCV, session calendar, instrument universe, corporate actions, floorsheet, broker summaries, sector membership, sector indices and fundamentals.
- Enforces source envelope identity, evidence ID, raw SHA-256 format, timezone-aware point-in-time availability, approved rights, verified validation and finality.
- Quarantines malformed rows, invalid OHLCV and duplicate security/session observations.
- Outputs research-review eligibility only; production promotion is always false.

## Boundaries
- Adapters validate caller-supplied captured records. They do not fetch NEPSE data, scrape sites, authenticate publishers or prove source independence.
- Dataset-specific effective-date, completeness and reconciliation checks remain required downstream.
- Broker codes and transaction rows do not establish beneficial ownership or manipulation.
- Synthetic tests are contract tests, not evidence of actual NEPSE data ingestion.
