# Part 5 — validation acceptance register (2026-11-28)
Research only. No canonical admission, training, production signals or orders authorized.
| Task | Status | Evidence / next acceptance |
|---|---|---|
| 5.01 | Started | historical_segment_eligibility.py; require reviewed canonical rows, explicit session and lifecycle evidence |
| 5.02 | Started | point_in_time.py; require per-decision feature availability and label maturity |
| 5.03 | Completed implementation only | execution_costs.py; scenario assumptions |
| 5.04 | Open | authenticate effective-dated fee/tax schedules and independent hand calculations |
| 5.05 | Started | historical_trade_simulation.py; validate settlement, price bands, liquidity and cash availability |
| 5.06 | Open | net equity curve, drawdown, risk-adjusted metrics and aligned benchmark |
| 5.07 | Started | walk_forward_report.py exists; require purged label horizons and fold-local fitting |
| 5.08 | Open | locked untouched chronological holdout |
| 5.09 | Started | test future append invariance, feature timestamps and label maturity |
| 5.10 | Started | effective-dated universe including delisted/suspended securities |
| 5.11 | Open | parameter sensitivity, cost/liquidity stress and regime stability |
| 5.12 | Open | immutable paper journal; hypothetical fills clearly labelled |
| 5.13 | Open | net win rate, drawdown, sample count and uncertainty |
| 5.14 | Blocked | independent review after evidence and exact-head CI |
| 5.15 | Blocked | explicit production approval after all applicable gates |
## Initial code audit
Historical segment evaluator checks row availability against one cutoff, not each historical decision; caller-supplied no-trade and lifecycle assertions need authoritative evidence. Point-in-time snapshot can be empty and still satisfy its timestamp predicate; not a training admission decision. Walk-forward report sorts observation dates but does not establish when training labels matured or whether probabilities were fitted without test data. These are integration gaps, not proof of historical leakage.
## Acceptance sequence
1. Verify reviewed manifest, dataset hashes, instrument identities, session evidence and source rights. Keep unresolved repeats/conflicts quarantined.
2. For each fold enforce feature availability <= decision time and training label availability <= fit cutoff < test decision time; purge overlapping label intervals. Freeze parameters before untouched holdout.
3. Independently validate dated costs and settlement constraints; daily OHLC cannot establish actual fills or queue priority. No shorting or fabricated candles.
4. Report net returns, drawdown, exposure, turnover, trade count, benchmark and uncertainty; no metric when eligible sample absent.
5. Require exact-head CI and independent review; no production promotion from this register.
