# Steps 46–47: mainline consolidation and historical-data pilot audit

**Audit date:** 2026-11-27  
**Baseline:** `main` at `c4d645cd566d931c31acaad5e78d46724e363311`  
**Scope:** repository state and evidence already committed to the default branch. This is an audit and gating record, not a production approval.

## Executive result

| Priority | Result | Status |
|---|---|---|
| Step 46 — mainline integration and dependency consolidation | Dependency-chain work is substantial, but the branch has diverged too far from `main` for a blind merge. A staged integration is required. | **Audit complete; code consolidation pending** |
| Step 47 — real NEPSE historical-data pilot | Several real/public datasets and official NEPSE captures exist, but their coverage and quality are fragmented. No market-wide, point-in-time, corporate-action-reconciled panel is proven ready for six-strategy OOS testing. | **Readiness audit complete; pilot admission blocked** |

The distinction is intentional: implementation commits and passing CI are not evidence of a completed market-wide dataset, validated strategy performance, live trading readiness, or profitable signals.

---

## Step 46 — mainline integration and dependency consolidation

### 46.1 Verified repository state

- Default branch: `main`; observed head SHA: `c4d645cd566d931c31acaad5e78d46724e363311`.
- The six-scanner dependency branch `historical-acquisition-unified-portfolio-risk` compares as **262 commits ahead / 56 commits behind** `main`, with **156 changed files** in the comparison.
- PR #237 (Steps 42–43) and PR #238 (Steps 44–45) are merged into the dependency chain, not into `main`.
- PRs #233, #235 and #236 are open drafts against `main`; none is the six-scanner integration.
- PR #235's latest observed head checks passed: backend-tests run 46047871461 and Backend contract tests run 46047871558.
- PR #233's observed backend-tests run 46047709350 passed.
- PR #236's observed backend-tests run 46048037096 passed. A second workflow was not present in the observed run list.
- Older IDPAT and historical pipeline PRs remain open on stacked/dependency branches. Their existence must not be mistaken for default-branch integration.

### 46.2 Why a bulk merge is rejected

The comparison includes a large set of new IDPAT, historical-data, six-strategy, replay, execution, risk and test modules, plus a modification to `backend/app/main.py`. Meanwhile `main` contains 56 commits not in the dependency branch. A merge of the entire branch would combine unrelated historical-data, lifecycle, scanner and portfolio work and risks overwriting or bypassing newer mainline safeguards.

**Decision:** do not merge the dependency branch wholesale and do not retarget its large stacked PR chain to `main`.

### 46.3 Safe integration sequence

1. Keep the strict historical segment eligibility port in PR #235 as the current mainline candidate. Require independent review of its evidence-host allowlist, caller compatibility and fail-closed UNKNOWN states before merge.
2. Review PR #233 (official positive-session overlap) and PR #236 (44 populated lifecycle records) as separate evidence/documentation changes. Neither should promote unverified dates or lifecycle starts.
3. Create one fresh integration branch from the then-current `main`. Port only a coherent vertical slice at a time: shared evidence contracts and source adapters; IDPAT/strategy engines; historical features and point-in-time replay; trade plan/risk; portfolio execution/mark-to-market.
4. For each slice, preserve existing `main` behavior, add import/API compatibility tests, run all applicable CI, and record exact source/head SHAs. Do not use a passing test suite from a dependency branch as proof that the mainline integration passed.
5. Integrate only after each slice is reviewed and its full dependency closure is present. Keep research-only and production-disabled flags intact.

### 46.4 Definition of done

- A main-based integration branch contains the required modules and tests with no unresolved duplicate implementations.
- Main application/API wiring calls the intended integrated pipeline, not isolated demo functions.
- Full CI passes on the final integration head.
- A dependency inventory confirms every imported module, test fixture and runtime configuration is included.
- No production or trading authorization is inferred from the integration.

---

## Step 47 — real historical-data pilot readiness

### 47.1 Existing dataset evidence on `main`

The committed `docs/DATA_SOURCES.md` records the following measured inventories and QA. These are source-specific results; do not combine them into one supposedly homogeneous dataset.

| Source/table | Recorded coverage or size | Recorded QA / limitation | Pilot disposition |
|---|---:|---|---|
| Ankit `eod_history_ext` | 516,620 rows; 1995-07-20 to 2026-08-19 | 40,373 OHLC anomalies (about 7.82%); no matching source quality flag | **Quarantine from raw-candle pattern analysis pending row-level review** |
| Ankit `eod_price` | 93,859 rows; 2025-08-19 to 2026-11-20 | 578 close-outside-range rows, all source-flagged | **Keep source flags; investigate before canonical admission** |
| Ankit `floorsheet` | 330,978 rows; 2026-08-19 to 2026-11-20 | Zero duplicate trade keys, invalid trade values or material quantity × rate mismatches in recorded QA | **Candidate for bounded floorsheet pilot, source-separated** |
| Ankit `broker_flow_daily` | 81,418 rows; 2026-08-19 to 2026-11-20 | Arithmetic and business-key checks passed; broker codes remain execution-channel IDs, not beneficial owners | **Candidate for descriptive broker-flow research only** |
| Ankit `bars_1m` | 114,537 rows; 2026-08-19 to 2026-11-20 | Zero duplicate bar keys and OHLC range violations in recorded QA | **Candidate for bounded intraday research; verify session completeness** |
| Ankit warehouse total | 306 files; 1,139,853 rows across six separate tables | Source tables have different coverage and semantics; warehouse artifact is not permanently stored in Git | **Not a single canonical panel** |
| Urek floorsheet archive | 603 files; 2024-01-02 to 2026-08-26 | 2024-01-02 smoke test: 85,435 rows accepted, zero rejected; only one session tested | **Broader ingestion and session-by-session audit required** |
| Urek sector indices | 6,429 files; 1997-07-20 to 2026-08-26 | Same one-session smoke test accepted 16 index rows; full coverage not validated | **Candidate after calendar and per-file validation** |
| NEPSE official security-history capture | 7 symbols; 22 responses; 8 conflict records | API, HRL and RHGCL history responses require review (18, 18 and 228 rows); BGWT, MEHL, RAWA and ULHC returned valid empty responses in their queried windows | **Not broad enough for market-wide history; empty is UNKNOWN, not zero trades** |

### 47.2 Cross-source reconciliation warning

The Ankit EOD tables have 75,671 overlapping symbol/date records from 2025-08-19 to 2026-08-19. The recorded comparison reports exact volume agreement on all 75,671 records and exact close agreement on 75,657; 14 close mismatches remain, with a maximum absolute difference of NPR 60. The cause is unresolved. Keep the tables separate and quarantine the mismatches until independently explained.

The official NEPSE capture report dated 2026-11-25 records eight conflicts. It is useful raw evidence, but its seven-symbol sample and mixed empty/review-required history responses cannot establish a complete security universe or market-wide history.

### 47.3 Pilot admission gates

A real-data pilot must not begin six-strategy OOS scoring until all of the following are satisfied for the selected sample:

1. Raw files/responses are retained unchanged with source, retrieval time, exact URL or dataset version, rights basis and verified SHA-256.
2. Every row has a stable security identity and effective-dated lifecycle; delisted, suspended, successor and IPO histories are represented without survivorship leakage.
3. Session dates are reconciled to an evidence-backed exchange calendar. Missing bars and verified no-trade sessions remain distinct.
4. OHLCV has duplicate, numeric, bounds, timestamp, availability-cutoff, volume/turnover and outlier checks; anomalies are quarantined, not silently repaired.
5. Corporate actions are reconciled from independent evidence with explicit adjustment factors and effective dates. Raw and adjusted series remain distinct.
6. Floorsheet, broker-flow and sector data remain source-separated and are joined only with valid keys and matching time windows. Broker codes are not interpreted as beneficial ownership.
7. The admitted panel has sufficient contiguous causal warm-up for each horizon, and all features are computed as of the decision timestamp.
8. A readiness report identifies coverage by security, session, source and field. Any critical missing coverage blocks the affected security/horizon; missing optional feeds remain missing, not neutral.
9. The same admitted panel, costs, execution assumptions and sample partitions are used across all six strategies. Final performance assessment is OOS-only and execution-aware.

### 47.4 Recommended bounded pilot

Start with a **small, explicitly named cohort** and a recent overlapping window where official NEPSE records, a secondary EOD source, session calendar, corporate-action evidence and floorsheet can be reconciled. Do not choose symbols because their later performance is known. Include both liquid and less-liquid securities and retain failed/insufficient cases in the audit.

The first pilot output should be a data-readiness and reconciliation report, not a BUY list or strategy leaderboard. Only after the cohort passes admission should it feed historical feature snapshots and six-strategy walk-forward replay.

### 47.5 Current decision

**Pilot status: BLOCKED for market-wide strategy validation; bounded source-specific ingestion is permissible.**

Reasons:
- the long Ankit EOD history contains unresolved OHLC anomalies;
- the 2025–2026 EOD overlap has 14 unresolved close mismatches;
- the Urek end-to-end normalization evidence is one session, not full-archive validation;
- the official NEPSE security-history sample is only seven symbols and has eight conflicts;
- full point-in-time lifecycle, calendar and corporate-action reconciliation has not been demonstrated for one common panel;
- broker and sector evidence coverage is not yet aligned to the same historical window.

No win rate, profit factor, expectancy, accuracy, calibrated probability or live BUY/SELL recommendation may be claimed from these inventories.

---

## Next execution queue

1. Finish independent review of mainline PR #235 and its callers; keep #233 and #236 as separate review units.
2. Build a fresh main-based scanner integration branch with a single vertical slice and full CI.
3. Produce a bounded, source-separated historical pilot bundle and machine-readable readiness report.
4. Reconcile the 14 EOD close mismatches and the flagged historical OHLC rows before admitting affected bars.
5. Expand official NEPSE security-history capture across the selected cohort, preserving conflicts and empty responses as unresolved evidence.
6. Only then run six-strategy OOS replay and compare execution-adjusted outcomes.

**Safety boundary:** research only; production remains disabled. No data-quality audit or passing CI run authorizes live trading.


---

## Recheck addendum — 2026-11-27 19:24 UTC

A later repository refresh supersedes the original comparison snapshot above:

- Current `main` head: `4840fc0b16926bd53c6c3cc9321a4baa5aadec39`.
- The dependency branch `historical-acquisition-unified-portfolio-risk` remains **262 commits ahead / 80 behind**, with **156 changed files**. The behind count increased from 56; bulk integration remains unsafe.
- PR #239's documentation-only audit head had backend-tests run `46052188530` pass, but no second contract workflow was observed. PR #239 remains open/draft and is not merged.
- PR #233 remains open/draft and currently reports `mergeable=false`; PR #235 and #236 remain open/draft and report `mergeable=true`. All three were created against the earlier mainline baseline and require a fresh review against current `main`.
- The 616-session cross-check report records 616 candidate dates, 224 with official market-summary observations inside its one-year coverage window, 392 before that coverage window, and a decision of `review_only_no_calendar_promotion`. This does not authorize promotion of candidate dates into the canonical session calendar.
- The official 2026 holiday evidence records 40 verified closed dates plus one exceptional closure, but zero verified open dates. Absence from the holiday API is not evidence of an open session.

The 18-symbol 2025 lifecycle cohort has since been added in PR #242 with a structural validator. It remains secondary-source/archive evidence only; 17 matching boundaries are candidates for further review and SAIL remains quarantined. PR #242's final observed backend suite passed 1,398 tests, and its historical-integrity workflow passed. It is open/draft, not merged.

This addendum is the current audit snapshot. It does not change the original research-only, non-promotable disposition.
