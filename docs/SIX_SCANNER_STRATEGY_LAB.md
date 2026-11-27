# Six-Scanner Strategy Lab — Architecture v1

## Objective
Run six independent strategy hypotheses on one shared NEPSE data and risk platform. Compare them fairly; do not assume the hybrid/master strategy wins.

## Strategy engines
1. Trend & Momentum Elite — Minervini trend template, relative strength, Wyckoff, VSA/volume, SMC confirmation, sector and tradability.
2. IDPAT Smart Money — price/volume, accumulation/distribution, hidden liquidity levels, Wyckoff, broker flow and confirmation.
3. Broker Footprint Intelligence — broker net flow/persistence, price confirmation, distribution-risk checks, sector and tradability. Broker codes do not prove beneficial ownership or intent.
4. SMC / ICT Liquidity — market structure, BOS/CHoCH, sweeps, equal highs/lows, order blocks, FVG and premium/discount. ICT timing is weighted toward T+2, not positional decisions.
5. Hybrid Consensus Master — combines independent evidence clusters. Correlated Wyckoff/SOS, BOS and price/volume breakout evidence is capped to avoid double-counting.
6. Fundamental & Investment Intelligence — valuation, earnings quality, balance sheet, corporate actions, sector, relative strength, trend and liquidity.

## Shared platform
- One point-in-time canonical data/evidence layer.
- One market-health and sector/broker context layer.
- One common execution/risk service, including settlement-aware exit state.
- One backtest harness and immutable signal/outcome ledger.
- Each strategy is run separately across T+2, swing, positional and investment horizons.

## Scoring and comparison
Registered weights are design assumptions, not calibrated edge estimates. Missing, stale, future or unverified evidence is rejected and reduces coverage; it is never imputed as neutral. Correlated features with the same declared evidence cluster receive only one capped contribution. Feature-level evidence is preserved for explanation.

Compare strategies using identical symbols, point-in-time dates, costs, slippage, execution assumptions and market regimes. Use chronological train/validation/test splits, walk-forward evaluation and an untouched final holdout. Report sample size, trade frequency, win rate, average gain/loss, profit factor, expectancy, max drawdown, exposure, turnover, target/stop hit rates and execution-adjusted returns. Use ablation tests to measure feature contribution. Do not choose a winner on win rate alone.

## Settlement-aware risk
The shared exit-state helper consumes broker-confirmed sellable quantity and sellable date. If a stop is hit but shares are not sellable, it returns EXIT_PENDING (or partial exit pending) rather than pretending the stop executed. The stress-gap price is a scenario, not a forecast. No settlement calendar or legal sellability rule is hard-coded; those must come from verified broker/CDSC evidence.

## Boundaries
- This is a strategy registry and research scorer, not live data ingestion or production trading.
- A research-ranked result is not a BUY recommendation.
- No probabilities or backtest results are emitted.
- No actual strategy winner can be named until comparable, verified historical testing is complete.
