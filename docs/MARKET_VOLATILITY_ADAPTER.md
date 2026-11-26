# Verified NEPSE index volatility adapter

## Purpose
Provides the 15% volatility input to market health as an inverse historical
realized-volatility rank. It measures relative stability, not direction or
expected return.

## Admission contract
- Requires 271 exact sessions from an independently verified ordered NEPSE
  exchange calendar.
- Admits only verified/final \`index_ohlcv\` rows for NEPSE with valid OHLC,
  source ID, SHA-256 payload digest and timezone-aware \`available_at\` no later
  than decision time.
- All rows must share one source ID. Duplicate, missing, provisional,
  malformed or future-available rows withhold the score.
- No forward-fill, interpolation, session substitution or source splicing.

## Calculation
- Calculate 270 close-to-close log returns from 271 exact closes.
- Calculate 251 rolling 20-session sample standard deviations, annualized by
  \`sqrt(252)\` and expressed as a percentage.
- Rank the latest rolling volatility against the preceding 250 observations.
  Mid-rank ties are used; score = 100 minus empirical percentile rank.
- Lower relative volatility therefore produces a higher stability score.
  This is not a probability or a directional bullish/bearish signal.

## Warnings and limitations
Flags top-decile volatility and bottom-decile compression. Compression may
precede volatility expansion and is not automatically bullish. Annualization
assumes 252 trading sessions per year. The adapter is standalone and is not
yet wired to live verified NEPSE index feeds, API or market-health classifier.
Synthetic tests validate calculations only; no live volatility score is
claimed.
