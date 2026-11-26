# P4.31 — Backup freshness and recovery-readiness audit

## Scope

This is a read-only operator check over the immediate child directories of an
existing backup root. It verifies each backup using the P4.27 checksum and
inventory verifier, reads its UTC creation timestamp, counts valid recovery
points, and checks the newest verified backup against a freshness threshold.

It never changes a backup, deletes old recovery points, runs a restore, or
claims that a path is off-site.

## Run

```sh
python scripts/audit_evidence_backups.py \
  --backup-root /absolute/path/to/mounted-backup-volume \
  --max-age-hours 30 \
  --minimum-verified 1
```

Exit code 0 means the local audit criteria passed. Exit code 2 means the
backup root is not ready under the supplied thresholds. The JSON report
includes valid and invalid backup records, age, integrity and count results.

## Readiness meaning

The report returns `status=ready` only when:
- at least the configured number of verified backups exist;
- the newest verified backup is not older than the configured threshold;
- no discovered backup with a manifest has a failed integrity or metadata
  check.

This is local backup-set readiness only. It does not establish:
- an off-host or separate-account failure domain;
- encryption at rest or recoverable encryption keys;
- immutability or retention enforcement;
- a successful isolated restore;
- complete capture of every database and raw payload path;
- a running scheduler, alert delivery, or production service health.

The report hard-codes these external controls as unverified and keeps
`production_eligible=false`.

## Operational use

Run after each manual backup and from an external monitoring system once a
host and scheduler exist. Alert on non-zero exit code, increasing backup age,
any invalid backup, or missing recovery points. Keep the JSON report with
deployment audit records.

Do not add automatic pruning here. Retention deletion must be a separately
reviewed operation after off-site copies and isolated restore drills are
proven. A green local audit must never be interpreted as disaster-recovery
certification.
