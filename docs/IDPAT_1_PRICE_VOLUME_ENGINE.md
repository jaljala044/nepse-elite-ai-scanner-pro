# IDPAT-1 — Price/Volume & Candlestick Context Engine

- Version: `idpat-1.0.0`
- Branch: `idpat-1-price-volume-engine`
- Module: `backend/app/idpat_price_volume.py`
- Tests: `backend/tests/test_idpat_price_volume.py`
- Scope: first implementation slice of IDPAT; research-only and point-in-time.

## Implemented
- OHLCV evidence admission: verified status, source ID, coverage threshold (default 95%), timezone-aware availability timestamp and cutoff checks.
- Bar validation: positive OHLC prices, non-negative volume, valid OHLC geometry, unique ascending dates and no future bars.
- Prior-20-session volume ratio and close position in the prior-20-session range.
- Contextual bullish/bearish rejection candle checks.
- Close-and-volume breakout and breakdown confirmation; failed-breakout warning when price penetrates the prior high but closes back below it.
- Explicit partial component scores; no full IDPAT score.

## Input contract
```python
{
  "symbol": "SYMBOL",
  "price_volume": {
    "status": "verified",
    "source_id": "immutable-source-record-id",
    "coverage": "1.0",
    "available_at": "2026-11-26T15:00:00+05:45",
    "bars": [
      {"date":"2026-11-01","open":"100","high":"103",
       "low":"99","close":"102","volume":"12000"}
    ]
  }
}
```
At least 21 daily bars are required. Bars must be ordered oldest to newest. The caller is responsible for establishing source verification and completeness; the module validates the supplied assertion and data shape but does not independently fetch or attest the source.

## Interpretation and safety boundaries
- OHLCV-derived zones and patterns are inferred chart observations, not verified order-book liquidity or proof of smart-money activity.
- Broker flow, ownership, operator intent, order-book depth, opening-range/OPR/OPS and intraday patterns are outside this first slice.
- A confirmed breakout flag is a descriptive condition, not an entry instruction. It does not establish acceptance/retest, market alignment, liquidity or executable fills.
- The response always remains `NO_TRADE` in this phase. `overall_score` and probabilities remain null.
- No backtest or performance claim is made.

## Next implementation slices
1. IDPAT-2: accumulation/distribution, shakeout and buying/selling climax.
2. IDPAT-3: liquidity sweeps, structure shifts, breakout retests, SOS/SOR and multi-timeframe confluence.
3. IDPAT-4: risk sizing, reward/risk plans, replay/backtesting and validation.
4. Integrate only after upstream data manifests and execution constraints are wired and tested.
