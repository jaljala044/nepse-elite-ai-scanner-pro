# Steps 50–51 — official first-trade proof and historical pilot admission

**Baseline main:** `fe61ae040b31c81df283f87dcd91642f78abb30e`  
**Pilot:** 18-symbol 2025 lifecycle-start cohort  
**Disposition:** research-only; no canonical or backtest promotion

## Step 50 — contract-level first-trade verification

Added `data/reference/nepse_first_trade_floorsheet_evidence_pilot_2025.csv` and `backend/app/first_trade_floorsheet_evidence.py`.

The register preserves the current 18 lifecycle candidates and permanent security IDs. It records all 18 as `pending_official_contract` because the repository does not contain contract-level official floorsheet proof for these dates. It does not mislabel secondary reporting or a positive-volume archive row as an exchange contract.

A record can reach `verified_contract_match` only when it includes:
- official NEPSE floorsheet source ID and HTTPS source reference;
- raw response SHA-256;
- contract identifier;
- exact first-trade date and contract quantity at least the archive first-row volume;
- UTC verification timestamp;
- matching reported and archive first-row dates.

SAIL remains quarantined because the reported first trade (2025-11-23) and archive first row (2025-11-24) differ. It cannot be promoted by the validator even if a purported contract record is added; the date-boundary conflict must first be separately resolved and the derived price panel versioned.

The validator checks evidence structure; it does not fetch, cryptographically authenticate or independently certify publisher responses.

## Step 51 — per-security historical panel admission

Added `backend/app/historical_pilot_panel_admission.py`. A symbol is blocked unless it has:
1. contract-level first-trade verification;
2. effective-dated security identity;
3. complete evidence-backed session calendar coverage;
4. clean OHLCV with raw SHA-256 and zero unresolved anomalies;
5. corporate-action reconciliation supported by at least two independent sources with no unresolved events.

Missing data blocks admission. It is never scored as neutral or treated as clean.

Panel admission and horizon warm-up are separate. Minimum history thresholds are currently explicit engineering floors: T+2 5 sessions, swing 20, positional 60, investment 200. Passing them is not statistical sufficiency or a BUY signal.

## Tests and actual pilot status

Regression tests cover official-source provenance, raw digest, contract ID/date/quantity, secondary-source rejection, SAIL mismatch, missing evidence, calendar gaps, OHLCV anomalies, corporate-action conflicts and horizon warm-up.

The committed real cohort currently has **0/18 official contract matches** and **18/18 pending**. Therefore this pilot remains blocked from canonical promotion and backtest admission. No data rows are synthesized or altered.

## Next requirements

- Capture complete official floorsheets for the 18 first-trade dates and retain raw bytes, retrieval metadata and hashes.
- Independently resolve SAIL's 23/24 November boundary.
- Build per-symbol expected-session coverage from an evidence-backed calendar.
- Verify lifecycle identity and corporate actions for each selected symbol.
- Reconcile raw OHLCV against official and independent sources; quarantine unresolved discrepancies.
- Only after the admission report is ready should the selected panel enter six-strategy OOS replay.


## Final CI and repository recheck — 2026-11-27

- Main baseline at branch creation: `fe61ae040b31c81df283f87dcd91642f78abb30e`.
- Final implementation/test head: `ef79f58625aed5f65ebe4f4f4fb0058e6ece1522`.
- Backend unit-test workflow run `46057008131`: **success**.
- NEPSE historical data integrity workflow run `46057008217`: **success**.
- The first test attempt exposed an incorrect expected blocker count; the assertion was corrected, and the final workflows passed on the strengthened implementation.
- Final observed PR #244 state: open, draft, mergeable, not merged. The implementation branch compares as 10 commits ahead and zero behind current `main`.
- The latest validator additionally checks security-ID joins, effective-date validity, first-trade inclusion in verified open sessions, calendar and OHLCV provenance, and two distinct corporate-action evidence sources with raw hashes.
- The cohort's actual evidence state remains 0/18 official contract matches and 18/18 pending. CI validates implementation and regression tests, not external market evidence.

No canonical dataset, backtest eligibility, training permission or production trading authorization is enabled.
