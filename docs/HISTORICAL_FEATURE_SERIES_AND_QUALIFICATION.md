# Historical Feature Series and Six-Strategy Qualification

## Step 12 — As-of feature series
`build_historical_feature_series` invokes the existing `build_feature_snapshot` separately at each chronological decision timestamp. Every point receives its own canonical session calendar, universe, sector membership inputs and trusted per-symbol evidence manifest. It then uses the existing strategy adapter to produce the six strategy evidence maps.

This prevents a current/latest feature snapshot from being reused for historical dates. The point-in-time feature pipeline applies availability cutoffs before calculating features. A missing evidence manifest is recorded as withheld; no provenance is fabricated.

## Step 13 — Horizon-specific qualification
For every symbol and strategy, the orchestrator evaluates T+2, swing, positional and investment independently using the existing research scoring rules. It records score, coverage, missing/rejected features, history gate and accepted correlation clusters. Insufficient history or evidence is withheld; there are no default-neutral scores.

## Current limitations
- This creates feature snapshots and research qualifications, not BUY/SELL signals or trade plans.
- Complete IDPAT hidden-level, accumulation/distribution, broker-persistence and fundamental feature engines remain absent or unsupported in the adapter.
- SMC remains experimental-only; it is not silently counted as verified score evidence.
- A trusted evidence manifest must come from the server-side source ledger. Client-supplied attestations are not trusted.
- Actual historical OHLCV, index, sector and broker source coverage remains a prerequisite for meaningful out-of-sample performance testing.
- No live data or performance metrics are claimed; production remains disabled.
