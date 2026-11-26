# Market-health API readiness

## Endpoint
\`GET /v1/market-health\` exposes the current readiness contract.

## Current response
The endpoint deliberately returns:
- \`status=insufficient_evidence\`
- \`regime=unknown\`
- \`trading_posture=preserve_capital\`
- null market-health and component scores
- zero verified coverage
- all five components listed as missing

## Why no live score is published
The integrated calculator is implemented, but the current production API storage
does not connect the required evidence-bearing records. Existing CSV ingestion
stores price values without preserving source IDs, source-payload hashes,
record finality, or point-in-time availability. The API also lacks connected
verified NEPSE index OHLCV, market-summary turnover, a canonical exchange
calendar, authoritative sector membership, and sector-price evidence manifests.

The active equity candidate manifest is sourced from a secondary provider and
is explicitly not authoritative membership evidence.

## Promotion requirements
Do not change this endpoint to publish a calculated score until:
1. Each source record is retained with provenance, finality, payload digest and
   point-in-time availability.
2. The canonical open-session calendar is independently verified.
3. The mature equity cohort and effective-dated sector membership are
   independently validated for the decision session.
4. Index, market-summary, OHLCV and sector-price records pass the adapter gates.
5. API-level integration tests prove missing or stale evidence remains UNKNOWN.

This endpoint is a readiness diagnostic, not a market forecast or trade signal.
