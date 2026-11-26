# Canonical evidence read gate

## Purpose

The immutable evidence catalog is the bronze layer. Every ingested row remains
`review_required` / `provisional`, even if an uploaded payload tries to claim
`verified` / `final`.

`backend/app/canonical_evidence.py` provides a separate, read-only canonical
view. It joins the evidence catalog to the signed promotion ledger and the
pinned source registry. It does not mutate bronze rows or create a production
data feed.

## Promotion requirements

A row is returned only when:
- its database record ID has an accepted promotion event;
- the promotion ledger hash chain is valid;
- the registry digest matches the trusted pinned digest;
- the event's reviewer attestation verifies with a server-held reviewer key;
- the attestation is bound to the exact record ID, source ID, record type,
  payload digest, session, availability time, registry digest and decision time;
- the source policy is active and allows that record type for the exact session;
- every record-type-specific validation check and independent evidence
  reference passes; and
- the original raw payload object still exists and hashes to the recorded SHA-256.

Revocations are rechecked and remove the record from the canonical view. An
invalid ledger, signature, registry, raw object, or row/event mismatch blocks
the read instead of returning partial trusted-looking data.

## Bronze versus canonical status

The returned canonical view labels a promoted row as
`source_validation_status=verified` and `finality_status=final` only when the
signed `exchange_finality` check is present and passed. It also preserves the
original bronze labels in `bronze_source_validation_status` and
`bronze_finality_status`. This is a read-time projection; the persisted bronze
row is never updated.

The database record ID is the canonical evidence-store primary key, not a
parser-supplied `record_id`. `load_evidence_record_details` retrieves this
database identity together with the raw object path for integrity verification.

## Production boundary

This read gate is not yet wired into the scanner API, market-health pipeline,
feature pipeline, or ranking engine. No source is populated or promoted by
default. No live NEPSE record is claimed to be verified. Reviewer-key
provisioning, trusted registry digest deployment, operational review UI,
transactional multi-writer ledger storage, and independent evidence acquisition
remain prerequisites for production activation.

Tests use synthetic fixtures only and prove fail-closed integration behavior,
not actual NEPSE data authenticity.
