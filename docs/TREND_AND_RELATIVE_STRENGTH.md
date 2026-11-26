# Minervini trend and cross-sectional relative-strength engines

## Minervini trend template
`minervini_trend_template(rows)` consumes already Stage-1 validated, point-in-time OHLCV rows. It requires 252 distinct session dates to assess a full 52-week high context. It reports seven transparent checks: close above 50/150/200 DMA; 50 > 150 > 200 DMA; rising 200 DMA versus 20 sessions earlier; close within 25% of the 52-week high; and higher high plus higher low versus the preceding 20-session window.

The score is the percentage of those seven checks passed. It is a trend-template score, not a BUY signal. Duplicate dates, invalid/non-positive prices and malformed OHLC are rejected. Missing history returns a null score with an explicit reason. No calendar-day interpolation, synthetic rows or historical price splicing is performed.

## Relative strength
`relative_strength_universe(securities, benchmark_rows)` aligns each stock to the benchmark by exact session date and calculates 5/21/63/126-session returns. RS is stock return minus benchmark return in percentage points. The weighted RS is 20% 1W, 30% 1M, 30% 3M and 20% 6M.

The 0–100 component score is the average-tie percentile rank within the supplied eligible equity universe, not an arbitrary transformation and not a probability. All securities share the latest verified final NEPSE benchmark session. Every exact benchmark session in each 1W/1M/3M/6M window must exist for the stock; a missing intermediate date or stale endpoint excludes the symbol. Missing benchmark sessions are never filled. The feature pipeline accepts only `index_ohlcv` rows with `index_code=NEPSE`, `source_validation_status=verified`, `finality_status=final`, a nonblank `source_id` and a 64-character source payload SHA-256. Provisional/unverified index rows are counted but withheld. This is an ingestion contract, not a claim that a real benchmark dataset has already passed the project-wide source/calendar/corporate-action gates.

## Integration boundary
The feature pipeline now wires this engine to the explicit `index_ohlcv` record contract above. If no verified final NEPSE index rows are supplied, the RS result and 15% component remain null. The current YONEPSE archive is only a third-party mirror with documented TLS/provenance limitations; SocrateAI index files also have known duplicate and OHLC anomalies. Neither is auto-promoted by this integration. The input producer must set the verification status only after independent row, session, finality and provenance checks pass.
