# IDPAT-10 — Immutable raw capture and canonical OHLCV admission

## Delivered
- Content-addressed immutable local raw capture using SHA-256, byte count and a sidecar provenance manifest.
- Capture manifest preserves source ID/URI/publisher, published/captured/available timestamps, rights status, independent source validation status and finality.
- Existing content-addressed paths cannot be overwritten with different bytes or conflicting metadata.
- CSV admission validates required schema, stable security ID, verified exchange session, OHLC relationships, positive volume, nonnegative turnover, duplicate symbol/session keys, row-level availability, source rights, finality, raw hash and coverage.
- Invalid rows are explicitly quarantined. No correction, deletion, forward-fill, or missing-session inference occurs.
- Even a successful validation allows research admission only; production promotion remains disabled.

## Security and evidence boundaries
- This module performs no external HTTP request. It does not assume a candidate endpoint is official or accessible.
- A SHA-256 digest proves byte integrity against the manifest, not publisher authenticity, exchange origin, completeness, or legal data-use rights.
- Source validation, finality, rights clearance, expected security IDs and verified session calendar must be supplied by trusted upstream review/ingestion services.
- Test fixtures are synthetic and do not represent actual NEPSE records.

## Acceptance tests
- Hash mismatch; missing/unknown rights; unverified source; duplicate key; invalid OHLC; future availability; missing calendar/universe; idempotent raw capture; research-only admission.
