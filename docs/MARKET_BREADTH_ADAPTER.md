# Verified market breadth adapter

## Purpose
Produces the 25% market-breadth input for market health. It reports advances,
declines, unchanged securities, advance/decline ratio, percentage above SMA50
and SMA200, and 20-session highs/lows. The score is descriptive, not predictive.

## Admission contract
- Requires a separately validated point-in-time mature-equity cohort and its
  source ID, SHA-256 digest, status and as-of session.
- Requires an independently verified ascending exchange-session calendar.
- Requires 200 exact sessions per included security.
- Admits only `record_type=ohlcv`, verified, final rows with valid OHLC,
  source ID, SHA-256 digest and timezone-aware `available_at` no later than
  decision time.
- Duplicate symbol/session records fail. Missing/provisional/future rows
  reduce coverage; no forward-fill, interpolation or substitution.
- At least 80% of the supplied mature cohort must have complete exact history.

## Score
- 30% advance/decline balance
- 25% of mature cohort above SMA50
- 25% of mature cohort above SMA200
- 20% 20-session high/low balance

Each input is expressed on a 0-100 scale. The output score is normalized over
these fixed weights only when the complete coverage gate passes. A no-advancer
and no-decliner day receives a neutral descriptive balance of 50, not a
probability. New highs/lows refer to 20 sessions, not 52 weeks.

## Data limitations
This is a standalone adapter. It is not yet wired to the API or market-health
classifier. The current OHLCV evidence pipeline marks parsed records
eligible-for-review, not automatically verified; only an upstream validator
may produce the strict verified/final fields accepted here. Synthetic tests
validate logic, not live market data. No live breadth score is claimed.
