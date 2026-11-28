# Steps 320–329 — Persistent point-in-time source data-quality evidence

## Implemented

1. Add typed append-only evidence records for calendar sessions, capture policies, source captures, market observations, correction records and source lifecycle events.
2. Preserve the submitted bundle as exact raw bytes in the existing bronze evidence store.
3. Generate deterministic evidence identities when the collector does not supply an ID; preserve supplied IDs.
4. Reject duplicate evidence IDs within a bundle and across batches.
5. Enforce timezone-aware capture and receipt timestamps and immutable batch identity.
6. Make exact batch retries idempotent and changed-payload retries fail.
7. Replay only rows whose server-assigned availability timestamp is at or before the decision cutoff.
8. Reuse the Steps 310–319 validators for calendar, capture policy, completeness, corrections and cross-source reconciliation.
9. Expose read-only persistent readiness through `NEPSE_SOURCE_DATA_QUALITY_DB_PATH`; missing stores remain unconfigured without creating a database.
10. Add synthetic tests for persistence, identity, idempotency, cutoff leakage, conflicts and fail-closed readiness.

## Evidence and safety boundaries

All persisted rows remain `review_required` / `provisional`. A HIGH diagnostic means only that the supplied reviewed inputs satisfy the diagnostic's completeness rules; it is not NEPSE first-party attestation, publisher certification, canonical OHLCV/floorsheet approval or trade authorization. Cross-source disagreement is retained and no majority value is promoted. Missing calendar, policy, capture, correction or source observations remain unknown/LOW confidence. No live source data, exchange sessions or capture policies are fabricated.

The readiness endpoint does not accept client-supplied paths or trust settings. This adapter is descriptive only: canonical promotion, OHLCV/floorsheet admission and recommendations remain disabled.
