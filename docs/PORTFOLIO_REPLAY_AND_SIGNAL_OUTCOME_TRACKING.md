# Portfolio Replay and Signal Outcome Tracking

## Step 18 — Portfolio-level replay
`replay_portfolio` consumes trade records from the point-in-time single-trade replay. It models concurrent positions, cash-only capital, maximum open positions, per-position allocation, total exposure, risk budget, settlement-gap stress and a mandatory per-trade liquidity quantity cap. Existing single-trade net returns already include the round-trip costs/slippage configured in that replay; portfolio replay does not deduct them a second time.

Positions are exited before new entries on the same session. Candidate entry order is deterministic: session, descending supplied strategy score, then strategy/horizon/symbol/signal ID. The engine rejects missing/duplicate signal IDs, invalid stop/entry/exit structures and missing liquidity capacity. It does not infer ADV or depth.

The current portfolio drawdown is realized-only: open positions are held at entry cost. This intentionally avoids fabricated mark prices but understates true intraperiod risk. Do not treat the metric as a complete portfolio backtest.

## Step 19 — Append-only signal/outcome ledger
`generate_historical_research_signals` now emits a stable SHA-256 signal ID from symbol, strategy, horizon and decision timestamp, plus the risk engine's ADV quantity cap when available.

`build_signal_outcome_ledger` appends a SIGNAL_RECORDED event and a separate OUTCOME_ATTACHED event. It distinguishes target hit, stop hit (including settlement-delayed stop exit), time exit, not executed, settlement/horizon pending and unmatched/rejected. It summarizes win rate, net returns, profit factor and maximum favorable/adverse excursion by strategy and horizon.

Original signals are never overwritten. NO_TRADE is not labelled a false negative without a separately defined counterfactual policy. Unmatched signals remain unresolved rather than being counted as losses.

## Validation and limitations
- Portfolio replay requires externally supplied, point-in-time liquidity quantity caps; missing caps fail closed.
- Costs/slippage must be identical across strategies for fair comparison.
- Portfolio replay consumes completed single-trade outcomes; partial fills, market impact, circuit queues, order-book queue priority and intraday mark-to-market are not simulated.
- Corporate actions must be reconciled upstream.
- Signal ledger metrics are descriptive and not calibrated probabilities or validated live accuracy.
- No real NEPSE historical dataset is bundled; no performance claim or production authorization is made.
