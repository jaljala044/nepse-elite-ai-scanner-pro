# Six-Scanner Feature Integration — Step 1

## What is connected
`backend/app/scanner_strategy_integration.py` adapts existing `feature_pipeline.build_feature_snapshot` outputs into the feature-evidence schema consumed by `scanner_strategy_lab.evaluate_strategy`.

Supported one-to-one source mappings:
- Minervini trend → `trend`
- Relative strength → `relative_strength`
- Wyckoff events → `wyckoff`
- VSA/volume → `volume`
- SMC → `smc` (only if upstream eventually marks a numeric score observed; current experimental-only output is rejected)
- Liquidity/tradability → `liquidity`
- Sector strength → `sector`
- Broker footprint → `broker_flow`

## Evidence admission
Each feature needs an upstream `status=observed`, numeric score in [0,100], and separate trusted manifest evidence with `status=verified`, source ID, evidence ID and timezone-aware availability no later than the decision cutoff. Future, stale-format, unverified, missing or invalid values are omitted and reported as missing. The adapter never calculates scores.

## Deliberately not fabricated
The current repository does not provide independently scored, fully evidenced outputs for IDPAT overall price-volume, accumulation/distribution, hidden levels, broker persistence, distribution risk, BOS/CHoCH subcomponents, valuation, earnings quality or balance sheet. These remain missing. Partial IDPAT price-volume scores and experimental SMC heuristics are not relabeled as verified strategy scores. Wyckoff is not copied into accumulation/distribution and SMC is not copied into market structure, avoiding correlated-feature double counting.

## Integration boundary
This adapter returns strategy-specific evidence dictionaries; callers pass each dictionary to `evaluate_strategy` with the same symbol, horizon, decision time and verified session count. The evidence manifest must be assembled server-side from trusted source/evidence records. Client-provided provenance is not trusted. This is research-only and does not create BUY/SELL orders, probabilities, trade levels or production promotion.
