# P4.29 — Docker persistence acceptance test

## Purpose

P4.28 introduced a named Docker volume for the API DuckDB import database.
This step adds an executable synthetic-data acceptance test rather than
mistaking a configured volume for proven persistence.

## Run

Use a disposable deployment only. From the repository root:

```sh
docker compose build
docker compose up -d
python scripts/verify_docker_persistence.py
```

The script validates the Compose configuration, waits for API health, uploads
one uniquely named synthetic OHLCV row, reads it back, restarts the API
container, waits for health again, and verifies the exact row remains present.
It prints a JSON evidence record with the generated symbol and ingest batch ID.

The script deliberately leaves its synthetic row in the volume. To reset a
disposable test environment after preserving the output:

```sh
docker compose down -v
```

**Never run the reset command against a deployment containing data that must
be retained.** The smoke test itself does not delete data.

## Acceptance criteria

- Compose configuration validates.
- API is healthy before ingestion and after restart.
- Ingest accepts exactly one row.
- The row read before restart matches the expected synthetic values.
- The same row is readable after container restart.

## Boundaries

A passing test proves only that this one API database survives a container
restart while its Docker named volume remains attached. It does not prove
survival of host loss, volume deletion, provider failure, migration, redeploy
to a different host, backup integrity, or restore. It does not test the
separate bronze/raw evidence store. Run the drill on the actual target host
and retain its JSON output, Docker image digest, volume identity and timestamp
before making any durability claim. Production eligibility remains false.
