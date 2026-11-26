# Minervini trend and cross-sectional relative-strength engines

## Minervini trend template
`minervini_trend_template(rows)` consumes already Stage-1 validated, point-in-time OHLCV rows. It requires 252 distinct session dates to assess a full 52-week high context. It reports seven transparent checks: close above 50/150/200 DMA; 50 > 150 > 200 DMA; rising 200 DMA versus 20 sessions earlier; close within 25% of the 52-week high; and higher high plus higher low versus the preceding 20-session window.

The score is the percentage of those seven checks passed. It is a trend-template score, not a BUY signal. Duplicate dates, invalid/non-positive prices and malformed OHLC are rejected. Missing history returns a null score with an explicit reason. No calendar-day interpolation, synthetic rows or historical price splicing is performed.

## Relative strength
`relative_strength_universe(securities, benchmark_rows)` aligns each stock to the benchmark by exact session date and calculates 5/21/63/126-session returns. RS is stock return minus benchmark return in percentage points. The weighted RS is 20% 1W, 30% 1M, 30% 3M and 20% 6M.

The 0–100 component score is the average-tie percentile rank within the supplied eligible equity universe, not an arbitrary transformation and not a probability. If any required horizon lacks common sessions, the security is excluded with an explicit reason. Missing benchmark sessions are never filled. The benchmark series must be independently identified and validated by the caller.

## Integration boundary
These functions are deliberately standalone until the repository's canonical benchmark/index record schema and validated security universe are confirmed. Do not silently treat a ticker row as NEPSE index data. Wire them into the feature pipeline only after that schema is explicit and source lineage/availability metadata are preserved.
