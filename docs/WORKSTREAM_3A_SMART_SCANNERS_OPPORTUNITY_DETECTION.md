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

## Phase 1 implementation log

### 3A.01 — market-wide scanner foundation

- Implemented deterministic all-candidate orchestration and `POST /v1/scan/market-wide`.
- Enforced an effective Nepal-date cutoff; future `as_of` requests are clamped to today and future OHLCV rows are excluded before analysis.
- Exposed observation coverage, missing observations, latest observation and calendar-age metadata without claiming session freshness.
- Connected the browser scanner view to the market-wide endpoint.
- Kept production ranking and BUY eligibility disabled; the empty reviewed-row manifest continues to fail closed.
- Added backend unit/API coverage for ordering, date cutoffs, missing rows, invalid universes and unreviewed-row suppression.
- Added frontend build checks to pull-request CI and changed `backend/Dockerfile` to build and package the browser terminal at `/terminal`.
- Included the dated candidate-universe CSV in the image at `/data/reference`, matching the API's runtime manifest path.
- Extended container smoke tests to call `/v1/research/readiness`, `/v1/symbols` and the full `POST /v1/scan/market-wide` endpoint across all 281 candidate symbols.
- Latest verified CI head `e156325ba646d1047b1e94488a20bc902c0faed3`: backend unit tests (run `45891652840`), backend contract tests (run `45891652836`), and frontend build/deployment-image checks (run `45891652788`) all passed. The frontend workflow builds the production assets and Docker image, then smoke-tests `/health`, `/terminal/`, `/terminal/scanner.js`, readiness, symbol loading and the full 281-symbol market-wide scan. In the clean CI container, the scanner correctly reports 281 candidate symbols, zero stored observations, 0% observation coverage and ranking disabled. This is container/CI validation, not a live deployment test.


### Exchange-primary universe source investigation (2026-11-27)

- Located the official NEPSE [stocklist page](https://www.nepalstock.com.np/stocklist). Its indexed page content is timestamped **2026-10-15 15:00** and exposes a live traded-stock list, making it a primary-source cross-check candidate.
- The repository candidate manifest is dated **2026-11-26** and sourced from NepseAlpha. The available official page snapshot is older by six weeks; it cannot establish the full active-equity membership or effective dates as of the manifest date.
- NEPSE notice PDFs found in search are for restricted subsets (for example, margin-trading eligible securities), not the complete listed-equity universe. They must not be substituted for the full universe.
- Therefore the exchange-primary reconciliation gate remains **open**. Do not promote the 281-symbol secondary snapshot or enable production ranking on the basis of this older page snapshot.

### Outstanding acceptance gates

3A.01 is **implemented in the repository but not production-verified**. Do not mark it fully complete until:
- The active-equity universe is reconciled against authoritative NEPSE membership and effective dates.
- Canonical OHLCV rows have passed the reviewed identity, provenance, session, corporate-action and point-in-time gates.
- The actual deployment's DuckDB data coverage is measured across the candidate universe.
- The built image is deployed and `/terminal`, `/v1/research/readiness`, `/v1/symbols` and `/v1/scan/market-wide` are smoke-tested against the deployed data snapshot.

The repository does not currently expose a verified deployment target or deployment credentials. CI builds a deployable image, but this is not evidence that a live service was deployed or tested.

## Initial status

- Scope catalogue: documented in this branch.
- Existing building blocks: partial; see baseline assessment.
- Full market-wide engine: not yet implemented.
- Production Top 20 / Top 10: not authorized by the current empty reviewed-row manifest.
- P&F and RRG: not verified as implemented.
- Live continuous scanning: not connected or verified.

### Candidate-universe drift check (2026-11-27)

- Rechecked the current NepseAlpha traded-stocks page: its indexed table now reports **284 active-traded entries**, compared with **281 unique symbols** in the repository's 2026-11-26 manifest. This is a three-entry count difference, not yet a verified three-symbol change: the provider's current page and the dated CSV may use different snapshot times or inclusion rules.
- The same provider page separately exposes a broader listed-security table with active and delisted rows; that table must not be conflated with actively traded equity membership.
- The NEPSE primary stocklist page remains available only as an indexed snapshot dated 2026-10-15. No newer complete official active-equity snapshot or documented official API contract was located in this search.
- Keep the dated 281-symbol file immutable as historical evidence. Do not silently append three securities, replace the candidate universe, or promote it to authoritative membership. Resolve symbol-level additions/removals against a date-aligned primary source before universe acceptance.

### NEPSE API endpoint investigation (2026-11-27)

- Found a third-party NEPSE client implementation that references the exchange-hosted paths `/api/nots/company/list` and `/api/nots/security?nonDelisted=true` (reference implementation: https://github.com/basic-bgnr/NepseUnofficialApi/blob/master/nepse/data/API_ENDPOINTS.json).
- The same client describes the company list as including delisted companies and the security list as non-delisted securities, including promoter shares. Therefore, even if retrieved successfully, the security endpoint is not automatically equivalent to the active ordinary-equity trading universe; instrument type and listing lifecycle still require explicit filtering and validation.
- Direct unauthenticated retrieval of both exchange-hosted endpoints returned HTTP 401 in this check. The endpoint response schema, authentication requirements, effective-date semantics and complete symbol membership could not be independently verified.
- This is a useful lead to an exchange-hosted API path, not an official published API contract or a validated dated universe snapshot. Do not use the third-party implementation as authority, bypass access controls, or promote its output to the candidate manifest.
- The exchange-primary universe gate remains open. Continue using the immutable 281-symbol file only as a dated secondary-source candidate set until an accessible, date-aligned primary source and instrument classification are verified.


### Private research image authentication smoke test (2026-11-27)

- Added a separate CI build of `Dockerfile.research` and exercised its private-mode HTTP boundary.
- Verified in the built image that `/health` remains reachable, unauthenticated `/v1/research/readiness` and `/terminal/` requests receive HTTP 401, and a forged subject header without the proxy secret receives HTTP 401.
- Verified that a test request carrying both a syntactically valid subject and the configured proxy secret can reach readiness and the terminal.
- CI run `45891950033` (workflow run 44) passed; its job log marks both private-image build and authentication-boundary smoke-test steps successful. Backend tests `45891950038` and backend contract tests `45891950048` also passed on commit `02722569bb3e1f5ccc38923bcc0b41e222e22272`.
- This validates the application-side gate in a container. It does **not** independently audit a real reverse proxy's header stripping, OIDC verification, TLS, CSRF protections, persistent-volume permissions, or deployed account isolation. Those remain deployment gates.


### Candidate-universe provenance surfaced in scan responses (2026-11-27)

- Every successful `POST /v1/scan/market-wide` response now includes `candidate_universe_provenance`: record count, observation date, provider, snapshot SHA-256, evidence tier, explicit `membership_authoritatively_verified=false` and `promotion_allowed=false`, plus a human-readable warning.
- The scanner UI displays the warning beside the scan coverage summary. This prevents the 281-row secondary snapshot from appearing to be an official or point-in-time NEPSE active-equity universe.
- API regression coverage asserts the provenance flags and warning are present.
- This is a transparency/contract improvement only. It does not resolve official-universe membership, reviewed OHLCV, live data coverage or deployment acceptance gates.


### Additional universe-source lead: licensed company API (2026-11-27)

- Located ShareHub's published NEPSE Data API documentation: `https://sharehubnepal.com/data/nepse-data-documentation/`.
- Its documented `GET /data/api/v1/nepse-data/companies` response includes `symbol`, `activeStatus` and `instrumentType`, which are useful fields for reconciling ordinary active equities against the current secondary-provider snapshot.
- The documentation states that requests require a ShareHub-issued Bearer token, an allow-listed server IP and an enabled licence/service. No credentials or licensed access are available in this repository context, so no authenticated data was retrieved and no membership rows were inferred from the documentation.
- This is a potential licensed cross-check, not NEPSE-primary evidence. It does not replace the exchange's official stocklist or prove point-in-time membership. Do not promote or alter the candidate manifest from this source alone.
- Latest scanner application commit `d8dfa5ae53dba67402a2379ffe383b55cafb26da` passed all three CI workflows: backend tests `45892760417`, backend contract tests `45892760653`, and frontend/deployment image checks `45892760396`.
