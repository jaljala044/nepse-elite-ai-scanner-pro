# Portfolio Risk Dashboard and Walk-Forward Diagnostics

## Step 20 — Portfolio risk dashboard
`build_portfolio_risk_dashboard(comparison)` creates a separate exposure report for each strategy/horizon portfolio. It reports peak gross exposure, peak concurrent symbol and sector concentration, open stop-risk budget, accepted/closed/open counts, and sector coverage. Concentration thresholds are configurable (defaults: 25% single symbol and 40% sector of initial equity).

Independent strategy/horizon portfolios are **not summed** into a synthetic combined live book. A true combined portfolio requires a single shared capital allocator and deduplication policy.

Accepted entries and closed outcomes are reconciled by unique source-signal ID. All dates are canonical ISO dates; actual exits terminate closed positions and scheduled exits bound still-open positions. Duplicate/orphan closes, malformed or reversed intervals, missing open-position exit dates, and reported open-count mismatches fail closed.

The report is an exposure diagnostic only. Open positions remain valued at entry cost; it is not mark-to-market portfolio risk or a complete backtest. Missing sector remains UNKNOWN and lowers coverage.

## Step 21 — Walk-forward outcome diagnostics
`diagnose_walk_forward_folds(fold_results)` accepts fold-level metrics and considers only `out_of_sample` rows. Default gates require at least 3 complete folds, 30 closed trades in total, positive net expectancy, profit factor >= 1 and max drawdown <= 25% in every complete fold. Every complete fold must pass; this deliberately conservative all-fold rule blocks selection after a weak fold. Winners are selected independently by horizon using median fold expectancy, fold consistency and sample size.

Fold IDs are checked for duplicates, but the module cannot prove chronological non-overlap or that folds were untouched. The upstream research pipeline must enforce expanding chronology and embargo. Missing metrics never become neutral scores.

## Status and limits
Research only; no live NEPSE history or empirically validated scanner performance is included. No circuit queues, partial fills, market impact, or guaranteed stop fills are modeled. No strategy winner is asserted without qualifying real out-of-sample fold records.
