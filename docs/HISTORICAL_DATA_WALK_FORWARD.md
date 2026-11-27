# Historical Data Readiness and Walk-Forward Validation — Steps 6 and 7

## Step 6 — Point-in-time historical panel
\`app.nepse_historical_panel.assemble_historical_panel\` consumes already-admitted OHLCV, trading calendar, effective-dated instrument universe and corporate-action reports. It checks source-report status and availability by decision cutoff, builds a common open-session calendar, verifies complete per-symbol histories and requires historical universe membership. Incomplete symbols are excluded, not silently forward-filled.

Corporate actions effective inside the sample are not adjusted automatically. Affected securities are excluded pending a verified, consistent adjustment/reconciliation ledger. This prevents split/bonus/rights discontinuities from contaminating backtest returns. Delisting and historical universe completeness must be represented in the supplied universe records.

## Step 7 — Expanding walk-forward folds
\`app.nepse_walk_forward.build_walk_forward_folds\` creates chronological expanding training windows, followed by validation and forward out-of-sample blocks. It inserts an embargo between partitions equal to 120 sessions by default, matching the longest configured investment outcome horizon. The same indices and dates must be used by all six strategies and all four horizons.

The final out-of-sample block must remain untouched during feature, threshold and strategy selection. Repeated walk-forward folds support robustness analysis but do not replace a final holdout when many design choices are tested.

## Status and limitations
- These are data admission and partition-planning modules, not a live data connector.
- No NEPSE historical prices have been fetched or included; no accuracy or returns are claimed.
- The assembler requires source validation reports from \`nepse_official_adapters\`; it does not authenticate publishers.
- Corporate-action price/volume adjustment, floorsheet/broker/sector reconciliation, delisted-symbol recovery, circuit/partial-fill execution and portfolio concurrency remain required before a defensible full historical performance study.
- Research-only; production remains disabled.
