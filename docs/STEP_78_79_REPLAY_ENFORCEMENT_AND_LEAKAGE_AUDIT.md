# Steps 78–79 — Replay enforcement and point-in-time leakage audit

## Step 78 — enforced replay handoff
- Introduce one orchestrator that runs the Step-77 dataset admission, a per-observation leakage audit, the existing explicit human research replay approval, and only then the existing 24-run replay adapter.
- The replay adapter is never invoked for a blocked dataset, mismatched fingerprint, non-OOS partition, failed leakage audit, or absent human approval.
- All six scanners and four horizons receive one identical manifest fingerprint; partial runs remain explicitly incomplete.
- Replay remains research-only; no production activation, canonical promotion, or probability calibration.

## Step 79 — leakage regression suite
- Check each observation's decision timestamp against every feature and source availability timestamp.
- Require outcome labels to be delayed until the outcome window is complete; reject labels embedded in feature records.
- Reject missing timestamps, duplicate observation IDs, duplicate/missing feature IDs and future information.
- Regression tests cover the clean path, late features, early labels, duplicated observations, missing provenance, fingerprint mismatch and absent approval.

## Boundaries
Synthetic tests only. This does not authenticate publishers, prove feature calculations, or establish exchange-wide historical completeness. The injected runner still needs independent validation for NEPSE commissions/taxes, fills, liquidity, settlement, circuit/no-bid and stop execution. No live historical data was acquired or replayed by these tests.
