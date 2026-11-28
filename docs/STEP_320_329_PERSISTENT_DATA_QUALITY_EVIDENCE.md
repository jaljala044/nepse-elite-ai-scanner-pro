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

All persisted rows remain `review_required` / `provisional`. A HIGH diagnostic requires reviewed calendar/policy inputs, fresh expected captures, correction history and at least two distinct source IDs agreeing for each observed group. It does not prove publisher ownership-group independence and is not NEPSE first-party attestation, publisher certification, canonical OHLCV/floorsheet approval or trade authorization. Cross-source disagreement is retained and no majority value is promoted. Missing calendar, policy, capture, correction or source observations remain unknown/LOW confidence. No live source data, exchange sessions or capture policies are fabricated.

The readiness endpoint does not accept client-supplied paths or trust settings. This adapter is descriptive only: canonical promotion, OHLCV/floorsheet admission and recommendations remain disabled.


## Steps 330–339 — Signed review attestation gate

The follow-on review gate adds a server-owned HMAC-signed reviewer registry. Calendar-session and capture-policy rows count as reviewed only when their per-row attestation has a valid signature, an allowed reviewer/scope, an exact evidence-payload hash and a review timestamp no later than the replay cutoff. Registry and key are read only from server configuration:

- `NEPSE_SOURCE_QUALITY_REVIEW_REGISTRY_PATH`
- `NEPSE_SOURCE_QUALITY_REVIEW_HMAC_KEY`

Without the registry, calendar and policy evidence remain excluded from trusted replay and quality stays LOW. HMAC is an internal integrity control only; it does not authenticate a person's real-world identity, establish NEPSE authority, or certify publisher ownership. No production admission is enabled.
