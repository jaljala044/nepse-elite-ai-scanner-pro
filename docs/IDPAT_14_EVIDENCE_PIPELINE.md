# IDPAT-14 — NEPSE evidence pipeline orchestration

## Delivered
- Joins existing immutable raw capture/CSV admission, official calendar/universe admission, independent OHLCV reconciliation and rolling history validation.
- Requires a successful raw CSV admission and matching source ID/SHA-256 from a trusted capture manifest.
- Requires approved rights, verified source, finality, point-in-time availability and reviewer-approved independent source groups.
- Conflicts and missing security/session pairs remain quarantined.
- Applies corporate-action review and adjustment-basis checks through the 120-session validator.
- Research-review readiness requires every upstream gate to pass. Production promotion is always false.

## Limitations
- This is an orchestration layer, not a downloader. It consumes outputs from existing capture, reference-data and OHLCV validators.
- It does not authenticate publishers, scrape NEPSE, fetch records or grant data rights.
- Only a trusted backend ingestion service may call it; clients must not submit admission attestations.
- Synthetic tests do not establish actual NEPSE coverage.
