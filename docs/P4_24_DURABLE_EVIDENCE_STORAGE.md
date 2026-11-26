# P4.24 — Durable evidence storage contract

## Purpose

The official market-summary capture workflow currently runs on ephemeral GitHub-hosted
runners. Its 90-day workflow artifact is an audit hand-off, not a shared production
database. P4.24 defines the deployment contract for a durable bronze evidence volume.

## Required deployment configuration

Mount a persistent volume and configure all four environment variables:

- `NEPSE_EVIDENCE_STORAGE_ROOT`: mounted volume root
- `NEPSE_EVIDENCE_DATABASE`: DuckDB catalog path beneath that root
- `NEPSE_EVIDENCE_RAW_ROOT`: immutable raw-object directory beneath that root
- `NEPSE_EVIDENCE_PERSISTENT_VOLUME=true`: explicit operator attestation that the
  mount is provisioned as persistent storage

Example paths (illustrative only):

```text
NEPSE_EVIDENCE_STORAGE_ROOT=/var/lib/nepse-evidence
NEPSE_EVIDENCE_DATABASE=/var/lib/nepse-evidence/catalog/evidence.duckdb
NEPSE_EVIDENCE_RAW_ROOT=/var/lib/nepse-evidence/raw
NEPSE_EVIDENCE_PERSISTENT_VOLUME=true
```

Do not set the attestation flag on an ephemeral container filesystem. The flag is
an operator assertion; the application cannot independently prove cloud-volume
retention, replication, backup policy or survival after host loss.

## Implemented validation

`app.evidence_storage_config.inspect_evidence_storage`:

- fails closed when any path or the operator attestation is missing;
- requires the DuckDB catalog and raw-object root to resolve beneath the configured
  storage root;
- checks that catalog parent and raw-object root share the root filesystem;
- performs a write, file fsync and directory fsync probe, then removes the probe;
- reports `configured_operator_attested` only after the filesystem checks pass;
- always leaves `deployment_persistence_verified=false` and
  `production_eligible=false`.

The function does not create, migrate or promote evidence records. It does not
change the canonical reader, source registry, promotion ledger, scanner readiness
or any BUY gate.

## Operational constraints still requiring deployment work

1. Provision a real persistent volume in the target hosting environment.
2. Independently verify retention across restart/reschedule and host replacement.
3. Configure encrypted backups and test restore into an isolated environment.
4. Enforce a single DuckDB writer per mounted catalog; use a server database if
   multiple application replicas need concurrent writes.
5. Run a restart/replay/revocation integration test against the deployed volume.
6. Wire this report into the authenticated operational readiness endpoint.

A passing unit test proves the configuration validator behaves as designed. It
does not prove the deployment has durable storage or that the official capture
workflow writes into that deployment. Bronze rows remain review-required and
provisional. Persistence alone never makes a record canonical.
