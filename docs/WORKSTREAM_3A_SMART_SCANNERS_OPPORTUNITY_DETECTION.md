# Workstream 3A — Smart Scanners and Opportunity Detection

**Status:** Development required; workstream opened  
**Scope:** 3A.01–3A.23  
**Branch:** `feat/3a-smart-scanners-opportunity-detection`  
**Baseline:** `main` at `80aa212351dfefc1b58d21d3e4f318c07d606260`

## Objective

Build an evidence-first, market-wide NEPSE scanning system that discovers early opportunities, classifies setup stages, detects deterioration and ranks candidates without overstating what the available data proves.

A scanner result is a research candidate, not a trade instruction. No scanner may infer missing sessions, impute missing component scores, use future data, or convert broker execution records into beneficial-ownership claims.

## Current baseline assessment

The repository currently has useful but incomplete foundations:

- `backend/app/scanner.py`: basic daily OHLCV descriptors (SMA20, 20-session change and relative volume); not a market-wide multi-strategy engine.
- `backend/app/scoring_engine.py`: eight-component weighted score with explicit coverage, hard blocks and strict BUY prerequisites. Missing evidence is not imputed.
- `backend/app/scanner_eligibility.py`: fail-closed row eligibility using reviewed identity, lifecycle, session, provenance, corporate-action and point-in-time evidence. The server-owned reviewed-row manifest is currently empty, so this gate does not authorize production rankings.
- `backend/app/market_structure.py`: causal daily-bar structure/event observations; not a complete SMC liquidity engine.
- `backend/app/floorsheet_pipeline.py`: typed floorsheet processing and broker aggregation foundations; broker codes remain execution-channel evidence, not beneficial ownership.
- Wyckoff candidate-event documentation and scoring foundations exist, but candidate heuristics do not prove a Wyckoff campaign.
- Frontend scanner/dashboard assets exist, but live feed, production rankings and the full set of scanner outputs are not verified as connected.

Therefore, this workstream starts from partial foundations; it does not claim any of the 23 deliverables is complete.

## Scanner catalogue and acceptance targets

| ID | Scanner / feature | Required output and acceptance target |
|---|---|---|
| 3A.01 | All-market stock scanner | Scan the approved active-equity universe for a selected as-of date; expose coverage, exclusions, stale/missing data and per-symbol status. |
| 3A.02 | Early accumulation scanner | Identify quiet supply absorption candidates using range behaviour, relative volume, close location and demand/supply evidence; label as candidates only. |
| 3A.03 | Re-accumulation scanner | Detect pauses/consolidations within an established uptrend; distinguish from distribution and ordinary sideways action. |
| 3A.04 | Momentum scanner | Rank positive price/volume momentum over documented horizons; normalize for market/sector context and liquidity. |
| 3A.05 | Reversal scanner | Detect potential trend exhaustion and reversal structure; require confirmation and show invalidation levels. |
| 3A.06 | Trend-relay scanner | Identify orderly continuation/pullback setups in established trends; avoid late/chasing entries. |
| 3A.07 | Breakout-ready scanner | Find compression/base candidates near defined resistance with improving participation; explicitly mark unconfirmed. |
| 3A.08 | Confirmed breakout scanner | Require a completed-bar close through a validated level plus participation/quality checks; reject false or unconfirmed breaks. |
| 3A.09 | Breakout retest scanner | Track post-breakout retests, support hold/failure, volume behaviour and retest invalidation. |
| 3A.10 | Distribution scanner | Flag potential supply/distribution evidence and deteriorating structure; do not infer intent or manipulation. |
| 3A.11 | Breakdown-risk scanner | Identify support loss, trend deterioration, liquidity and gap risk; surface risk before opportunity scores. |
| 3A.12 | Strongest relative-strength scanner | Compare each eligible equity with NEPSE benchmark and peer/sector returns over matched point-in-time windows. |
| 3A.13 | Broker accumulation scanner | Show broker-side net participation/recurrence only where floorsheet coverage and broker identity are verified; never label it beneficial-owner accumulation. |
| 3A.14 | Sector leadership scanner | Rank sectors by breadth, relative strength, momentum and constituent participation using dated membership. |
| 3A.15 | Volume expansion and dry-up scanner | Detect statistically contextualized volume expansion/contraction, with liquidity and data-quality safeguards. |
| 3A.16 | Wyckoff pattern scanner | Surface phase/event candidates (e.g. spring, test, SOS/LPS, upthrust/SOW) with event dates, causal evidence and confidence limits. |
| 3A.17 | Minervini trend-template scanner | Evaluate each documented trend-template condition separately; report pass/fail/unavailable rather than hiding missing inputs. |
| 3A.18 | SMC structure and liquidity scanner | Detect causal swing structure, breaks/shifts, equal highs/lows and liquidity zones; avoid repainting and lookahead. |
| 3A.19 | Point & Figure dashboard | Produce reproducible P&F columns, box/reversal settings, patterns and dated signals; parameters visible and versioned. |
| 3A.20 | Relative Rotation Graph (RRG) dashboard | Plot sector relative strength and momentum against a benchmark; require synchronized sector/index series and disclose lookback. |
| 3A.21 | Top 20 opportunity ranking | Rank only eligible candidates using reviewed component outputs, coverage, risk gates and deterministic tie-breaking; expose full score decomposition. |
| 3A.22 | Top 10 watchlist generation | Build a diversified, deduplicated watchlist from eligible candidates with setup stage, trigger, invalidation and review date. |
| 3A.23 | Avoid and weak-stock scanner | Identify weak trend/relative strength, distribution, breakdown, poor liquidity, stale data and unresolved quality risks; state exact exclusion reasons. |

## Shared engine contract

Every scanner must return a common, versioned result contract containing:

- `scanner_id`, `scanner_version`, `symbol`, `security_id`, `as_of_date`, `generated_at`.
- `status`: observed, candidate, confirmed, rejected, unavailable, insufficient_data or data_quality_failed.
- `setup_stage` and `direction` where applicable.
- Evidence-backed features, raw measurements, thresholds and lookback windows.
- Source/evidence references, source hashes and point-in-time availability.
- Data coverage, missing inputs, exclusions and limitations.
- Score and component decomposition only when supported; never fabricate confidence or probability.
- Trigger/confirmation conditions and invalidation conditions where applicable.

All computations must be causal: a signal dated at session T may use only data available by the defined decision timestamp at T. Indicators must be computed from completed, eligible observations, not from future rows or silently inferred calendar sessions.

## Ranking and safety policy

1. Validate instrument identity, active-equity membership, session status, source provenance, corporate actions, price basis and point-in-time availability before scanning.
2. Apply liquidity, stale-data, unresolved-conflict and market-regime hard blocks before opportunity ranking.
3. Preserve unavailable component values as unavailable. Do not replace missing evidence with zero, neutral or a guessed score.
4. Keep component coverage visible. Provisional coverage cannot become a production BUY or an unqualified Top 20 selection.
5. A high composite score is not a probability. Calibration requires a separately validated, out-of-sample outcome study.
6. Broker flow is broker-code execution-channel activity, not proof of client identity, beneficial ownership, coordination or intent.
7. Separate candidate detection from confirmation. A breakout-ready candidate is not a confirmed breakout.
8. Preserve the avoid/risk output even when opportunity candidates exist; risk warnings take precedence over promotional ranking.
9. Backtests must use point-in-time universe membership, session evidence, corporate-action handling, NEPSE trading constraints, realistic costs and no lookahead. Report sample size and uncertainty.
10. Do not enable live/continuous scanning until an authorized, tested feed and scheduling path exist. Daily EOD scanning is not continuous intraday monitoring.

## Delivery sequence

### Phase 0 — Scope and contracts
- Record the 23 scanner definitions and acceptance criteria (this document).
- Audit existing feature producers, API contracts, frontend integration and test coverage.
- Freeze shared result schemas, as-of semantics, evidence requirements and scanner versioning.

### Phase 1 — Market-wide foundation
- Implement a universe/as-of orchestration layer over the fail-closed eligibility gate.
- Add shared feature computation, caching, missingness/coverage reporting and deterministic scanner execution.
- Add integration tests for no-lookahead, stale data, missing sessions, inactive instruments and empty reviewed manifests.

### Phase 2 — Core price/volume opportunity scanners
- Implement 3A.01–3A.12 and 3A.15.
- Add golden fixtures and edge-case tests for gaps, suspensions, illiquidity, corporate actions, volume spikes and false breakouts.

### Phase 3 — Advanced evidence engines
- Complete 3A.13–3A.14 and 3A.16–3A.18.
- Keep broker identity coverage, dated sector membership, Wyckoff heuristic limits and SMC experimental/observed status explicit.

### Phase 4 — Analytical dashboards
- Implement reproducible 3A.19 P&F and 3A.20 RRG calculations and visual outputs with visible parameters and data coverage.

### Phase 5 — Ranked outputs and validation
- Implement 3A.21–3A.23 only after upstream scanner and eligibility gates pass.
- Run historical replay, walk-forward and out-of-sample validation; publish failure cases and performance by regime.
- Connect frontend views and verify API-to-UI behaviour against the same as-of snapshot.

## Workstream completion gates

A scanner is complete only when its implementation, tests, data/evidence contract, limitations, API output and UI representation are all verified. A workstream item must not be marked complete merely because a prompt, design, heuristic or static dashboard exists.

The overall workstream is complete only when all 23 items pass their acceptance criteria, integration tests pass, ranked outputs are reproducible, and the production data/rights/deployment gates are independently satisfied.

## Initial status

- Scope catalogue: documented in this branch.
- Existing building blocks: partial; see baseline assessment.
- Full market-wide engine: not yet implemented.
- Production Top 20 / Top 10: not authorized by the current empty reviewed-row manifest.
- P&F and RRG: not verified as implemented.
- Live continuous scanning: not connected or verified.
