# Steps 58–59 — data quality dashboard and six-scanner replay admission

## Step 58 — historical data quality dashboard

Added `historical_pilot_quality_dashboard.py` to summarize evidence-backed symbol/session coverage, missing and unexpected panel rows, source conflicts, ingestion errors, insufficient publisher coverage, capture failures, first-trade verification, corporate-action exceptions and the replay-preflight manifest hash. It fails closed and exposes exception details rather than converting missing data to neutral scores.

Coverage is calculated only from supplied effective-dated identities and explicitly evidence-backed confirmed-open sessions. The dashboard is bounded-cohort research QA, not proof of exchange-wide completeness. It never authorizes backtesting or canonical promotion.

## Step 59 — six-scanner/four-horizon replay admission

Added `historical_pilot_replay_admission.py` as a separate explicit admission contract. It requires a clean quality dashboard, passed source/panel preflight, exact dataset SHA-256 match, all six registered strategy IDs, all four horizons, an untouched OOS partition, declared commission/regulatory fees/taxes/slippage, next-session/liquidity/settlement/stop-first/circuit execution assumptions, and explicit human approval with reviewer and timestamp.

A successful decision authorizes only a research-runner handoff for 24 strategy/horizon evaluations against one common immutable dataset. It does not run the backtest, claim results, calibrate probabilities, promote canonical data or enable production.

## Current evidence boundary

Tests use synthetic fixtures only. No real official NEPSE/CDSC capture, complete calendar, verified SAIL first-contract evidence or admitted historical panel has been supplied. Therefore no live data-quality result, OOS backtest, scanner accuracy, win rate or trading probability is reported. The real-world replay remains blocked until evidence is captured, independently reviewed and explicitly admitted.
