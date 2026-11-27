# Strategy evidence adapters and trade-level audit

## Step 34 — Strategy-specific evidence adapters
The adapter maps only the canonical evidence keys required by each of the six strategy definitions. Every accepted feature must be explicitly marked verified and carry source ID, evidence ID, a timezone-aware availability timestamp no later than the decision cutoff, and a finite 0–100 score. Missing, invalid and future-dated evidence remains withheld. No cross-strategy substitution, imputation or synthetic confirmation is performed.

The output is an input adapter, not a strategy signal. Existing strategy scoring, evidence-cluster de-duplication, minimum history and separate trade-plan/execution gates remain authoritative.

## Step 35 — Trade-level audit
The audit joins point-in-time signals to replay outcomes by stable signal ID within an explicit data partition. It reports closed trades, target/stop/time exits, settlement-pending exits, replay rejects and unmatched signals separately. Unmatched records remain unresolved rather than being labelled losses. Per-run target/stop hit rates are descriptive replay statistics only.

## Safety and current limits
Research only; no live orders, live NEPSE dataset, calibrated probability or performance claim. Entry/exit hit rates inherit the replay's next-session-open, stop-first, cost/slippage and settlement assumptions. Circuit queues, partial fills, market impact and full portfolio mark-to-market remain separate limitations. Final selection must use the untouched out-of-sample partition and identical inputs/costs across strategies.
