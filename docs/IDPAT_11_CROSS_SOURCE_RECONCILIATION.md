# IDPAT-11 — Cross-source canonical reconciliation ledger

## Delivered
- Retains normalized OHLCV values and raw-row line references from Step 10 admission reports.
- Joins records by stable security ID and verified session date, not ticker text alone.
- Requires source validation, approved rights, finality, point-in-time availability, raw hash and reviewer-approved independent-source group.
- Exact observations across independently reviewed source groups become cross-source reconciled research-only rows.
- Conflicting values are quarantined with both source observations; no automatic source winner is selected.
- One source, or multiple sources sharing one independence group, is insufficient for independent corroboration under the default policy.
- Missing expected security/session pairs remain explicit.
- Builds a deterministic SHA-256 ledger and persists it content-addressed and idempotently.

## Safety boundaries
- Matching values do not prove independence; independent lineage is a separately reviewed input.
- Reconciliation is not exchange certification and does not prove legal data rights beyond supplied reviewed evidence.
- Canonical and production promotion are always false.
- Synthetic fixtures only; no actual NEPSE prices are represented.

## Tests
- Independent agreement, same-publisher duplicate, cross-source conflict, late/unlicensed source, missing/one-source pair, idempotent persistence and hash tampering.
