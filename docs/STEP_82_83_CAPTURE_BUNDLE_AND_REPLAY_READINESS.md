# Steps 82–83 — Raw source bundle validation and replay readiness

## Step 82 — validate the supplied source bundle
- Reuse the existing human-reviewed source contract validator and raw capture manifest validator.
- Verify every page's raw bytes against its SHA-256, exact HTTPS host allowlist, publisher ID, capture cutoff, contiguous pagination and final-page marker.
- Require an injected dataset-specific schema validator to return a positive row count.
- Require an injected immutable archive verifier to return an archive reference and manifest SHA-256.
- Require approved NEPSE, CDSC and at least two independently reviewed third-party source contracts/captures; retain ShareSansar, Chukul, ShareHub Nepal and Punji in the source candidate register.
- Require hashed reconciliation, calendar and point-in-time universe reports. Any missing proof blocks admission.

## Step 83 — controlled replay handoff
- Run bundle validation first; do not accept a caller-supplied "ready" boolean as a substitute for raw manifest/payload validation.
- Only a ready bundle is handed to the Step 78–79 dataset admission, leakage audit and human replay approval.
- Preserve one common dataset fingerprint for six strategies × four horizons.
- Keep production and canonical promotion disabled. Report replay metrics only after the actual runner returns and its output is independently reviewed.

## Boundaries
The implementation supplies validation interfaces, not provider credentials, legal permissions, source URLs, raw history, schema parsers, archive infrastructure or a reconciliation engine. Tests use synthetic bytes and injected validators to test blocking/acceptance paths. No real NEPSE data is acquired or replayed by these steps.
