# Scheduled official NEPSE market-summary evidence ingestion

The scheduled workflow captures the official market-summary-history response, verifies and archives the exact response bytes, then imports those bytes into a DuckDB bronze evidence catalog on the runner.

## Workflow behavior

- Runs on the existing weekday schedule and manual dispatch.
- Captures the official endpoint and retains the raw response plus capture report.
- The importer independently checks the official source ID, HTTPS host, endpoint path, HTTP 200, capture-origin attestation, byte length and SHA-256.
- Rows are always `review_required` and `provisional`; no source approval, calendar verification or trading eligibility is granted.
- The DuckDB catalog and raw object store are uploaded as a 90-day workflow artifact for audit and download.

## Important persistence limitation

GitHub-hosted runners are ephemeral. The uploaded artifact is a retained evidence bundle, not a live shared application database. Production persistence requires a separately provisioned durable storage/database target and secrets/permissions. This workflow intentionally does not commit a mutable DuckDB file to Git or claim production readiness.

## Tests

The importer tests cover raw preservation, provisional status, exact replay, origin and host checks, hash mismatch, HTTP status and timestamp validation.
