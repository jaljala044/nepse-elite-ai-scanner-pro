# IDPAT-13 — 120-session historical OHLCV coverage validation

## Delivered
- Validates a configurable rolling window, default 120 verified exchange trading sessions, not calendar days.
- Recomputes the reconciliation-ledger SHA-256 and checks its research-only promotion policy.
- Joins stable security IDs against verified session dates and cross-source reconciled OHLCV.
- Rechecks per-row OHLCV validity, source IDs, source hashes, independent-source lineage and source point-in-time timestamps.
- Reports per-security coverage, missing sessions, overall coverage and first/last session; no missing bar is filled or inferred.
- Requires an explicit corporate-action review for every security, with verified no-action or verified-adjusted status, evidence lineage, cutoff timestamp and matching adjustment basis.
- A default 98% coverage threshold is configurable. Even a complete result is research-review only; production promotion remains false.

## Important limitation
- The validator consumes a verified session calendar, a reconciled ledger, source-evidence metadata and corporate-action review records. It does not fetch or manufacture these artifacts.
- Synthetic fixtures test logic only; they do not establish actual 120-session NEPSE coverage or actual corporate-action status.
