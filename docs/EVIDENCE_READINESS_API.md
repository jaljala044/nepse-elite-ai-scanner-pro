# Evidence readiness API

`GET /v1/evidence-readiness` reports the operational configuration and
integrity state of the canonical evidence path. It is diagnostics-only: it
returns no source rows, raw payloads, file paths, reviewer IDs or secrets.

## Deployment configuration

- `NEPSE_SOURCE_REGISTRY_PATH`: reviewed JSON source registry.
- `NEPSE_SOURCE_REGISTRY_SHA256`: expected registry digest pinned in trusted
  deployment configuration.
- `NEPSE_REVIEWER_KEYS_JSON`: JSON object mapping reviewer IDs to hex-encoded
  HMAC keys (minimum 32 bytes each). Supply via secret management, never source
  control or request payloads.
- `NEPSE_PROMOTION_LEDGER_PATH`: append-only promotion ledger path.
- `NEPSE_EVIDENCE_DATABASE`: bronze evidence DuckDB path.

The endpoint does not create missing databases or ledgers. Invalid registry,
reviewer-key or ledger state is reported as blocked. Secrets are parsed in
memory and only a key count is returned.

## Readiness states

- `not_configured`: required deployment configuration or storage is absent.
- `blocked`: a registry, signature configuration, ledger or canonical read
  integrity check failed.
- `no_promoted_records`: configuration is valid but no accepted canonical
  promotions exist yet.
- `ready_for_internal_read`: at least one canonical record passes the full
  signed promotion and raw-object integrity checks.

Even `ready_for_internal_read` does **not** mean the scanner is production
eligible. The response keeps `production_eligible=false` until canonical
evidence is deliberately connected to scanner and market-health consumers and
the source activation process is separately approved.

No live NEPSE source is preconfigured by this change.
