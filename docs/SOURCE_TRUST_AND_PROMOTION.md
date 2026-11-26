# Source trust registry and evidence promotion

## Purpose and boundary

This layer separates three questions that must not be conflated:

1. **Source trust:** is this publisher authorized for this record type and historical period?
2. **Record validation:** do independently reviewed checks establish this exact payload, schema, security identity, session, timestamp and market-data semantics?
3. **Usage rights:** may the resulting data be retained, used internally, used for model training or redistributed?

A source can be trusted for authenticity while its redistribution rights remain unknown. Conversely, a permissive licence does not make its market data authoritative.

No source is approved by default. The repository ships no populated production trust registry and no reviewer secrets.

## Registry contract

`backend/app/source_trust_registry.py` defines effective-dated source policies. Every policy requires:
- stable source ID and publisher identity;
- trust tier and explicitly allowed record types;
- separately declared canonical record types;
- active/review-required/suspended/revoked status;
- effective-from/effective-to dates;
- reviewer, review timestamp and evidence references;
- a separate rights declaration.

Only `exchange_primary` and `official_registry` tiers can be configured for canonical records. Secondary publishers, licensed aggregators, user uploads and derived datasets may be retained as corroborating/research evidence, but cannot become canonical through this policy engine. Their records must not be silently substituted for official exchange evidence.

The serialized registry is content-hashed. Production callers must pin the expected registry SHA-256 in trusted deployment configuration and call `verify_source_registry`; accepting an arbitrary registry supplied with the data request defeats the trust boundary. Registry updates require reviewed code/configuration changes and a new pinned digest.

## Reviewer attestations

Promotion validation requires a server-verifiable HMAC-SHA256 signature over the complete validation packet. Reviewer keys are injected from a secret manager or protected environment configuration; they must never be committed to the repository, included in API requests, or written to logs.

The signed packet binds:
- reviewer and validation ID;
- validation timestamp and exact raw payload SHA-256;
- per-record-type required checks;
- independent evidence references for each check.

The required checks vary by record type. For OHLCV they include payload integrity, source identity, schema mapping, instrument identity, independently verified session calendar, point-in-time availability, corporate-action basis and price integrity. Floorsheets additionally require trade identity and coverage completeness. Broker observations require broker identity. A missing check or evidence reference blocks promotion.

The current HMAC scheme is an application-level reviewer attestation mechanism. Key rotation, reviewer provisioning, access control, secure signing UI and operational audit retention must be supplied by deployment infrastructure before production use. It does not prove that a reviewer actually performed a competent review.

## Promotion ledger

Every promotion/rejection/revocation decision is an append-only JSONL event with a SHA-256 hash chain. Revisions are represented by new events, never edits to historical decisions. The ledger verifier detects altered, removed, reordered or duplicated events. A corrupted ledger blocks canonical reads and further appends.

The writer is intended to be serialized by a single trusted service process. Do not mount the same ledger for concurrent independent writers; use a transactional database with compare-and-swap/locking before scaling writes horizontally.

A promotion is accepted only when:
- the pinned registry digest matches;
- the source is active for the exact session and allowed for that canonical record type;
- the reviewer signature verifies against a server-held key;
- the row's payload digest matches the exact raw payload digest;
- the record and validation were available by the decision timestamp;
- every required validation check passed with an evidence reference.

Revocation is an append-only event. A revoked record is no longer returned by the active-promotion reader. Rejected decisions remain in the audit ledger but never enter the active set.

## Explicit non-goals

This change does not:
- populate or approve NEPSE or third-party sources;
- certify any live NEPSE payload, OHLCV row, broker trade or corporate action;
- connect the ledger to the current API upload store or market-health pipeline;
- grant data redistribution rights or training rights;
- make any existing CSV import canonical;
- create market scores, rankings or trade signals.

Until a trusted registry, reviewer key provisioning, evidence verification workflow, canonical storage integration and production-source reconciliation are in place, scanner data quality remains subject to the existing UNKNOWN / PRESERVE_CAPITAL gates.

## Tests

`backend/tests/test_source_trust_registry.py` covers source-tier restrictions, pinned registry digests, signed reviewer attestations, per-record validation requirements, point-in-time checks, effective dates, payload digest matching, hash-chain tamper detection, idempotent events and revocation.
