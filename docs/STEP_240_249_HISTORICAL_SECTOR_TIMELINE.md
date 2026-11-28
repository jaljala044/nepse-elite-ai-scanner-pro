# Steps 240–249: historical sector timeline and identity continuity

1. Add immutable sector classification, reclassification, symbol-change and corporate-action-link events.
2. Bind every event to a stable, independently verified security ID; reject unknown IDs.
3. Preserve source, publisher, source class, evidence reference and payload SHA-256.
4. Separate capture/availability timestamps from effective dates for point-in-time replay.
5. Apply only events available by decision cutoff and effective on the requested Nepal-local date.
6. Keep symbol changes as aliases on stable security identity; never join by ticker text alone.
7. Require independent publisher corroboration for sector and symbol alias claims.
8. Withhold conflicting and single-publisher claims; preserve missing evidence states.
9. Link corporate-action IDs as references only; do not infer adjustment factors or continuity.
10. Add historical replay, look-ahead, identity, conflict and production-gate tests.

This is an in-memory research adapter, not a persistent database, official identity master, or live scanner input. Known security IDs must come from a separately verified source. No corporate action, ticker alias, sector mapping, adjusted price, score, or trade recommendation is inferred.
