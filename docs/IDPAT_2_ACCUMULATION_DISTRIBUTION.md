# IDPAT-2 — Accumulation, Distribution, Shakeout & Climax

- Version: `idpat-2.0.0`
- Branch: `idpat-2-accumulation-distribution`
- Module: `backend/app/idpat_accumulation_distribution.py`
- Tests: `backend/tests/test_idpat_accumulation_distribution.py`
- Depends on: IDPAT-1 evidence admission and OHLCV validation.

## Implemented observations
- Compare the latest 20 daily bars with the preceding 20 daily bars.
- Measure relative range compression and volume dry-up.
- Compare average volume on up-closing sessions with down-closing sessions.
- Flag possible shakeout/reclaim and upthrust/rejection bars using prior-20-session extremes, volume expansion and close location.
- Flag possible buying/selling climax candidates only when both volume and spread expand materially and the close location supports the event.
- Produce separate partial accumulation and distribution evidence scores and a descriptive hypothesis.

## Evidence and safeguards
- Requires the IDPAT-1 verified OHLCV input contract, >=95% coverage by default, timezone-aware availability timestamp and point-in-time cutoff.
- Requires at least 40 valid, ascending, unique daily bars.
- All thresholds are transparent heuristics, not universal Wyckoff laws; future validation may calibrate them by NEPSE sector and liquidity cohort.
- A climax is not a reversal signal without follow-through; a shakeout/upthrust is not proof of manipulation, stop hunting or operator intent.
- OHLCV alone cannot establish smart-money ownership, broker intent or actual institutional orders.
- No overall score, probabilities, BUY/SELL, entry, stop, target or backtest metrics are emitted. Output remains NO_TRADE.

## Next
- IDPAT-3: liquidity sweeps, BOS/CHoCH, retest/acceptance, SOS/SOW/LPS/LPSY and multi-timeframe context.
- IDPAT-4: risk sizing, reward/risk, replay/backtest and calibration against verified point-in-time NEPSE data.
