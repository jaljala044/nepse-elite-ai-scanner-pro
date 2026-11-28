# Steps 50–51 — official lifecycle verification and point-in-time panel readiness

**Base:** Steps 48–49 bounded lifecycle pilot at dcc38cb897db730f9a4f4129c131f692f66dfde3.  
**Scope:** deterministic validators only. No official NEPSE/CDSC payloads were available or fabricated.

## Step 50 — official first-trade verification

Added backend/app/historical_pilot_verification.py. It accepts only explicitly typed official NEPSE floorsheet or CDSC records and requires contract ID, permanent security ID, source-record ID, raw-byte SHA-256, finality, verified status, positive quantity/price, and timezone-aware capture/availability timestamps. Evidence available after the decision cutoff is rejected. The earliest official contract date is matched to the cohort's reported first-trade date. Missing records and date conflicts remain unresolved; secondary-provider evidence is rejected.

**SAIL remains unresolved** until a captured official contract-level record establishes whether 23-Nov-2025 or 24-Nov-2025 was the first execution. Unit-test fixtures are synthetic and are not evidence about SAIL.

## Step 51 — panel readiness

Added backend/app/historical_pilot_panel.py. It requires unique permanent security identities with effective dates, an evidence-backed confirmed-open session list, valid OHLCV, unique symbol/session keys, raw SHA-256 format, lifecycle membership, point-in-time availability, complete symbol/session bars, and an externally supplied clean corporate-action reconciliation report. It returns READY_FOR_BOUNDED_RESEARCH or BLOCKED with explicit errors and missing rows.

Even READY is not canonical promotion or backtest authorization. It is only a bounded research panel gate. It does not establish source completeness, market representativeness, broker/sector alignment or exchange-wide session completeness.

## Current evidence state

The existing 18-row cohort remains secondary-source evidence. No official first-trade records, authoritative session panel, complete OHLCV panel or new corporate-action reconciliation report were added. Therefore no actual pilot panel is declared READY, no six-strategy OOS backtest is admitted, and production remains disabled.

## Required external evidence

1. Capture official first-day floorsheet contracts for all 18 securities, with permitted access, response bytes, capture timestamp and SHA-256.
2. Resolve SAIL using the official record; preserve unresolved if unobtainable.
3. Obtain permanent security IDs and lifecycle intervals from an authoritative source.
4. Supply evidence-backed expected sessions and raw OHLCV per active symbol/session.
5. Reconcile corporate actions and source completeness before considering bounded OOS replay.
