# SMC structure and multi-timeframe features

## Scope and data boundary

`backend/app/smc_features.py` consumes Stage-1 validated OHLC bars already
filtered by the point-in-time snapshot. It does not infer institutional orders,
broker intent, order-book liquidity, or executable prices. Its labels are
mechanical chart observations/candidates and are not standalone trade signals.

A minimum of 10 valid OHLC sessions is required. Duplicate dates, invalid
timestamps/dates, non-finite/non-positive prices and impossible OHLC bars are
rejected. The current snapshot includes daily, weekly and monthly context.
Weekly/monthly OHLC is aggregated from observed daily bars, with the latest
calendar bucket excluded because it may be incomplete.

## Structure and liquidity rules

- Swing pivots use two bars on each side. A pivot is published only when the
  two right-hand bars are already available; its `confirmed_session` is the
  bar on which confirmation becomes knowable.
- BOS is a close crossing the latest confirmed swing in the direction of the
  current/neutral structure bias. CHoCH is a close crossing the opposite
  confirmed swing against the established bias.
- Buy-side liquidity sweep: current high exceeds the latest confirmed pivot
  high and current close finishes below that level.
- Sell-side liquidity sweep: current low falls below the latest confirmed
  pivot low and current close finishes above that level.
- Bullish FVG: current low exceeds the high two bars earlier. Bearish FVG:
  current high is below the low two bars earlier. A later bar whose range
  overlaps the gap marks it mitigated.
- Premium/discount uses the latest confirmed swing-high / swing-low range;
  the midpoint is equilibrium. If a valid pair is unavailable, location is
  unavailable.

## Multi-timeframe handling

Daily structure uses all bars available as-of the decision time. Weekly and
monthly bars are aggregated from daily OHLC and the latest calendar bucket
is excluded from analysis to avoid treating a potentially partial period as
closed. These are context observations; they do not override daily data
quality or create a BUY on their own.

## SMC component candidate

A transparent uncalibrated evidence balance is provided for the 5% SMC
component: 50 plus 8 times the bullish-minus-bearish daily BOS/CHoCH event
count, plus 5 times the sell-side-minus-buy-side sweep count, plus 2 times
the bullish-minus-bearish open-FVG count, clipped to 0..100. Counts and formula
are returned for audit. This is neither a probability nor a validated
predictive score; it must be assessed in walk-forward research before any
production recommendation.

The feature pipeline exposes `component_candidates` for V3 scoring. Wyckoff,
trend, volume and SMC candidates are populated only when their feature status
is observed. Relative strength, broker, liquidity and sector remain null until
their evidence-backed implementations are connected. The existing scoring
engine therefore retains its coverage gate and must not impute these values.

## Validation

Synthetic unit tests cover minimum history, FVG formation and mitigation,
pivot confirmation timing, higher-timeframe partial-period exclusion, duplicate
dates, invalid OHLC and pipeline integration. They do not represent historical
NEPSE performance or live trading signals.
