# IDPAT-15 — Multi-horizon scanner validation harness

## Delivered
- Runs existing partial IDPAT research components separately for T+2, swing, positional and investment windows.
- Minimum history thresholds are 21, 40, 60 and 120 bars respectively. These are data sufficiency thresholds, not calibrated forecast periods.
- Requires a passed 120-session history gate before evaluating horizons.
- Uses trailing history slices and a common point-in-time cutoff.
- Exposes component evidence and blocked-gate reasons without double-counting.
- Every horizon remains NO_TRADE; overall scores, probabilities and production recommendations remain unavailable.

## Limitations
- This does not integrate/calibrate the complete Wyckoff, Minervini, RS, VSA, broker, sector, liquidity and execution stack into a validated combined score.
- No order-book depth, intraday fills, circuit execution, settlement simulation or backtest is added.
- No live NEPSE data or predictive accuracy is claimed. Synthetic fixtures test the contract only.
