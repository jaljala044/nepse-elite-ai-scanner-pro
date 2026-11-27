# Steps 24–25 — Automated Feature Ablation and Experiment Registry

## Step 24 — Matched OOS ablation matrix
`run_feature_ablation_matrix` runs every registered strategy and horizon over caller-supplied chronological OOS folds. For each strategy/horizon/fold it runs a full-feature baseline and one ablation per evidence cluster defined in the strategy catalogue. It rejects any run whose universe, panel, cost model, execution model or methodology version differs from the fold or baseline. Empty or malformed trade outcomes remain rejected/insufficient; no missing metric is imputed.

The injected `run_variant` callback must rebuild the feature snapshot and signal decisions at that fold's decision cutoffs. This module orchestrates the experiment; it does not invent a feature engine, fetch market data or certify the callback.

## Step 25 — Append-only experiment registry
Each baseline and ablation variant emits a registration event and a completion event. Events include strategy, horizon, fold, partition, excluded feature groups, assumption IDs, output SHA-256 and timestamp. The registry uses a deterministic hash chain and rejects changed, reordered, duplicate or broken events. Persist the returned full event list in versioned, access-controlled storage; the in-process module alone is not durable.

## Guardrails
- Only `out_of_sample` folds are accepted by this matrix.
- Baseline and ablation must share identical universe/panel/cost/execution/methodology fingerprints.
- Ablation is not causal proof and is not a future performance probability.
- No live NEPSE data, real strategy winner, or production recommendation is claimed.
- The experiment timestamp is caller-supplied and is not independently trusted or externally timestamped.
