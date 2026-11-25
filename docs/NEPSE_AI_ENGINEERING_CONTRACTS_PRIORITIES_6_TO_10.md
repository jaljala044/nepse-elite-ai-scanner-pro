# NEPSE AI Engineering Contracts — Priorities 6–10

Date: 2026-11-25  
Status: **design contract / implementation gate**, not a claim that production ingestion, broker identity, feature generation or predictive validation is live.

## Why this layer is being started now

The project has historical OHLCV and floorsheet research artifacts, but source lineage, session dates, instrument membership and upstream rights are not yet sufficiently verified for canonical training. Engineering must therefore preserve raw evidence and uncertainty. Nothing in this document promotes an unverified archive or creates a live market feed.

## Priority 6 — production-safe floorsheet ingestion

### Required pipeline
`request -> immutable raw capture -> parse -> schema validation -> normalization -> idempotent persistence -> reconciliation -> publish`

The raw-capture step must complete before parsing or normalization. A parse failure must not destroy the captured response.

### Raw response envelope
Every fetch attempt records:
- `source_id`, `source_url`, `source_method`, request parameters (secrets redacted), request timestamp and response timestamp in UTC.
- Claimed exchange-local session date (Asia/Kathmandu), independently verified session date/status, and the evidence reference used for that verification.
- HTTP status, response content type, byte length, SHA-256 of exact response bytes, retrieval software version and parser version.
- Fetch attempt ID, retry number, outcome, error class, and upstream request/correlation ID when available.
- Rights/authorization status and source lineage status; unknown must remain unknown.

### Persistence and safety invariants
1. Raw payloads are append-only and content-addressed by SHA-256; never overwrite a prior response.
2. Re-running the same source/session/payload is idempotent. A changed payload creates a new immutable version and a reconciliation event.
3. No `clear worksheet`, destructive replace, or delete-before-upload operation.
4. TLS certificate verification is mandatory. Fail closed on certificate errors; no insecure fallback.
5. Retry only transient failures with bounded exponential backoff and jitter. Do not retry validation failures as if they were transport failures.
6. Normalize into a separate table only after schema checks; preserve original field names and raw values.
7. Quarantine unexpected schemas, duplicate contract IDs, malformed dates, impossible arithmetic and conflicting versions. Do not silently drop or repair.
8. A missing response is not proof of a market closure. A local date is not proof of an exchange session.
9. Publish only after row counts, uniqueness, totals and source/session checks pass; publication records the exact raw hashes.
10. Secrets never enter logs, artifacts or committed fixtures.

### Minimum normalized contract fields
`source_id, fetch_id, raw_sha256, source_record_key, exchange_session_date, session_status, contract_id, symbol, security_id, buyer_broker_id, seller_broker_id, quantity, rate, amount, trade_timestamp, ingested_at_utc, parser_version, validation_status`.

Fields not supplied by a source remain null; do not manufacture stable IDs or trade timestamps. Record source schema version and explicit field mapping.

### Release gate
Unit tests for retries, TLS fail-closed, idempotency, changed payload versions, malformed schema, duplicate IDs, timezone boundaries and non-destructive persistence; plus a dry-run against a captured fixture with matching raw hash. Live activation additionally requires documented authorization, real endpoint verification, session-date evidence and reconciliation.

## Priority 7 — broker identity and footprint reconciliation

### Identity model
Use a stable internal `broker_entity_id` only when supported by authoritative evidence. Keep source-specific IDs separate:
- `broker_source_id(source_id, source_broker_code, valid_from, valid_to, observed_at, evidence_id)`
- `broker_entity(broker_entity_id, canonical_name, entity_status)`
- `broker_name_history(broker_entity_id, name, valid_from, valid_to, evidence_id)`
- `broker_identity_link(source_id, source_broker_code, broker_entity_id, link_status, evidence_id, reviewer, reviewed_at)`

Never merge brokers based only on similar names. Unknown, ambiguous, renamed and unmapped identities remain explicit states. Preserve the buyer and seller sides independently.

### Reconciliation grain
Primary aggregation grain: `session_date × security_id × broker_entity_id × side`, with source, raw hash and contract-level lineage retained. Derive buy/sell quantities, amount, trade count, weighted average price and net flow only when both sides and units are defined. Do not infer beneficial ownership, client identity, intent, accumulation or distribution from broker code alone.

### Required controls
- Contract-ID uniqueness within the source's documented scope.
- Buyer/seller symmetry and aggregate contract reconciliation.
- Quantity and amount arithmetic tolerance documented per source.
- Broker code changes and name changes are effective-dated, not retroactively overwritten.
- Missing broker rows and partial-day captures create coverage flags.
- Duplicate contracts across publishers are not double-counted; matching data from two mirrors is not independent provenance.
- Every broker feature links to its contributing contract IDs or immutable raw partitions.

### Release gate
Fixtures for code reuse across sources, name change, ambiguous match, unmapped broker, buyer/seller reversal, duplicate contract and partial capture. No broker-level model feature is eligible until identity and coverage flags are carried through.

## Priority 8 — point-in-time feature store

### Mandatory temporal fields
Every raw, normalized and derived record carries:
- `event_time`: when the market event occurred, if known.
- `published_at`: when the source made it available, if known.
- `retrieved_at`: when this system obtained it.
- `available_at`: earliest time the strategy could actually have consumed it, derived conservatively.
- `valid_from/valid_to`: effective interval for reference data such as symbol and broker mappings.
- `computed_at`, `feature_version`, `source_snapshot_id`, `lineage_hash`.

Unknown timestamps stay null and block point-in-time eligibility where necessary. Do not substitute retrieval date for publication date.

### As-of query rule
For a decision timestamp T, include only records with `available_at <= T`, and use reference mappings whose effective interval contains the event/decision time under the declared policy. Late corrections are new versions; historical snapshots must remain reproducible as they were knowable at T.

### Corporate actions and instrument lifecycle
Maintain effective-dated security master, symbol aliases, listing/trading/suspension/delisting states, splits, bonuses, rights, dividends and adjustment factors with source evidence. Keep raw unadjusted prices immutable. Adjusted series must be versioned and specify whether adjustment factors were known at each historical T.

### Leakage barriers
- No centered rolling windows, future-filled values or full-sample normalization.
- Fit scalers, imputers, feature selection and thresholds on training windows only.
- Purge/embargo overlapping labels where horizons overlap.
- Keep corrected/late-arriving observations out of earlier snapshots.
- Every feature row records its maximum input `available_at`; enforce `max_input_available_at <= decision_time`.

### Release gate
Automated time-travel tests: a late publication cannot appear in an earlier snapshot; a future corporate action cannot alter a past as-of view; symbol mapping changes apply only in their valid interval; feature values reproduce from pinned raw hashes and code version.

## Priority 9 — explainable footprint features and episode retrieval

### Market-wide features
- Breadth: advancing/declining/unchanged counts and ratios, with explicit eligible-universe denominator.
- Turnover and volume: total value/quantity, active-security count, missing-data coverage.
- Concentration: top-k security/broker share and concentration indices, only where denominator and coverage are adequate.
- Participation: unique mapped/unmapped broker counts and side-specific activity.
- Regime context: index return/volatility, breadth/turnover regime and source coverage.

### Security-level features
- Price/volume structure: returns, range, gap, turnover, volume relative to trailing as-of baseline.
- Broker participation: buyer/seller concentration, net quantity/value, persistence and breadth of participation.
- Footprint changes: new/returning broker activity, concentration shifts, unusual participation relative to that security's own history.
- Data-quality context: session confidence, source coverage, missing contracts, unresolved identity share and corporate-action status.

### Interpretation rules
Accumulation/distribution are hypotheses, not direct observations. Require multiple independent dimensions, persistence across verified sessions, price/volume context and coverage thresholds. A broker's net buying is not proof of beneficial ownership or intent. Similarity search returns historical analogues, not guaranteed forecasts.

### Episode retrieval contract
Store episode start/end, security/universe, regime, feature snapshot IDs, source coverage, similarity method/version, distance and nearest-neighbour set. Exclude future observations from feature vectors and labels. Show both matching evidence and disconfirming evidence, including how many historical episodes were found and the outcome distribution.

### Output format
Each signal carries `hypothesis`, `evidence_for[]`, `evidence_against[]`, `coverage`, `as_of_time`, `confidence_method`, `confidence`, `alternative_scenarios[]`, `invalidators[]`, `feature_versions[]` and `lineage_refs[]`. If coverage or identity quality is insufficient, return `insufficient_evidence`, not a forced signal.

### Release gate
Feature-level unit tests, denominator/coverage tests, missingness stress tests, as-of reproducibility, and analyst-readable evidence cards. No opaque single-score footprint output.

## Priority 10 — walk-forward scenario and validation engine

### Evaluation design
- Chronological walk-forward folds only; freeze each training cutoff before evaluating the next period.
- Separate model development, calibration and final holdout periods.
- Purge/embargo overlapping outcome horizons.
- Compare against transparent baselines (no-change, market/index, simple momentum/mean-reversion and class-prior baselines as applicable).
- Evaluate separately by instrument, liquidity, market regime and coverage quality; report sample counts.
- Include realistic fees, taxes, slippage, spread/impact assumptions and turnover constraints for any tradability claim.
- Include survivorship-safe historical instrument universe and delisted/suspended lifecycle records where data supports it.

### Scenario outcomes
Define horizons and labels before running tests. Evaluate probability quality (Brier score, log loss, reliability/calibration curves), ranking/discrimination where relevant, directional accuracy, drawdown and net-of-cost returns only for strategies that are explicitly simulated. Confidence must be calibrated on data not used to fit the predictor.

### Mandatory negative tests
- Shuffle labels and future timestamps: performance should collapse to baseline.
- Inject a future-only feature: leakage detector must fail.
- Change late-arriving data: earlier point-in-time snapshots must remain unchanged.
- Remove broker identity coverage: broker-derived confidence should degrade or become unavailable.
- Perturb costs/slippage and exclude illiquid instruments: conclusions should disclose sensitivity.
- Compare against simple baselines and test multiple regimes to expose overfit.

### Release gate
No accuracy or profitability claim without reproducible fold definitions, immutable input snapshots, code/environment versions, baseline results, calibration, uncertainty intervals, costs and independent holdout. Publish failures and null results as well as wins.

## Cross-priority dependency and implementation order

| Priority | Build artifact | Hard dependency |
|---|---|---|
| 6 | Immutable capture + safe ingestion | Authorized source and captured fixtures |
| 7 | Broker identity registry + reconciled aggregates | Priority 6 raw lineage; authoritative broker mapping |
| 8 | As-of feature store | Priorities 6–7 plus security master/corporate actions |
| 9 | Explainable feature/episode layer | Verified sessions, universe, point-in-time features |
| 10 | Walk-forward scenario engine | Stable labels, immutable snapshots, baseline and costs |

Parallel work is permitted on schemas, validators and synthetic fixtures. Real-data features, model training and production activation remain gated by the unresolved calendar, universe, lineage, rights and coverage questions.

## Current implementation status

This file records the engineering contracts and acceptance criteria. It does **not** assert that these components have been implemented, tested against live exchange data, deployed, or approved for trading. The next implementation slice is Priority 6: add immutable raw-envelope and append-only/idempotency primitives with fixture-based tests, then Priority 7 identity tables and reconciliation.
