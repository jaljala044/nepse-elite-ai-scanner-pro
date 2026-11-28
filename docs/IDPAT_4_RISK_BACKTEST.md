# IDPAT-4 — Risk Management, Reward/Risk & Historical Replay

Version: idpat-4.0.0  
Branch: idpat-4-risk-backtest

## Risk sizing
- Long-only whole-share sizing from explicit entry, structural stop, capital and risk budget.
- Default risk budget 1%; configurable hard ceiling defaults to 2%.
- Position cap defaults to 20% of capital.
- Optional average-daily-turnover participation cap defaults to 5%.
- T1 is mandatory; net T1 reward/risk must meet configurable minimum (default 2:1).
- T1/T2/T3 net reward/risk includes caller-supplied round-trip cost and per-side slippage estimates.
- Eligible output is REVIEW_ONLY, never an order or BUY recommendation. Rejections are NO_TRADE.

## Historical replay
- Consumes explicit, externally generated historical signals and verified OHLCV; it never creates signals.
- Simulated entry is next available session open.
- Exit is stop, target or horizon close. If stop and target both occur in one OHLC bar, stop is assumed first.
- Horizons: T+2 up to 5 sessions, swing 20, positional 126, investment 504.
- Reports sample size, win rate, average gain/loss, profit factor, expectancy, compounded return and maximum drawdown.
- Requires full horizon history; right-censored trades are rejected.
- Chronological walk-forward split helper; no random shuffling.

## Limitations
- Cost/slippage are explicit caller inputs; zero means unmodelled, not free execution.
- No queue position, partial fills, circuit limits, suspensions, settlement, market impact, actual NEPSE brokerage/tax schedule or corporate-action adjustment in this first replay layer.
- No verified historical signal archive, live feed, production calibration or actual performance claim is included.
- No probability or forward performance estimate is produced.
