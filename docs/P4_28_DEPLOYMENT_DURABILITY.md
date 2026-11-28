# P4.28 — Deployment durability baseline (not production approval)

## Scope

The repository has no confirmed hosting provider or deployed backend. This
change supplies a reproducible single-instance Docker baseline so deployment
work can begin without assuming a cloud vendor.

The API's interactive CSV-import database is placed at
`/var/lib/nepse/nepse-api.duckdb` using `NEPSE_API_DATABASE`. Docker Compose
mounts the named volume `nepse-api-data` at that path. The container runs one
Uvicorn worker and binds the published port to loopback only; place a separately
configured TLS/authenticated reverse proxy in front of it before external use.

## Start locally

From the repository root:

```sh
docker compose build
docker compose up -d
docker compose ps
curl --fail http://127.0.0.1:8000/health
```

The named volume survives container replacement when the same Docker host and
volume are retained. It does not survive host loss, volume deletion, or an
unconfigured migration to another host.

## Restart persistence drill

Use a disposable deployment and a small synthetic CSV only:

1. Upload a synthetic CSV to `POST /v1/ingest/csv` and record the returned
   batch ID and accepted row count.
2. Confirm the row is visible after restarting the container:
   `docker compose restart nepse-api`.
3. Recreate the container without deleting the volume:
   `docker compose down` then `docker compose up -d`.
4. Confirm the same imported row and batch history remain available.
5. Record command output, timestamps, image digest, volume identity and API
   responses as deployment evidence.

Do not use `docker compose down -v`: that intentionally deletes the volume.

## Safety constraints

- Keep exactly one API instance and one Uvicorn worker while this API uses
  local DuckDB writes. Do not horizontally scale or mount the same DuckDB
  file into multiple writers.
- Do not expose port 8000 publicly. Add TLS, authentication, request limits,
  secrets management and network controls at a reviewed ingress layer.
- Keep backups separate from the live volume. The P4.27 backup/restore tool
  requires ingestion writers to be quiesced and an integrity audit to pass.
- Test restore into a new isolated volume before any recovery operation.
- Never store credentials in the image, Compose file, or Git.

## Explicit gaps — remain not production-ready

This baseline does not deploy to a cloud provider and does not prove a live
restart/redeploy. It does not configure off-site backup, backup scheduling,
retention, encryption at rest, cross-region replication, provider-level
durability, monitoring/alerting, TLS, authentication, or disaster recovery.

It also does not claim that the separate bronze/raw evidence-store database
and payload directory are wired to this named volume. Before production use,
identify their actual configured database and storage-root paths and mount both
on durable storage; then run the P4.26 audit and P4.27 backup/isolated-restore
drill against that exact deployment.

`production_eligible` must remain false until these gaps are closed and the
restart, redeploy, backup and restore drills have recorded passing evidence.
