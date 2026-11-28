# Steps 300–309 — Persistent source reliability integration

## Ten implementation steps
1. Added `source_reliability_event` to the shared append-only evidence record vocabulary.
2. Added it to the reviewed source-registry record vocabulary with explicit required checks.
3. Persisted validated source lifecycle event batches through the existing raw-byte/DuckDB bronze store.
4. Preserved event payloads, effective dates, source IDs and original provenance inside immutable normalized records.
5. Added deterministic event-manifest hash and batch metadata.
6. Added exact retry idempotency through the existing fetch-id/payload invariants.
7. Added a typed loader that returns events as review-required/provisional.
8. Added read-only source reliability readiness replay from the configured evidence DB.
9. Added explicit expected-source coverage and verified-calendar absence reporting; no calendar is guessed.
10. Added persistence, idempotency, missing-store, historical replay and fail-closed tests.

## Runtime configuration
Set `NEPSE_SOURCE_RELIABILITY_DB_PATH` to an existing evidence DuckDB database to expose persisted source reliability diagnostics. The readiness endpoint never creates a database merely to inspect status. Optional expected source IDs are supplied through server configuration, not client input. No verified session dates are assumed by this integration; calendar coverage remains unconfigured until an independently validated calendar is connected.

## Safety and limits
Persisted source events remain provisional and do not authorize source approval, data promotion, ranking or recommendations. Existing source-trust registry and freshness policy remain separate mandatory gates. This adapter does not fetch ShareSansar, Chukul, ShareHub Nepal, Punji or other publishers, nor infer outages from missing records. Production admission and recommendation overrides remain disabled.
