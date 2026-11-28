# Steps 250–259: persistent sector evidence timeline

## Implementation
- Reuse the existing append-only DuckDB evidence store; do not create a parallel database.
- Persist each timeline batch as exact canonical JSON bytes with a SHA-256 digest and capture manifest.
- Store each event as a provisional `sector_membership` evidence record, retaining the original nested event and its publisher/source provenance.
- Keep capture-envelope identity distinct from the original publisher identity.
- Make exact batch retries idempotent and reject changed payloads under an existing batch ID.
- Reject event-ID reuse across distinct batches and duplicate IDs within a batch.
- Load by batch or across all persisted batches without silently promoting evidence.
- Replay loaded events through the existing Nepal-local point-in-time sector timeline rules.
- Keep all records `review_required` / `provisional`; production admission and recommendation overrides remain disabled.

## Evidence and trust boundaries
The capture envelope is an internal storage container, not an independent publisher. Original event-level source IDs, publisher IDs, source classes, evidence references, payload hashes, captured/available timestamps and effective dates remain in the nested event. Publisher independence still requires a separately reviewed publisher registry; a string publisher ID is not proof of independence. The store does not establish official NEPSE membership or security identity.

## Validation
Synthetic tests cover raw/normalized persistence, exact replay idempotency, immutable batch conflicts, duplicate event IDs, batch filtering, point-in-time replay and closed production gates. No live sector classifications or identity mappings are added.
