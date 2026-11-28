# Steps 48–49 — bounded historical lifecycle pilot and admission validator

**Baseline:** `main` at `4840fc0b16926bd53c6c3cc9321a4baa5aadec39`  
**Cohort:** 18 equities from the documented 2025 lifecycle-start review  
**Purpose:** test lifecycle boundary evidence handling, not produce a price panel or trading signals.

## Step 48 — cohort selection

The cohort is the 18-symbol 2025 lifecycle-start set already documented in `docs/P4_11_3_2025_LIFECYCLE_START_COHORT_2026-11-26.md`. It is selected because each symbol has a documented first-trade report and a directly observed pinned-archive first row. This is a lifecycle-boundary pilot only; it is not designed to represent market-wide sector or liquidity distributions.

- 17 rows have matching reported first-trade and archive first-row dates.
- SAIL remains quarantined: secondary sources report 2025-11-23, while the pinned OHLCV archive begins 2025-11-24.
- HIMSTAR and TTL retain the actual executed first-trade dates after their scheduled unmatched sessions.
- All 18 rows are explicitly labelled secondary-provider plus archive observation. None has contract-level NEPSE floorsheet proof in this cohort.

The CSV `data/reference/nepse_lifecycle_pilot_cohort_2025.csv` preserves the dates, first-row volumes, evidence tier, disposition and exceptions. It does not invent or synthesize a missing SAIL bar.

## Step 49 — fail-closed validator

`backend/app/historical_pilot_cohort.py` validates:
- exact cohort size and required fields;
- unique uppercase symbols;
- canonical ISO dates and positive first-row volume;
- allowed evidence tier and dispositions;
- matching dates for candidate rows;
- explicit date mismatch for quarantined rows.

The result is deliberately non-promotable:
- `exchange_execution_verified = false`
- `canonical_promotion_allowed = false`
- `backtest_admission_allowed = false`
- `production_enabled = false`

Regression tests cover the committed cohort, SAIL mismatch preservation, candidate mismatch rejection, duplicate/count rejection and invalid disposition rejection.

## Still required before any six-strategy OOS replay

1. Obtain contract-level official floorsheet evidence for each selected first trade where available.
2. Verify permanent security IDs and effective-dated lifecycle, including predecessor/successor and delisted states.
3. Reconcile every expected session against authoritative calendar evidence; distinguish no-trade from missing data.
4. Verify raw OHLCV bytes/hashes and resolve anomalies and cross-source close mismatches.
5. Reconcile bonus, rights, splits, mergers and other corporate actions with explicit effective dates and factors.
6. Align benchmark, sector and broker evidence to the same point-in-time window.
7. Run per-security/per-field readiness and coverage reports; keep incomplete securities/horizons blocked.

**Result:** a bounded 2025 lifecycle cohort and structural validator are implemented. This is not a market-wide backtest-ready dataset, does not verify beneficial ownership, and creates no BUY/SELL eligibility.
