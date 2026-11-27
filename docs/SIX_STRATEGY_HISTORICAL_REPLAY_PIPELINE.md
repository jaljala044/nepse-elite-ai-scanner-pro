# Steps 32–33 — six-strategy historical candidate and replay bridge

Step 32 evaluates each complete point-in-time feature snapshot against all six strategy definitions and four horizons using independently supplied, source-backed feature evidence. Missing evidence remains missing; no indicator is converted into an invented score. Each strategy/horizon evaluation is recorded, including withheld cases.

A strategy ranking alone never becomes a replay trade. A candidate requires an independent verified trade plan with entry, stop, target, >=2 net reward/risk, liquidity quantity cap, decision timestamp matching the snapshot, feature fingerprint match and explicit train/validation/out-of-sample partition.

Step 33 passes only qualified signals to the existing common-input six-strategy replay coordinator. Existing backtest handles next-session-open entries, cost/slippage assumptions, stop/target/time exits and settlement-lock scenarios. OOS remains separate and is not used for feature tuning.

This bridge does not derive Wyckoff, SMC, broker or fundamental evidence. It does not fetch live NEPSE data or produce recommendations/probabilities. Results are research-only; execution simplifications and historical data coverage remain material limitations.
