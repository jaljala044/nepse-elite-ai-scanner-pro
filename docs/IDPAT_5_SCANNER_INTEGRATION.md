# IDPAT-5 — Scanner Integration & Evidence Gates

Version: idpat-5.0.0  
Branch: idpat-5-scanner-integration

## Implemented
- Added a separate POST /v1/research/idpat endpoint.
- Orchestrates IDPAT-1 price/volume, IDPAT-2 accumulation/distribution, IDPAT-3 structure and IDPAT-4 risk planning.
- Does not change the existing /v1/scan path, ranking, candidate universe or production recommendations.
- Requires explicit point-in-time gate evidence for market, sector, broker, liquidity, execution, corporate actions and source quality.
- Each gate must be status=verified, have non-empty source_id and evidence_id, and a timezone-aware available_at no later than the decision timestamp.
- Missing, unverified, malformed or late evidence blocks risk planning.
- Risk plan requires explicit levels/capital and can only return REVIEW_ONLY or NO_TRADE.
- Produces a deterministic SHA-256 research snapshot identity.
- Optional persist_signal=true freezes a NO TRADE record for the requested horizon and appends it to the existing P4.42 DuckDB signal store. Identical retries are idempotent.

## Persistence boundary
- Persistence is opt-in and requires all seven verified gate attestations. The stored record is explicitly research_only_not_execution and action=NO TRADE.
- Reuses existing signal_tracking.py and signal_store.py; no competing signal ledger is introduced.
- The endpoint does not store BUY/SELL/HOLD decisions or claim fills/outcomes.
- This endpoint does not generate BUY/SELL/HOLD decisions. The final action remains NO_TRADE.

## Operational status
- No live NEPSE data ingestion is connected to this endpoint.
- The caller supplies all stage data and gate attestations; the API validates structure/timestamps but does not independently authenticate those upstream sources.
- Current market-health readiness still reports missing canonical market, sector and source evidence.
- Synthetic tests validate the adapter contract only; they are not a strategy backtest or production acceptance.
## Integration dependency
- This branch depends on IDPAT-4 and the tested historical-segment eligibility implementation in PR #177. Preserve both dependencies in the PR base chain so the full backend suite runs against the matching implementation and evidence-aware tests.
