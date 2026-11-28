# P4.29 — Backup retention and recovery operations

## Scope

P4.29 adds an operator-facing audit for backup freshness and an append-only
restore-drill record. It builds on the P4.27 verified backup/isolated restore
implementation and the P4.28 single-instance persistent-volume baseline.

## Backup freshness and retention

`audit_backup_retention` enumerates backup directories, verifies each backup
using the P4.27 byte inventory and SHA-256 checks, parses timezone-aware UTC
creation times, detects duplicate IDs, reports invalid backups, and flags a
latest valid backup older than the configured freshness threshold. It also
reports the IDs beyond the newest `retain_last` valid backups as
`retention_review_candidates`.

These candidates are recommendations only. The function never deletes,
rewrites, moves, expires, or overwrites a backup. Operators must review and
execute retention separately under their approved retention/legal-hold policy.
The defaults (26-hour freshness and 7 retained backups) are application
thresholds, not proof that a scheduled backup job actually ran.

## Restore-drill log

A drill may be recorded only when the isolated restore result is
`restore_verified` and its post-restore audit is `integrity_ok`. Each JSONL
event includes the drill/backup IDs, UTC timestamp, result, previous-event
hash, and its own SHA-256. The verifier checks every link and rejects duplicate
IDs, tampering, malformed records, and broken chains. Writers take an
inter-process exclusive `flock` on a sidecar lock file across log validation,
duplicate-ID detection, chain-head selection, and append. The log and lock
paths reject symlinks; appends use `O_APPEND`, `O_NOFOLLOW` where available,
and `fsync`. A crash/partial append leaves the log invalid and blocks later
appends until operator recovery. The lock protocol requires a local filesystem
with working POSIX advisory locks. This is tamper-evident, not an independently
signed or immutable off-site audit record; an operator with filesystem write
access can rewrite the entire log.

## Readiness semantics

The retention audit is `healthy` only when the configured backup freshness,
minimum-valid-backup and restore-drill requirements pass. Missing, stale,
future-dated, duplicate or corrupt evidence is not treated as neutral.
Callers may explicitly disable the restore-drill requirement for diagnostics,
but that does not create a production-ready status.

All outputs preserve `production_eligible=false`. No backup deletion,
scheduled job, cloud bucket, encryption, provider retention lock, off-site
replication, alert delivery, or actual deployment-host drill is performed by
this module. The drill log records a supplied restore result; it does not run
a restore itself.

## Tests

From `backend/`:

```bash
python -m unittest tests.test_evidence_backup_operations tests.test_evidence_backup_restore tests.test_evidence_recovery
```
