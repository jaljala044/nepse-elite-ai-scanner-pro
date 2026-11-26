# Current-universe successor ID policy — 2026-11-26

## Decision

Project-owner instruction: use the **2026-11-25 current security-ID snapshot** as the canonical identity source for the current equity scanner. Former merger/acquisition tickers are retired aliases and are not required to have historical IDs recovered for current-universe scanning.

This is a scoped current-universe decision. It does **not** assert that a successor ID was historically assigned to a predecessor, establish predecessor validity intervals, or authorize historical OHLCV/floorsheet splicing.

## Current successor identity register

Source file: `data/reference/nepse_security_id_snapshot_2026-11-25.csv`

Snapshot date: 2026-11-25  
Snapshot source-blob SHA-256: `eed3bbb3152e83d4abcb0ee8d03d720c33c63cef`  
Repository CSV blob SHA: `ed548857eb550fbb237910eb903fc202751c63a1`

| Current successor symbol | Current snapshot security ID | Retired former ticker(s) | Snapshot status | OHLCV file present |
|---|---:|---|---|---|
| SLBSL | 2804 | BPW | A | yes |
| NMLBBL | 396 | MMFDB, NLBBL | A | yes |
| MATRI | 694 | JALPA, KLBSL | A | yes |
| SMATA | 2761 | MKLB | A | yes |
| SMPDA | 2896 | SABSL, SDLBSL | A | yes |
| GBLBS | 583 | SAMAJ | A | yes |
| PFL | 236 | SFCL | A | yes |

The numeric IDs, names, active status, snapshot date and OHLCV-presence flags above are copied from the dated snapshot. They are **current snapshot observations**, not historical predecessor-ID evidence.

## Scanner implementation rules

1. Resolve current instruments by exact current symbol + current snapshot security ID. Do not use a former ticker as a current instrument key.
2. Treat the former symbols in the table as retired aliases for lifecycle/reference display only. Exclude them from active current-equity scan output and current watchlists.
3. Use the successor's current ID for current-data joins only where the source row is itself for the successor symbol and the date is within the successor data's supported scope.
4. Preserve predecessor OHLCV and floorsheets as separate raw historical records. Do not concatenate or silently map them into successor price series.
5. Do not calculate continuous returns, moving averages, relative strength, Wyckoff structures, broker footprints, backtests or training labels across predecessor/successor boundaries unless a separately reviewed corporate-action adjustment and point-in-time identity mapping explicitly supports that calculation.
6. A missing predecessor ID is no longer a blocker for current-universe scanning. Historical identity recovery remains a separate optional research task, not a current-universe release requirement.
7. Do not use current security IDs to infer historical IDs. No ID backfill is permitted.
8. Mutual funds remain outside this equity-only scan scope, including NICEF as previously instructed by the project owner.

## Acceptance status

- Current successor identity mapping: **7/7 mapped from the 2026-11-25 snapshot**.
- Current scan use of successor IDs: **approved by project-owner instruction**, subject to existing data-quality, lifecycle, source-provenance and release gates.
- Former ticker current-universe inclusion: **excluded**.
- Historical predecessor ID recovery: **not required for current scanning; unresolved for historical research**.
- Historical price/floorsheet splicing: **not authorized**.
- Canonical/training promotion: **not implied**; all existing integrity, calendar, provenance, rights and test gates remain in force.

## Provenance and limitations

The snapshot is a point-in-time third-party/current catalogue artifact already retained in the repository. Its source-blob SHA is recorded in the CSV. This decision does not independently certify the upstream exchange origin, complete equity membership, or all instrument classifications. Keep the snapshot date attached to every ID use and refresh/version the snapshot when the current security master changes.

## Related evidence

- Historical merger/lifecycle evidence: `data/reference/nepse_historical_identity_evidence_2026-11-26.json`
- Historical security-ID source audit: `docs/PRIORITY_98_HISTORICAL_SECURITY_MASTER_SOURCE_AUDIT_2026-11-26.md`
- Progress register: `docs/NEPSE_AI_MASTER_PROGRESS_REGISTER_2026-11-25.md`
