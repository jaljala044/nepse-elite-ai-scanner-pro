# P4.32 — Scheduled backup runner and monitoring

## What this adds

- A serialized scheduled-run wrapper around the P4.30 verified backup CLI.
- Explicit pre-backup writer-quiesce and post-backup resume commands.
- A non-blocking OS file lock to prevent overlapping runs on the same host/filesystem.
- Append-only JSONL receipts with a SHA-256 hash chain.
- A read-only audit CLI that detects missing receipts, malformed/tampered history,
  failed latest runs, future timestamps, and backups overdue beyond the configured
  interval plus grace period.
- Non-zero exit codes for failed runs and unhealthy monitoring, suitable for
  systemd/cron monitoring and external alerting.

## Configure

Create an operator-owned JSON config outside source control, for example:

```json
{
  "quiesce_argv": ["/opt/nepse/bin/pause-evidence-writers"],
  "backup_argv": [
    "/opt/nepse/venv/bin/python",
    "/srv/nepse/scripts/create_evidence_backup.py",
    "--database", "/srv/nepse/data/evidence.duckdb",
    "--storage-root", "/srv/nepse/data/evidence-raw",
    "--destination-root", "/mnt/verified-backup-volume",
    "--writers-quiesced"
  ],
  "resume_argv": ["/opt/nepse/bin/resume-evidence-writers"],
  "command_timeout_seconds": 1800
}
```

Commands are argument arrays, never shell strings. Executables must be absolute
paths. Hook scripts, paths, service identities and mount identities must be
validated by the deployment operator. Do not put secrets in arguments or
source control.

## Run from a managed scheduler

The scheduler (systemd timer, cron wrapper, or orchestration platform) remains
an explicit deployment choice. Invoke:

```sh
python scripts/run_scheduled_evidence_backup.py \
  --mode run \
  --config /etc/nepse/evidence-backup.json \
  --receipts /var/lib/nepse/backup-receipts.jsonl \
  --lock /var/lock/nepse-evidence-backup.lock \
  --run-id "evidence-$(date -u +%Y%m%dT%H%M%SZ)"
```

The runner calls the quiesce hook, runs the verified backup command only when
quiescing succeeds, then attempts the resume hook even when quiescing or backup
execution reports failure. Resume failure forces a failed receipt. A timeout,
process kill, host crash, or power loss can still prevent cleanup; a deployment
must have an independent watchdog/recovery procedure for writers left paused.

The file lock serializes cooperating runner instances only. It is not a
distributed lock and does not prevent writers that ignore the hook. The
`--writers-quiesced` option in the underlying backup CLI remains an operator
attestation, not proof that every writer is stopped.

## Monitor

Run after the scheduler interval:

```sh
python scripts/run_scheduled_evidence_backup.py \
  --mode audit \
  --receipts /var/lib/nepse/backup-receipts.jsonl \
  --expected-interval-hours 24 \
  --grace-hours 2
```

Exit code 0 means the receipt chain is valid and the latest recorded run is
successful and fresh. Exit code 2 means attention is required. Send non-zero
exit codes to the deployment's external alerting system. The audit detects a
missed run after the expected interval plus grace; it does not itself run a
scheduler or deliver notifications.

## Receipt integrity and limits

Receipts store run IDs, timestamps, status, hook outcomes, a SHA-256 digest of
backup stdout, issue codes and the prior receipt hash. They do not store command
arguments or captured stdout/stderr. The hash chain is tamper-evident against
accidental edits, not independently signed or immutable against an operator
who can rewrite the entire ledger. Back up the receipt ledger separately.

A successful receipt is based on the P4.30 CLI's JSON response and verification
status. It does not independently prove an off-host failure domain, encryption,
provider retention lock, restore success, or cloud durability. P4.29 retention
and restore-drill audit remain separate controls.

No scheduler has been installed or enabled, no production hooks or paths have
been configured, no real backup has been executed, and no alert destination has
been connected. All outputs preserve `production_eligible=false`.
