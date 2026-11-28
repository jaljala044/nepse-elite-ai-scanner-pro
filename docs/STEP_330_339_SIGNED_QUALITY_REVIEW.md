# Steps 330–339 — Signed calendar and capture-policy review attestations

## Ten implementation items

1. Add a server-owned reviewer registry with explicit allowed scopes.
2. Sign the registry using HMAC-SHA256 and verify its integrity at load time.
3. Reject missing, malformed, duplicate, unapproved or future-dated reviewer registry entries.
4. Add evidence-bound review attestations for calendar-session records.
5. Add evidence-bound review attestations for source/dataset capture policies.
6. Bind each attestation to a SHA-256 digest of the exact evidence body.
7. Enforce reviewer identity, allowed scope, approval decision and timezone-aware review timestamp.
8. Reject altered evidence, invalid signatures, unauthorized scopes and future attestations during historical replay.
9. Load the registry and HMAC key only from server-side environment configuration and expose readiness status.
10. Add unit and end-to-end tests; missing registry means calendar/policy evidence is excluded and quality remains LOW.

## Runtime configuration

- `NEPSE_SOURCE_QUALITY_REVIEW_REGISTRY_PATH`
- `NEPSE_SOURCE_QUALITY_REVIEW_HMAC_KEY`

## Security boundary

HMAC protects internal payload integrity. It does not prove a reviewer's real-world identity, official NEPSE authority, publisher authenticity, legal ownership or beneficial ownership. The reviewer registry itself must be provisioned and controlled by an authorized operator. All evidence remains provisional; canonical OHLCV/floorsheet promotion and production recommendations remain disabled.
