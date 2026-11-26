# P4.27 — Evidence backup and isolated restore

## Operational contract

Backups require ingestion writers to be paused. DuckDB is checkpointed, the
source evidence store must pass the P4.26 read-only integrity audit, and the
database plus complete raw-object tree are copied into a new destination.
The backup manifest records the SHA-256 and byte count of every copied file.

Backups are never overwritten. A failed staging directory is retained for
operator inspection rather than silently deleted. The manifest itself is not
included in its own checksum inventory; it describes the immutable file set.

## Restore

Restore first verifies the exact backup inventory and every file checksum.
Only then does it copy the database and raw tree to a new isolated location.
Because the catalog stores absolute filesystem paths, restore rebinds those
path references to the new raw directory inside the restored DuckDB copy.
Payload bytes, capture manifests, normalized rows, hashes and evidence status
are not rewritten or promoted. The restored store must pass the P4.26 audit
before it is published at the requested restore destination.

An existing destination is always rejected. The live source database and raw
root are never modified by restore.

## Limits

This is an application-level local backup/restore implementation. It does not
provision durable cloud storage, schedule off-site backups, establish retention,
encrypt backups, prove cross-region replication, or test provider-level
point-in-time recovery. The caller must ensure writers are truly quiesced;
the boolean is an operator attestation, not independent process-lock proof.
All reports keep `production_eligible=false`.

## Tests

From `backend/`:

```bash
python -m unittest tests.test_evidence_backup_restore tests.test_evidence_recovery tests.test_evidence_store
```
