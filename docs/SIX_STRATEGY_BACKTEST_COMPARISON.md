# Six-Strategy Backtesting and Comparison — Steps 4 and 5

## Step 4: historical replay
The app.scanner_backtest.replay_strategy_horizon function replays one strategy and horizon using explicitly partitioned signals and verified daily OHLCV:
- Signal evidence and stop/target must be verified and available by the decision timestamp.
- Entry occurs at the next available session open after the signal date.
- Horizon windows: T+2 = 5 sessions, swing = 20, positional = 60, investment = 120.
- Intraday stop/target collision uses conservative stop-first handling.
- Costs and slippage are explicit round-trip percentages.
- A configurable sellability delay models settlement lock. A stop triggered while locked queues exit until the first permitted session open.
- Reports sample size, rejected/pending trades, win rate, average win/loss, profit factor, expectancy, drawdown, ending equity and exit reasons.

The simulator validates chronology, duplicate dates, OHLC consistency, volume and per-bar provenance. It does not yet simulate circuit queues, partial fills, impact, corporate-action adjustments or overlapping portfolio capital. One equal-notional trade per signal is used for this initial replay.

## Step 5: comparison
The app.scanner_strategy_comparison.compare_strategy_results function compares all six strategies independently for each horizon. It only accepts out_of_sample results. Default eligibility requires at least 30 closed trades, positive net expectancy, profit factor >= 1 and max drawdown <= 25%. Ranking uses expectancy, then profit factor, then lower drawdown, then sample size. A horizon has no winner when no candidate passes.

## Critical research discipline
- No historical NEPSE data is bundled or downloaded by these modules. Outputs are not performance claims.
- Train, validation and untouched out-of-sample partitions must be created chronologically by the caller; never shuffle dates.
- All strategies must receive the same symbol universe, decision dates, verified bars, fees, slippage and settlement assumptions.
- Do not select or tune on the untouched holdout repeatedly.
- Signals must be generated from data available at the decision timestamp. Future OHLCV is used only to evaluate outcomes.
- Data gaps, corporate actions, circuits, partial fills and portfolio concurrency need additional verified modelling before performance can be treated as realistic.
- Production recommendations remain disabled.
