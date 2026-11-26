# Part 2 — NEPSE Intelligence Integration Register

**Audit date:** 2026-11-27  
**Scope:** Market health, index intelligence, sector rotation, relative strength, broker behaviour, Wyckoff and market structure.

This register distinguishes code that exists, work submitted in open pull requests, and capabilities that are actually connected to trusted point-in-time data. A module is not production-ready merely because a calculator, endpoint, or dashboard exists.

## Current integration map

| Capability | Evidence in repository | Current status | Remaining gate |
|---|---|---|---|
| Market-health components | PR #132 ports the former PR #55 work onto current main | **Merged research-only pipeline and readiness endpoint**; five evidence-gated components and weighted regime descriptor; endpoint remains UNKNOWN until trusted primary sources are connected | Connect trusted canonical index, market-summary, mature-equity and sector evidence; validate market-health outputs against independent history |
| Official market-summary evidence | PR #133 | **Merged review-only validator** for pinned 2026-11-26 NEPSE official HTTPS capture; raw response SHA-256 and 229 dated records verified | Separate finality attestation and exact official session calendar are still required before turnover inputs can be admitted |\n| NEPSE index intelligence | `backend/app/index_intelligence.py`; PR #118; API `/v1/research/index-intelligence` added by PR #125 | **Merged research-only calculator and endpoint**; exact verified session calendar, point-in-time availability, returns, moving averages, 52-week high and descriptive regime | Connect verified primary NEPSE index/sub-index records and authoritative calendar; no live source adapter yet |
| Sector rotation | `backend/app/verified_sector_rotation.py`; PR #119; API `/v1/research/sector-rotation` added by PR #125 | **Merged research-only calculator and endpoint**; dated membership, constituent median returns and NEPSE-relative strength over 1W/1M/3M/6M | Connect verified primary index/stock data and official effective-dated sector membership; constituent medians are not official sector index returns |
| Relative strength | `relative_strength_features.py` and tests; exact-session benchmark alignment | Implemented as a feature; production evidence availability remains conditional | Connect verified point-in-time security and NEPSE benchmark histories; preserve missing-horizon exclusions |
| Broker daily ledger/memory | `broker_behavior_memory.py`, `broker_memory_store.py`, `broker_ingestion.py`, `broker_daily_history.py`; integrated by PR #121 | **Merged research-only backend stack**; append-only persistence and reconciled daily history code are present | Live NEPSE floorsheet ingestion, production storage operations, identity reconciliation and source completeness still require verified data operations |
| Rolling broker profiles | `broker_rolling_profiles.py`; PR #121 | **Merged research-only feature**; 5/21/252 verified-session windows and coverage-aware direction | Connect trusted complete-session manifests and validate real historical broker profiles |
| Broker sector rotation | `broker_sector_rotation.py`; PR #121; price/broker join in PR #120; API `/v1/research/sector-confluence` added by PR #125 | **Merged descriptive feature and confluence endpoint**; requires aligned as-of sessions and point-in-time availability | Connect trusted server-side broker/market artifact adapters; source lineage remains caller-attested at the API boundary |
| Broker-to-scanner bridge | `broker_intelligence_dashboard.py`; PR #121 | **Merged read-only dashboard composer**; caller-supplied manifests are propagated, not independently re-attested | Add trusted server-side adapters and verify provenance before use |
| Early accumulation/distribution candidates | `early_market_candidates.py`, `broker_pattern_detector.py`; PR #121 | **Merged research-only candidate engines**; detector requires complete five-session broker inventory, matched contract parties, verified price/volume and market/sector context | Calibrate against independent point-in-time history; no production actions until holdout validation |
| Broker intelligence dashboard | `/v1/research/broker-dashboard`; PR #121 | **Merged read-only endpoint**; broker codes remain execution-channel identifiers, not beneficial owners | Connect authenticated trusted inputs; no ownership/intent inference |
| Wyckoff | `wyckoff_features.py` and tests | Existing deterministic candidate-event feature | Confirm validated OHLCV/corporate-action inputs; event labels remain hypotheses, not proof of operator activity |
| Market structure / SMC | `market_structure.py`, `smc_features.py`; PR #18 also open | Feature work exists; some SMC outputs explicitly experimental | Preserve causal timing, zone lifecycle and calibration boundaries; do not score uncalibrated heuristics |
| Unified Part 2 snapshot | PR #115 and PR #128 | **Merged**; PR #128 adds deployment-pinned artifact loading, hash checks, point-in-time admission and module-specific quality gates | Provision protected deployment registry and immutable artifacts from verified source operations; no live source feed is connected |

## Completed in this task

- Merged PR #118 (`efca2dc03bb3b2c72b63e05b1d3167cc48350e85`) for verified index intelligence after fixing test calls to supply the required verified session calendar.
- Merged PR #119 (`7c89973300910bb48b7ed554ddbd110ca53c8c23`) for verified constituent-based sector rotation after correcting a missing-session fixture that removed a date outside the tested 1M window and a tuple-mutation test error.
- Merged PR #120 (`0efd3a5b28ff156c39238925be85c85131f81343d6`) for market/broker sector confluence.
- Merged PR #125 (`b52cc3c21cda5c3bb3eb106fe40e5ee2932ceb6d`) exposing index, sector and confluence research endpoints.
- Merged PR #121 (`cd8a35ca72dbe96975a51c357022ec336751f23d`) after all unit, backend and data-inventory checks passed. It ports the broker memory, daily ledger, ingestion, rolling profiles, broker-sector rotation, accumulation/distribution candidates, dashboard, early-signal engine and immutable floorsheet source capture onto `main`.
- Exposed three read-only research endpoints: `/v1/research/broker-dashboard`, `/v1/research/early-signals` and `/v1/research/broker-patterns`.
- Added the point-in-time broker pattern detector and a Nepal-local date-cutoff regression test.
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
**Completed on main.** Broker memory/profile/sector-rotation/candidate/dashboard/early-signal code is integrated through PR #121. The five-component market-health pipeline and fail-closed readiness endpoint were ported from the old PR #55 and merged through PR #132 (`b917507ac2fd702205a5adfa224800dc04488767`). The older PR #55 is superseded; its original branch is not the canonical integration.

### P2.02 — Connect primary NEPSE index intelligence data
The calculator and research endpoint are merged. The official NEPSE market-summary capture is independently hash/origin validated by PR #133, but its rows remain review-only because finality and exact session coverage are not yet attested.

**Endpoint discovery update — 2026-11-27:** community-maintained reverse-engineered references document two candidate route families:
- Graph POST routes: `/api/nots/graph/index/58` (NEPSE), `/api/nots/graph/index/57` (Sensitive), `/api/nots/graph/index/62` (Float), `/api/nots/graph/index/63` (Sensitive Float), and IDs 51–67 for sector/sub-index graphs. The client describes Salter authorization and a generated JSON `id` request body.
- Index-history GET route: `/index/history/58` (NEPSE); a separate community reference lists this route family but does not establish query parameters, schema, coverage, date limits or pagination.

These are **third-party reverse-engineered references only**, not an official NEPSE API specification. First-party page retrieval was attempted for the NEPSE homepage and candidate paths, but the homepage exposed no readable source and direct candidate-route retrieval was inaccessible in this research environment. No first-party response bytes, TLS capture report or payload hash were obtained. An inaccessible route is not evidence that the route does not exist. Tracking issue: #134.

**Next gate:** obtain a first-party browser/network capture or a direct TLS-verified official response for each candidate route; preserve method, exact path, query/body, redacted headers, raw bytes/hash, HTTP status, content type and retrieval timestamp. Validate schema, index identity, dates, duplicates, ordering, history depth and session coverage against an independently verified calendar. Keep all sub-indices unavailable until each one independently passes. Do not build or enable a data collector around undocumented assumptions.

### P2.03 — Connect primary sector rotation data
The calculator, API endpoint and broker confluence layer are merged. Remaining work is trusted ingestion of verified stock/index rows and effective-dated official sector membership. Publish leadership only when membership and price coverage pass.

### P2.04 — Wire trusted artifacts into the snapshot
**Merged in PR #128** (`00a92fd23e924b1a3b28858e33baa578bf87ccfb`). The server-side artifact store loads only deployment-pinned payload paths and SHA-256 hashes, checks source validation/finality, freshness and point-in-time availability, and fails closed on missing evidence. It additionally requires an exchange calendar identity, corporate-action status for price-derived modules, effective-dated sector-membership versioning for sector modules, and verified broker-code mapping plus coverage for broker modules. This is an adapter foundation only: no deployment registry or live NEPSE source feed has yet been provisioned.

### P2.05 — Integration and regression acceptance
**Merged and accepted in PR #130.** Cross-module snapshots require a common as-of date and consistent exchange-calendar identity; missing or mismatched calendar identity marks evidence partial and prevents full research status. Regression coverage includes as-of mismatch, missing/inconsistent calendar identity, conflicting calendar versions and Nepal-local cutoff handling. Deployment registry quality gates require calendar identity, verified corporate-action status for price modules, verified effective-dated sector membership and verified broker-code mapping/coverage. Production scores and trade actions remain disabled.

## Acceptance criteria for Part 2

Part 2 is complete only when:
- all eight required modules have real, independently validated, point-in-time upstream artifacts;
- index and sector intelligence cover their required horizons with explicit missing-data states;
- broker daily/weekly/monthly/yearly profiles are backed by reconciled floorsheet sessions and identity coverage;
- Wyckoff and SMC features are causal and use validated price history;
- the unified snapshot can be built from trusted server-side adapters and retains full provenance;
- integration tests demonstrate fail-closed behaviour under missing, stale, late, conflicting and incomplete evidence; and
- production scoring/trading remains disabled until separate strategy validation and backtesting gates are passed.

**Current overall status:** Partially implemented. The trusted artifact-store foundation is merged and cross-module alignment gates are being added. Protected deployment storage, verified live source ingestion, market-health integration and independent strategy/backtest validation remain incomplete.

## P2.02 endpoint discovery evidence and limitations

- Candidate route map reference: `basic-bgnr/NepseUnofficialApi`, `nepse/data/API_ENDPOINTS.json` and `nepse/NepseLib.py` (community-maintained, reverse-engineered).
- The client identifies its base URL as `https://www.nepalstock.com` and sends POST requests to graph endpoints using an authorization token and generated request ID.
- This does not independently prove that the route remains active, that the returned payload is final, that the response is complete, or that the date series covers every exchange session.
- No candidate response has been admitted to the trusted artifact store. No index history has been promoted, backfilled, forward-filled or used to calculate market health.
- Issue #134 records the required first-party capture, TLS, hash, schema, session-calendar and per-index acceptance gates.

## P2.03 sector membership audit update — 2026-11-27

PR #139 is merged at `bf5d16cdcaedaa85478526ae415dac791bf380e6`. GitHub Actions checks `backend-tests` and `Backend contract tests` both completed successfully.

The new `backend/app/sector_membership_manifest.py` performs deterministic structural checks for versioned membership manifests: manifest/payload SHA-256 references, source identity consistency, capture cutoff, record identity, sector codes, effective-date intervals, overlap detection, source-record references and point-in-time symbol coverage. Its strongest possible status is `review_ready`; it always reports `verified=false` and `admission_allowed=false`. It does not authenticate a publisher or prove official NEPSE classification.

Tracking issue [#146](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/issues/146) now owns the remaining primary-source work: acquire a reproducible NEPSE/SEBON sector classification source, preserve raw bytes and TLS/provenance evidence, establish effective dates and stable security identity, reconcile symbol changes and independently review the resulting manifest. No sector membership was promoted. Sector leadership and market-health sector participation remain unavailable until that evidence is approved.


## P2.03 Nepal-local effective-date validator correction — 2026-11-27

PR #147 was merged after both GitHub Actions workflows passed on the exact reviewed head `28e56e1874f1b4dc78a3eadb651ddddb8688b894`. Squash merge commit: `b6cc4a32baa2e36290ea2cd8e0985fe51d92a974`.

The validator now derives the effective-date cutoff from `Asia/Kathmandu`, preventing UTC date rollover from selecting the prior Nepal calendar date near local midnight. It also rejects non-string/blank expected symbols and invalid/empty sector-code entries. Regression coverage includes 00:15 Nepal local time while UTC remains on the previous date, plus malformed expected-symbol input.

This is a structural correctness fix only. Manifest status remains `review_ready`; `verified=false` and `admission_allowed=false`. It does not validate or promote official sector membership, and sector signals remain disabled pending issue #146 evidence review.


### P2.03 primary-source acquisition check — 2026-11-27

A further discovery pass checked the official NEPSE stock-list URL (`https://www.nepalstock.com.np/stocklist`) and SEBON annual-report material. Search indexing exposed a current stock-list snapshot, but not a sector membership export with effective dates; direct retrieval of the NEPSE page timed out in this pass, so no raw first-party response, TLS validation report or response hash was captured. The surfaced SEBON annual-report material is FY 2015/16 and contains aggregate historical sector counts, not a current security-level effective-dated mapping.

Third-party directories remain discovery/corroboration only. No sector mapping was inferred, backdated or promoted. Issue #146 records this acquisition result and the exact next gate: first-party capture containing security identity, classification and effective-date/current-snapshot semantics, with raw bytes and provenance preserved. Until that evidence is obtained and independently reviewed, official sector membership, sector leadership and market-health sector participation remain unavailable.


### P2.03 validator hardening — PR #148 merged 2026-11-27

PR #148 (`c8b64f59d750846209bbff4a11852665741fbb7e`) rejects non-string and blank `records[].symbol` values rather than coercing malformed values into synthetic identifiers. Regression tests cover null, numeric, list, object and whitespace-only symbols. Both `backend-tests` and `Backend contract tests` passed on the exact reviewed head `9088b71394c9b5c3e1bb017f29086c2667513a67` before squash merge.

This is structural validation hardening only. It does not authenticate the source or enable membership admission. Official sector membership and effective dates remain blocked on primary-source evidence tracked in issue #146.


### P2.03 canonical sector-code validation — PR #151 merged 2026-11-27

PR #151 (`4257cd95b0402102421992457738a5926e076019`) rejects configured allowed-sector-code values with leading or trailing whitespace and adds a regression test. Both `backend-tests` and `Backend contract tests` passed on exact head `248e69867c430fa176fc7b19ab38aaafc67986cf` before squash merge.

Structural validation only: no official sector membership source is authenticated; `verified=false` and `admission_allowed=false` remain in force. Primary-source acquisition remains blocked and tracked in issue #146.
