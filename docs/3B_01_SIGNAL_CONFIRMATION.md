# 3B.01 — Signal confirmation engine

## Rule set

A bullish confirmation requires all of:
1. Latest close above the prior 20-session high (latest candle excluded).
2. Latest close above SMA20 and SMA50.
3. SMA20 above SMA50.
4. Latest volume at least 1.5 times the prior 20-session average.
5. Latest close in the upper 25% of its candle range.

A bearish warning is the symmetric downside pattern: close below the prior
20-session low and both moving averages, SMA20 below SMA50, volume expansion,
and a close in the lower 25% of the candle. It is not a short-sale instruction.

## Fail-closed behavior

The caller must pass `eligible=True` only after the server-owned review gate
has certified row identity, lifecycle, session, provenance, corporate-action
and point-in-time availability. The default is false. Invalid or insufficient
input returns UNKNOWN.

## Output classes

- `bullish_confirmation`: all bullish rules passed.
- `bearish_warning`: all bearish rules passed.
- `no_confirmation`: eligible data, neither full rule set passed.
- `UNKNOWN`: eligibility or structural validation unavailable.
- `insufficient_data`: fewer than 55 observations.

## Limitations

Daily OHLCV only. No intraday confirmation, order book, verified broker flow,
sector/market regime, liquidity, slippage, transaction costs or out-of-sample
backtest. Thresholds are research defaults, not calibrated probabilities.
No BUY/SELL/HOLD/NO TRADE, entry, stop, target, sizing, alert or order is emitted.

## Tests

From `backend/`: `python -m unittest tests.test_signal_confirmation`
