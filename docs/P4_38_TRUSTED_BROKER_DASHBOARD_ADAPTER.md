# P4.38 trusted broker dashboard adapter

This change adds `POST /v1/research/broker-dashboard/trusted`. Its request contains
only an as-of date and timezone-aware decision timestamp. Broker profiles,
sector rotation, market health, index intelligence and sector membership
artifacts are loaded from a deployment-owned JSON registry and immutable
payload directory.

Deployment configuration:

- `NEPSE_TRUSTED_ARTIFACT_ROOT`: root directory for immutable payload files.
- `NEPSE_TRUSTED_ARTIFACT_REGISTRY_PATH`: deployment-controlled registry JSON path.
- `NEPSE_TRUSTED_ARTIFACT_MAX_AGE_DAYS`: optional nonnegative freshness limit (default 7).

The registry is not accepted from API request data. Each required module must
pass the existing trusted-artifact checks: payload SHA-256, source and evidence
IDs, finality, source validation, point-in-time availability, session calendar,
coverage, corporate-action clearance where applicable, effective-dated sector
membership, and broker-code mapping/identity coverage.

Required module payload contracts:

- `broker_profiles.data.rolling_profiles`: P4.37 rolling-profile object.
- `broker_profiles.data.candidates`: optional list of descriptive candidates.
- `broker_sector_rotation.data.sector_rotation_by_window`: optional mapping of
  dashboard windows to point-in-time broker-sector rotation artifacts.
- `market_health.data`, `index_intelligence.data`, and `sector_rotation.data`
  are returned as supporting market context, not recalculated by this adapter.

If any required artifact is missing, stale, late, unverified, incomplete, or
hash-mismatched, the endpoint returns an explicit insufficient-evidence
response and withholds the dashboard. No absent sessions are zero-filled.
The existing caller-payload dashboard endpoint remains available for local
research/testing but is explicitly not the trusted deployment boundary.

This endpoint remains descriptive-only. Broker codes are execution-channel
identifiers, not beneficial owners; BUY/SELL signals, probabilities, production
eligibility and trade actions remain disabled.
