# P4.30 — Evidence backup operator runner and policy

## Purpose

P4.27 provides the verified bronze-store backup and isolated restore library.
This step adds a fail-closed operator entry point and a minimum operational
policy. It does not silently invent database paths, claim an off-site target,
schedule jobs, or delete backups.

## Run manually

Run only after confirming the actual bronze database and raw payload paths.
Stop all ingestion and other writers first:

```sh
python scripts/create_evidence_backup.py \
  --database /absolute/path/to/evidence.duckdb \
  --storage-root /absolute/path/to/evidence-raw \
  --destination-root /absolute/path/to/mounted-backup-volume \
  --writers-quiesced
```

The destination root must already exist. Each run creates a unique child
directory, refuses overwrite, calls the P4.26 source integrity audit through
the P4.27 library, checkpoints DuckDB, inventories files and hashes, then
re-verifies the completed backup. It emits a JSON report and returns a
non-zero exit code if verification fails.

The flag `--writers-quiesced` is an operator attestation, not an OS-level
distributed lock. The operator must actually stop all writers. Do not run
while API ingestion or background collectors can write to the same evidence
store.

## Scheduling

Do not enable a scheduler until the deployment has a stable host, confirmed
paths, a tested off-host destination, and an operational writer-quiescence
mechanism. Then schedule the command through the host's managed scheduler
(e.g. systemd timer or cron) with:
- a dedicated least-privilege service identity;
- a pre-backup step that stops/pauses every evidence writer;
- a post-backup step that resumes writers even when backup fails;
- captured stdout/stderr, exit code, timestamp and alerting on failure;
- no credentials or encryption keys in command-line arguments or source control.

A simple cron entry alone is insufficient because it does not safely quiesce
writers or guarantee restart after failure.

## Backup policy baseline

Recommended starting policy, subject to business/legal approval:
- daily verified backups, plus a weekly isolated restore exercise;
- retain 14 daily and 8 weekly recovery points;
- keep at least one copy outside the application host/account;
- encrypt at rest using managed encryption and documented key recovery;
- restrict backup read/write/delete roles separately;
- monitor last-success timestamp, age, size, checksum verification and
  restore-test outcome;
- preserve immutable/auditable logs of backup and restore operations.

These are proposed policy defaults, not configured or proven settings.
No retention pruning is automated here: deleting recovery points before a
verified newer backup and restore process exists would be unsafe.

## Acceptance and evidence

For every run, retain the JSON output and independently record the host,
mount/volume identity, destination provider/account, UTC timestamp, backup
size, encryption status, retention class and operator identity. A backup is
not called off-site until the destination is demonstrably outside the
application host failure domain.

Restore into a new isolated destination using the P4.27 restore function,
then run the P4.26 integrity audit. Never restore over the live store.

## Explicit limitations

This is an operator runner, not a configured recurring job. It does not
provide encryption, off-site provisioning, immutable object lock, retention
deletion, alerting, a writer lock, host-loss recovery, or a completed restore
drill. The actual bronze database and raw payload paths have not yet been
confirmed in a deployed environment. Keep `production_eligible=false`.
