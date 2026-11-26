# P4.28 — Backup retention and recovery monitoring

## Contract

The read-only monitor inventories immediate child backup directories, validates
manifest timestamps, verifies each backup's complete file inventory and SHA-256
checksums, and computes freshness in UTC. It reports the newest verified
backup, invalid backups, stale-backup status, and whether the configured
expected backup interval plus grace period has been exceeded.

A missing backup root, no valid backup, a stale latest valid backup, or an
overdue schedule fails closed. Malformed and corrupted backups are reported
as invalid and never counted as recovery points. Future timestamps and
timezone-naive timestamps are rejected.

## Retention

The count-based `keep_last` policy marks older verified backups as retention
candidates. This is advisory only: the monitor never deletes, rewrites,
quarantines, or modifies backup directories. Invalid backups are not deletion
candidates and must be reviewed separately.

## Limits

This is local filesystem monitoring, not a scheduled service or cloud-provider
health check. It does not prove that a backup is off-site, durable, encrypted,
replicated, restorable on another host, or retained by an external provider.
The monitor always returns `production_eligible=false`. Operators must
provision persistent storage, schedule the monitor, alert on critical status,
and perform independent restore drills.
