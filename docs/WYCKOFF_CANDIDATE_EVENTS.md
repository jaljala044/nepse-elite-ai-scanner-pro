# Wyckoff candidate event features

## Scope and safety

`backend/app/wyckoff_features.py` derives deterministic, descriptive candidate
events from point-in-time OHLCV rows. It is not a standalone trading signal,
does not infer operator intent, and does not assert a confirmed Wyckoff phase.
The feature pipeline applies the Stage-1 availability filter before calling it.

A minimum of 41 valid sessions is required. Missing required OHLCV returns
`insufficient_evidence` with a null score. Duplicate sessions, invalid dates,
non-finite values, impossible OHLC relationships, and non-positive prices are
rejected. Each event is evaluated using only earlier sessions and the current
session; no future bar is used to create or confirm an event.

## Explicit rules

- Spring: current low sweeps the prior 20-session low, close reclaims that
  level, relative volume is at least 1.2x, and close-location value (CLV) is
  at least 0.60.
- Upthrust: current high sweeps the prior 20-session high, close rejects below
  that level, relative volume is at least 1.2x, and CLV is at most 0.40.
- SOS / Jump Across Creek: close exceeds the prior 20-session high, relative
  volume is at least 1.5x, and CLV is at least 0.70.
- SOW: close falls below the prior 20-session low, relative volume is at least
  1.5x, and CLV is at most 0.30.
- LPS / Backup to Creek: within 10 sessions after a detected SOS, price retests
  the breakout level, closes at/above it, and relative volume is at most 1.0x.
- LPSY: within 10 sessions after a detected SOW, price retests the breakdown
  level, closes at/below it, and relative volume is at most 1.0x.

Relative volume uses the average volume of the prior 20 sessions, excluding
the current bar. CLV is (close - low) / (high - low). All levels are calculated
from bars preceding the event.

## Regime candidates

The last 40 sessions are used to describe the range and close position.
Range width <=25%, close position >=60%, and up-candle volume >1.10x
down-candle volume yields `accumulation_candidate`; the corresponding lower
range/close and down-volume dominance yields `distribution_candidate`.
Range-bound closes in the upper/lower 40% without volume dominance are labelled
`re_accumulation_candidate` / `re_distribution_candidate`. These are
heuristic candidate labels only; they do not establish a Wyckoff campaign.

## Score and limitations

The 0-100 score is a bounded evidence balance: 50 plus 10 times the difference
between bullish and bearish candidate-event counts, clipped to [0,100].
It is not a probability, calibrated forecast, composite scanner score, or
BUY/SELL recommendation. Event counts can include multiple related labels
for one breakout (SOS and Jump Across Creek; LPS and Backup to Creek).

Events remain candidates until a later as-of snapshot provides follow-through.
The current detector does not use broker footprint, sector context, market
regime, corporate actions, or higher-timeframe confirmation. It must not bypass
the scoring engine's coverage gate or Stage-1 quality gate.

## Tests

Synthetic unit fixtures test insufficient history, Spring, Upthrust, SOS/JAC,
LPS/Backup, SOW/LPSY, duplicate dates, invalid OHLC and pipeline integration.
Synthetic tests validate code behavior only; they are not historical NEPSE
performance evidence or live stock signals.
