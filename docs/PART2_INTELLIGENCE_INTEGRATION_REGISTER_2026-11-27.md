# Part 2 — NEPSE Intelligence Integration Register

**Audit date:** 2026-11-27  
**Scope:** Market health, index intelligence, sector rotation, relative strength, broker behaviour, Wyckoff and market structure.

This register distinguishes code that exists, work submitted in open pull requests, and capabilities that are actually connected to trusted point-in-time data. A module is not production-ready merely because a calculator, endpoint, or dashboard exists.

## Current integration map

| Capability | Evidence in repository | Current status | Remaining gate |
|---|---|---|---|
| Market-health components | PR #55 adds five evidence-gated components and a readiness endpoint | Open PR; tests passed at last check | Rebase/review; connect trusted canonical index, market-summary, mature-equity and sector evidence |
| NEPSE index intelligence | `index_ohlcv` evidence type and NEPSE benchmark admission used by relative strength | Partial; no standalone integrated index intelligence module confirmed in this audit | Build index trend/returns/volatility and index/sub-index comparisons from verified index records |
| Sector rotation | `sector_strength_features.py`; broker-sector rotation in PR #108 | Stock-sector strength exists; broker-sector rotation is an open stacked PR | Verify dated sector membership and index/price series; integrate sector ranking and 1W/1M/3M/6M RS |
| Relative strength | `relative_strength_features.py` and tests; exact-session benchmark alignment | Implemented as a feature; production evidence availability remains conditional | Connect verified point-in-time security and NEPSE benchmark histories; preserve missing-horizon exclusions |
| Broker daily ledger/memory | PRs #88, #89, #92, #94, #97, #99, #101 | Multiple stages implemented in open PR stack | Complete dependency review, source completeness, identity reconciliation and persistence acceptance |
| Rolling broker profiles | PR #105 | Open PR | Merge after dependencies; validate complete-session coverage and daily/weekly/monthly/yearly windows |
| Broker sector rotation | PR #108 | Open PR | Merge after PR #105; verify authoritative sector mapping and source completeness |
| Broker-to-scanner bridge | PR #111 | Draft/open PR | Integrate only after upstream profile and sector artifacts are accepted |
| Early accumulation/distribution candidates | PR #109 | Open PR | Keep descriptive/research-only until independent price/volume and broker evidence gates pass |
| Broker intelligence dashboard | PR #114 | Open PR stacked on PR #109; unit and backend tests passed at last check | Resolve dependency stack and verify source manifests; descriptive only, no ownership/intent inference |
| Wyckoff | `wyckoff_features.py` and tests | Existing deterministic candidate-event feature | Confirm validated OHLCV/corporate-action inputs; event labels remain hypotheses, not proof of operator activity |
| Market structure / SMC | `market_structure.py`, `smc_features.py`; PR #18 also open | Feature work exists; some SMC outputs explicitly experimental | Preserve causal timing, zone lifecycle and calibration boundaries; do not score uncalibrated heuristics |
| Unified Part 2 snapshot | PR #115 | **Merged** as `683e281e393b20d92fb595c945a3fa5f34892dee` | Wire only trusted server-side artifact envelopes; contract intentionally emits no score, probability or trade action |

## Completed in this task

- Reconciled the active Part 2 work against the current GitHub pull-request stack rather than starting duplicate modules.
- Merged PR #115, the fail-closed composition contract for eight intelligence modules:
  - market health
  - index intelligence
  - sector rotation
  - relative strength
  - broker profiles
  - broker-sector rotation
  - Wyckoff
  - market structure
- Confirmed the PR's four GitHub Actions checks completed successfully before merge.
- The merged contract preserves missing or unverified artifacts as unavailable, checks point-in-time availability and provenance envelope fields, and disables production scores, probabilities, signals and trade actions.

## Critical integration rules

1. **No fabricated market state.** Missing index, market-summary, sector, broker or OHLCV inputs remain UNKNOWN/unavailable, never neutral or zero.
2. **Point-in-time only.** Every artifact must carry an as-of date and timezone-aware availability timestamp no later than the decision cutoff.
3. **Source validation precedes composition.** The snapshot contract propagates upstream attestations; it does not independently validate source files. Only trusted backend callers may construct artifact envelopes after checking source manifests and evidence.
4. **Broker data is descriptive.** Broker codes identify transaction channels, not beneficial owners. Flow patterns alone do not prove accumulation intent, distribution, circular trading, cornering or manipulation.
5. **Sector membership is dated.** Do not apply today's sector map retrospectively without effective-dated evidence.
6. **No production score or BUY/SELL.** The merged snapshot contract deliberately has `production_score=null`, `probability=null`, `signals_enabled=false` and `trade_actions_enabled=false`.
7. **Confidence is coverage-aware.** Do not treat absent modules as zero-weight neutral contributions.

## Next implementation sequence

### P2.01 — Stabilize upstream module dependency stack
Review and resolve PRs #55, #105, #108, #109, #111 and #114 in dependency order. Do not merge a stacked PR before its base dependency is merged or deliberately retargeted.

### P2.02 — Implement standalone NEPSE index intelligence
Use verified NEPSE index and sub-index observations to calculate point-in-time trend, 1W/1M/3M/6M returns, moving-average structure, volatility and index-vs-market breadth context. Keep unavailable sub-indices explicit.

### P2.03 — Complete sector rotation
Use dated sector membership and verified sector price/index evidence. Rank by 1W/1M/3M/6M returns and relative strength vs NEPSE; publish leadership status only when membership and price coverage pass.

### P2.04 — Wire trusted artifacts into the snapshot
Create a trusted server-side adapter for each of the eight required modules. Validate source manifest, finality, unique lineage, coverage and availability before passing the artifact to `build_market_intelligence_snapshot`.

### P2.05 — Integration and regression acceptance
Add cross-module tests for stale/future artifacts, missing modules, partial coverage, duplicate IDs, wrong sector membership version, broker identity gaps and market-calendar mismatch. Verify no score/action is emitted when any required evidence gate fails.

## Acceptance criteria for Part 2

Part 2 is complete only when:
- all eight required modules have real, independently validated, point-in-time upstream artifacts;
- index and sector intelligence cover their required horizons with explicit missing-data states;
- broker daily/weekly/monthly/yearly profiles are backed by reconciled floorsheet sessions and identity coverage;
- Wyckoff and SMC features are causal and use validated price history;
- the unified snapshot can be built from trusted server-side adapters and retains full provenance;
- integration tests demonstrate fail-closed behaviour under missing, stale, late, conflicting and incomplete evidence; and
- production scoring/trading remains disabled until separate strategy validation and backtesting gates are passed.

**Current overall status:** Partially implemented. The composition contract is merged, but upstream data connections and several module/dependency integrations remain incomplete.