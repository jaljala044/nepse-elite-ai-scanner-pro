# IDPAT-3 — Liquidity & Market Structure Intelligence

- Version: `idpat-3.0.0`
- Branch: `idpat-3-liquidity-market-structure`
- Module: `backend/app/idpat_market_structure.py`
- Tests: `backend/tests/test_idpat_market_structure.py`

## Reused engines
IDPAT-3 is an adapter over existing project modules, not a duplicate technical-analysis engine:

- `market_structure.detect_structure`: causal pivots, BOS/CHoCH, buy-/sell-side sweep candidates, equal highs/lows, FVG/order-block zones, retests and invalidations.
- `wyckoff_event_features`: SOS/SOW, LPS/LPSY, spring/upthrust, Jump Across Creek and Backup to Creek candidates.
- `evaluate_multitimeframe`: daily/weekly/monthly structure using a verified exchange-session calendar and conservative exclusion of incomplete higher-timeframe periods.

## Evidence admission
- Reuses IDPAT-1 verified OHLCV admission: verified source, source ID, >=95% coverage by default, timezone-aware availability timestamp, ascending unique bars and point-in-time cutoff.
- Optional multi-timeframe analysis requires a separate verified session-calendar object with source ID, coverage, availability timestamp and unique ascending sessions. It is withheld if absent, unverified, late, incomplete in coverage or contains future sessions.
- Existing engine validation is retained. No future pivot is exposed before its right-hand confirmation bars are available.

## Output
- Inferred buy-side/sell-side liquidity candidates from equal highs/lows and confirmed swing sweeps.
- BOS/CHoCH events, inferred chart zones and zone lifecycle events.
- Separate Wyckoff campaign event references.
- Daily structure bias and optional multi-timeframe alignment.
- No IDPAT overall score, probability, BUY/SELL, trade levels or backtest metrics.

## Interpretation boundary
- OHLCV chart levels are inferred, not verified resting orders.
- A sweep is a mechanical wick/reclaim or wick/rejection pattern at a confirmed swing; it does not prove stop hunting or operator intent.
- Wyckoff labels remain event candidates, not confirmed campaigns.
- Existing event engines are referenced without adding their counts again to a new score.
- No broker footprint, order book, market breadth, sector, liquidity execution or reward/risk evidence is synthesized.

## Next
IDPAT-4 will add risk sizing and reward/risk gates, signal replay, walk-forward evaluation and calibration. Trade actions must remain disabled until required market, sector, broker, liquidity, execution and data-quality gates are connected and independently validated.
