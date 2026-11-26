# Broker Behaviour Memory and Early Entry/Exit Intelligence

**Status:** mandatory product requirement; architecture and implementation plan  
**Applies to:** NEPSE AI web application, mobile application and shared backend  
**Owner decision recorded:** 2026-11-26  
**Related product issues:** [#85 Portfolio Intelligence](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/issues/85), [#86 Product roadmap](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/issues/86)

## Product objective

NEPSE AI must continuously observe eligible broker-wise floorsheet execution behaviour, preserve historical pattern memory, and use point-in-time comparisons to identify explainable **potential early-entry and early-exit conditions**. This is a foundational NEPSE-native intelligence capability shared by the scanner and portfolio assistant, not an optional dashboard decoration.

The system must remember what has been observed for each broker execution code/entity candidate, stock, sector and market context, then compare current activity with daily, weekly, monthly and yearly histories. Longer horizons must be explicitly marked unavailable when the history or evidence is insufficient.

## Observation horizons and memory

Maintain session-aware, rolling and calendar-aligned aggregates where evidence supports them:

- **Daily / 1D:** per-session buy/sell quantity and value, net flow, gross participation, market share, concentration, repeat activity and changes versus the broker's prior baseline.
- **Weekly / 1W:** repeated participation, multi-session persistence, broker-stock relationship changes, net-flow consistency and short-term rotation.
- **Monthly / 1M:** sustained activity, recurring stock preferences, concentration changes, sector rotation and reversals.
- **Yearly / 1Y:** long-term recurring tendencies and regime-conditioned patterns, with explicit coverage and no extrapolation beyond available history.
- Preserve useful intermediate horizons (3M, 6M, 2Y) when supported by complete, eligible history; they complement rather than replace the required daily/weekly/monthly/yearly views.

A horizon is not considered complete merely because a number of calendar days has elapsed. Use verified NEPSE session dates and expected coverage. Distinguish missing feed, incomplete floorsheet, no trade, suspension, non-session and unknown status.

Persist reproducible observations and derived features with:
- source/evidence IDs, payload hashes and row lineage;
- trade/session date, event time only when supplied, publication/availability time, retrieval time and calculation time;
- source and parser versions, feature-code version and parameter set;
- observed sessions, expected sessions, coverage, unresolved identity/value share and reconciliation status;
- first/last observation, sample size, lookback and as-of cutoff;
- supersedes/revision links without overwriting earlier point-in-time results.

## What the memory learns

For each broker code (and verified broker entity only when supported), stock, broker-stock pair, sector and market context, retain:
- buy/sell quantity, amount/turnover, net quantity/value and gross participation;
- active-session frequency, participation share, buy/sell streaks and recurrence;
- rolling-window flow direction, intensity, acceleration/deceleration and changes versus the broker's own historical baseline;
- concentration and changes in the top participating execution channels;
- broker-stock relationship persistence, appearance/disappearance and changes in participation;
- possible stock/sector rotation and unusual activity relative to comparable NEPSE market regimes;
- estimated accumulation/distribution and possible early reversal/unwind behaviour, always labelled as inference rather than observed ownership;
- subsequent historical outcomes, failed patterns and false positives for calibration.

## Candidate early-entry and early-exit detection

Implement deterministic, versioned and independently testable rules before AI interpretation. Candidate conditions to test (not assume) include:

- **Early-entry candidate:** repeated verified net-buy participation or rising broker participation share across sessions, before material price expansion, with adequate floorsheet coverage and supportive or explainable NEPSE index/sector/breadth/liquidity context.
- **Early-exit risk:** sustained weakening of previously persistent buyers, growing selling participation, reversal of broker-stock flow patterns, concentration unwind or price/volume divergence while price remains elevated.
- **Rotation watch:** historically active execution channels reduce participation in one group of stocks while increasing in another, with adequate cross-sectional coverage.

Do not equate broker buyer-side observations with market-wide net demand: every contract has both buyer and seller sides. Show gross buys, gross sells, broker-level net flow and concentration separately. Any directional breadth statistic must explain its definition and limitations.

Each result must carry:
- status such as `WATCH`, `EARLY_ENTRY_CANDIDATE`, `EARLY_EXIT_RISK` or `INSUFFICIENT_EVIDENCE`;
- exact as-of date/time, selected horizon and observed/expected sessions;
- triggering broker codes/entities, stock(s), quantities, values, participation shares and baseline comparisons;
- NEPSE Index, Sensitive Index, Float Index, Sensitive Float Index, sector index, breadth, turnover, liquidity, price/volume, circuit/price-limit and corporate-action context where eligible;
- evidence references, source, freshness, coverage, sample size, unresolved/conflicting input details;
- rule/version, calibrated confidence only where walk-forward evidence supports it, historical outcomes and known false-positive rate;
- clear separation of observed facts, deterministic detection, statistical inference and AI-generated explanation.

No signal is a guaranteed prediction or automated trade instruction. BUY/SELL/HOLD and any entry/exit/stop/target levels remain subject to the platform's existing upstream data eligibility and risk gates.

## NEPSE-native context

Do not transplant international-market thresholds or assumptions without validation against NEPSE history. Evaluate patterns in the context of local session/calendar rules, price/circuit limits, liquidity and turnover conditions, NEPSE Index and sub-indices, sector indices, market breadth, instrument lifecycle and verified corporate actions. The same broker behaviour may have different meaning in different NEPSE market regimes.

## Identity, source and integrity boundaries

- Broker numbers/codes are execution-channel identifiers. A floorsheet does not prove the broker's proprietary position, beneficial owner, client identity, holdings or intent.
- Use verified effective-dated entity mappings only where documentary evidence supports them. Keep unknown, ambiguous and unmapped codes separate and visible.
- Accumulation, distribution, cornering, manipulation and intent are estimates/hypotheses unless independently established; never present them as proven facts from broker codes alone.
- No fabricated broker identity, missing history, source, session, timestamp, intent, yearly pattern or signal.
- Fail closed for unverified session dates, incomplete or unreconciled floorsheets, inadequate coverage, unresolved source rights, stale inputs, conflicting rows or insufficient history.
- Do not promote quarantined/provisional evidence into production recommendations.
- Preserve raw bytes and immutable lineage; all derived features must be point-in-time and no-lookahead. A historical replay for date T may use only information demonstrably available at T.
- Do not use public Git as a store for large/private/licensed raw market data or secrets.

## Shared web and mobile contract

The backend is the single authority for broker observations, memory, horizon calculations, detections, confidence and provenance. Web and mobile must consume the same versioned API schemas and display the same values and status. No independent client-side P&L, broker-flow, horizon, score or signal calculations.

Required UI surfaces:
1. **Broker Behaviour Explorer:** searchable broker code/entity, stock, sector and market filters; daily/weekly/monthly/yearly horizon tabs; activity timeline, participation, net flow, concentration and source coverage.
2. **Stock Broker Footprint:** broker participation ranked by horizon, historical repeat behaviour, changes in flow and broker-stock memory.
3. **Early Entry / Exit Watchlist:** candidate status, trigger explanation, market/sector context, evidence drill-down, freshness and invalidation conditions.
4. **Portfolio integration:** explain how eligible broker-flow patterns affect a user's existing holdings and risk watchlist without asserting ownership or intent.
5. **Beginner and professional modes:** plain-language explanations for beginners; detailed quantities, values, filters, coverage, history and evidence lineage for professionals.

All surfaces must provide loading, empty, stale, partial-coverage, conflict and unavailable states. Never render missing data as zero or a reassuring neutral signal.

## Delivery sequence

1. **Preserve current engineering gates.** Do not interrupt stacked P4.28/P4.29/P4.30 PR chain #81–#84. Continue P4 deployment durability. Keep P1 historical evidence, session, floorsheet coverage, source rights and identity gates fail-closed.
2. **Backend contract and persistent memory:** inspect/reuse existing `broker_aggregation.py`, `footprint_features.py`, `floorsheet_broker_join.py`, `feature_pipeline.py` and historical evidence vault. Do not create a duplicate parser or bypass current evidence admission rules. Define versioned observation/profile schemas and durable storage/migrations.
3. **Horizon calculations and history:** validate daily/weekly/monthly/yearly windows against verified NEPSE sessions and completeness. Add broker-stock histories, baseline deltas, persistence and pattern lifecycle with deterministic fixtures.
4. **Candidate detection and validation:** define deterministic early-entry/exit rules, run prefix-invariance/no-lookahead tests, replay historical eligible periods, measure outcomes and false positives, and calibrate only with sufficient independent evidence.
5. **Shared APIs:** expose read-only, authenticated, user-safe endpoints for broker profile, stock footprint, horizon history and candidate watchlist. Enforce per-user portfolio privacy for personalized outputs.
6. **Web and mobile:** build the four shared surfaces against the same backend contracts. Do not claim either client is delivered until code, tests and CI are present.
7. **Operational release:** require persistent hosting, database migration, backup/restore, monitoring, authorization, source refresh schedule and recovery drills before live continuous memory is claimed.

## Acceptance criteria

- Daily observations are reproducible from eligible, reconciled evidence and retained with immutable provenance.
- Weekly/monthly/yearly profiles derive from the same observation history and display expected/observed session coverage and minimum-sample gates.
- Broker-stock memory survives application restarts and supports as-of queries and historical replay.
- Early-entry/exit candidates are explainable, versioned and include triggering evidence, baseline, context, freshness, coverage and limitations.
- Backtests/replays are strictly point-in-time, prefix-invariant and record false positives as well as successful outcomes.
- Tests cover incomplete/missing sessions, no-trade vs missing feed, duplicate/conflicting rows, source-rights holds, broker-code changes/unmapped identities, corporate actions, stale inputs, short history and regime changes.
- Web and mobile show identical backend-calculated values and evidence status.
- No live/production/continuous monitoring claim until authorized source feeds, durable hosting and scheduled ingestion are actually connected and verified.

## Current implementation facts (do not overstate)

The repository already contains broker party aggregation, floorsheet identity joins, descriptive footprint feature primitives, broker/SMC confluence research code and broker coverage reports. The footprint function currently has rolling windows and a 1D/1W/1M/3M persistence concept, but it is not proof of durable historical memory, a calibrated early-entry/exit engine or production data access. The README currently states that live API feeds, web UI, Android app, authentication, deployment and scheduled automation are not yet connected or verified.

This document records mandatory scope and an implementation plan. It does not claim that broker memory, early-entry/exit detection, a web UI, a mobile app, live ingestion or production deployment have been implemented.


## First backend implementation slice (PR #87)

The first backend foundation is now committed on `feat/broker-behaviour-memory-early-entry-exit`:
- append-only DuckDB tables for source-lineaged broker observations and immutable, content-addressed as-of snapshots; rows are rejected unless source rights are cleared for research use (`research_only`, `internal_use` or evidence-backed `redistribution_permitted`);
- cumulative rebuild from all previously stored observations that were available at the decision time;
- daily, weekly, monthly and yearly broker-flow windows, with additional 3M/6M/2Y descriptive windows in the underlying feature primitive;
- separate execution-channel-code profiles, including unmapped codes, without promoting them to verified broker entities;
- 20-session buy/sell baselines, daily activity acceleration ratios and a 21-session daily execution-channel timeline for each code; buyer and seller party observations from the same contract row are kept distinct by side in immutable lineage;
- a fail-closed, explicitly uncalibrated research-rule evaluator for early-entry/early-exit candidates, requiring complete 1D/1W/1M broker windows and verified NEPSE price/index/sector/breadth/liquidity/circuit/corporate-action context;
- read-only shared API endpoints `GET /v1/broker-memory/status`, `GET /v1/broker-memory`, `GET /v1/broker-memory/patterns` and paginated `GET /v1/broker-memory/lineage` evidence drill-down;
- a responsive web broker-memory explorer consuming the shared API, including 21-session timelines, early-pattern states and paginated source/rights lineage drill-down;
- tests for idempotency, cross-session memory, no-lookahead availability, source/session/floorsheet admission, lineage, short yearly history, execution-code-only behaviour and fail-closed candidate rules.

**Session input contract:** the `session_dates` supplied to the persistence layer must contain only verified NEPSE open sessions for which complete floorsheet coverage has been established and made available by the decision time. Future sessions are excluded. A mere exchange calendar is not enough to claim floorsheet coverage.

A first responsive **web broker-memory explorer** is also now present in the frontend and consumes the shared read-only API. This is not yet a complete web product surface, and no mobile client source tree was present in this repository; mobile implementation remains outstanding. The candidate evaluator is callable during snapshot creation when a separately verified per-symbol NEPSE market-context bundle is supplied, but no verified context producer currently feeds it automatically. It is not yet connected to a continuously refreshed API watchlist or production scanner output, and is not calibrated against historical NEPSE outcomes. This slice does not connect an automated source collector or scheduler, or certify production operation. It is not a live broker monitor. Existing P4 durability and P1/P2 evidence/source-rights gates remain mandatory.
