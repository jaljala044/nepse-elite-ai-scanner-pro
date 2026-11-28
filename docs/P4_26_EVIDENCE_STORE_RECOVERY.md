# P4.26 — Evidence-store restart and recovery audit

## Scope

The read-only `app.evidence_recovery.audit_evidence_store` routine checks the
on-disk DuckDB catalog against the content-addressed raw-object directory after
a process restart or deployment recovery.

It verifies:
- each catalogued raw payload exists and matches its stored byte count and
  SHA-256;
- each capture manifest exists, parses, matches the immutable catalog copy,
  and retains its fetch/source/payload lineage;
- each normalized record points to a catalogued capture with matching lineage;
- payloads and capture manifests present on disk but absent from the catalog
  are reported as unindexed/orphan evidence.

## Recovery behavior

The audit is strictly non-destructive. It never deletes, rewrites, repairs,
replays, promotes, or silently adopts orphan files. An operator must preserve
and investigate every reported object. Exact replay remains the supported
idempotent ingestion path after a clean database reopen; a replay with changed
metadata or normalized content must continue to fail closed.

The audit returns:
- `integrity_ok` only when catalog and filesystem checks pass;
- `integrity_issues` when one or more mismatches/orphans are found;
- `unavailable` when the database or storage root is missing or the catalog
  cannot be read.

All outcomes set `production_eligible=false`. This validates local
catalog/filesystem consistency only. It does not prove cloud-volume durability,
backup freshness, restore-point correctness, cross-zone replication, crash
atomicity under power loss, or multi-writer safety.

## Tests

Run from `backend/`:

```bash
python -m unittest tests.test_evidence_recovery tests.test_evidence_store tests.test_raw_capture
```

Tests use temporary synthetic DuckDB databases and files. They do not inspect
or certify a production deployment or live NEPSE records.
