# Steps 220–229: server-side sector evidence registry

1. Add a server-owned, read-only registry loader; no client request can submit membership.
2. Require a configured registry path and 32+ character HMAC secret.
3. Verify a canonical registry-level HMAC before parsing any entry.
4. Verify a separate reviewer-attestation HMAC for every membership manifest.
5. Require reviewer identity, scope, decision and review timestamp.
6. Reject future-dated registry generation or reviewer attestations.
7. Re-run the existing sector-membership manifest structural audit and exact-universe coverage check.
8. Reject duplicate, missing and unexpected symbols across registry entries.
9. Expose membership only as internally attested research-only; never mark it exchange-verified or production-admissible.
10. Add negative tests and document deployment configuration and evidence limitations.

## Runtime contract

Environment variables:
- `NEPSE_SECTOR_EVIDENCE_REGISTRY_PATH`: server-side JSON registry path.
- `NEPSE_SECTOR_REGISTRY_HMAC_KEY`: secret of at least 32 characters, held outside source control.

The registry HMAC protects integrity and reviewer attestations; it does not prove publisher authenticity or official NEPSE classification. This batch does not enable BUY signals or ranking. The registry is not populated with fabricated sector membership. Until a real registry is configured, readiness reports `not_configured` and scan results show sector membership unavailable.

See `backend/app/sector_membership_manifest.py` for the pre-existing structural audit contract. A `review_ready` result alone is not verified evidence.
