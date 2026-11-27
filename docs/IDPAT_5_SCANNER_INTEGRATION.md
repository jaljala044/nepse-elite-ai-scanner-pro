# IDPAT-5 — Scanner Integration & Evidence Gates

Version: idpat-5.0.0  
Branch: idpat-5-scanner-integration

## Implemented
- Added a separate POST /v1/research/idpat endpoint.
- Orchestrates IDPAT-1 price/volume, IDPAT-2 accumulation/distribution, IDPAT-3 structure and IDPAT-4 risk planning.
- Does not change the existing /v1/scan path, ranking, candidate universe or production recommendations.
- Requires explicit point-in-time gate evidence for market, sector, broker, liquidity, execution, corporate actions and source quality.
- Each gate must be status=verified, have a non-empty evidence_id and a timezone-aware available_at no later than the decision timestamp.
- Missing, unverified, malformed or late evidence blocks risk planning.
- Risk plan requires explicit levels/capital and can only return REVIEW_ONLY or NO_TRADE.
- Produces a deterministic SHA-256 research snapshot identity.

## Persistence boundary
- The endpoint returns immutable_snapshot=true but persisted=false. It does not write the snapshot to a durable ledger.
- The existing P4.42 append-only signal lifecycle is on a separate P4.41 feature branch and is not merged into this IDPAT dependency chain. Reuse/integration should happen after that branch is reviewed and its storage/API contract is ported or merged deliberately; do not create a competing signal ledger.
- This endpoint does not generate BUY/SELL/HOLD decisions. The final action remains NO_TRADE.

## Operational status
- No live NEPSE data ingestion is connected to this endpoint.
- The caller supplies all stage data and gate attestations; the API validates structure/timestamps but does not independently authenticate those upstream sources.
- Current market-health readiness still reports missing canonical market, sector and source evidence.
- Synthetic tests validate the adapter contract only; they are not a strategy backtest or production acceptance.
