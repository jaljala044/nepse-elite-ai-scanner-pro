# IDPAT-9 — Deployment readiness endpoint

## Implemented
- Adds a deployment-readiness loader that reads a server-owned artifact root, JSON registry path and pinned registry SHA-256 from environment configuration.
- Rejects missing configuration, non-directory artifact roots, missing registry files, registry hash mismatch and malformed registry documents.
- Loads the pinned artifacts through TrustedArtifactStore and derives the seven IDPAT gates through the Step 8 bridge.
- Exposes only gate readiness and lineage metadata; it does not expose raw artifact payloads.
- Missing deployment configuration returns blocked status rather than falling back to client-supplied attestations.

## Environment configuration
- NEPSE_TRUSTED_ARTIFACT_ROOT
- NEPSE_TRUSTED_ARTIFACT_REGISTRY
- NEPSE_TRUSTED_ARTIFACT_REGISTRY_SHA256
- Optional NEPSE_TRUSTED_ARTIFACT_MAX_AGE_DAYS (default 7)

The registry hash must be pinned through deployment configuration outside the API request. Registry and artifact write access must be restricted to the ingestion/approval service.

## API
POST /v1/research/idpat/gate-readiness
Request body contains only decision_date and decision_time. No gate statuses, source IDs, evidence IDs, registry paths or hashes are accepted from the caller.

## Limitations
- This is a readiness endpoint, not a live data acquisition service.
- No production NEPSE artifacts are currently provisioned by this change.
- A valid registry and hash establish deployment pinning and payload integrity, not exchange authenticity or data-use rights.
- IDPAT scoring, recommendations and order execution remain disabled.
