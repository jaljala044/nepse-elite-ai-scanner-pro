# Steps 310–319 — Calendar-backed source data-quality gate

## Scope
Research-only adapter connecting independently reviewed exchange-session evidence and explicitly reviewed source capture policies to OHLCV/floorsheet data-quality diagnostics.

## Ten implementation steps
1. Consume only point-in-time reviewed calendar sessions with source ID and payload SHA-256.
2. Reject future, duplicate, unreviewed, or lineage-incomplete calendar rows.
3. Require explicit per-source/per-dataset expected-session policies; no weekday or daily-cadence inference.
4. Require reviewed policy owner, source, dataset, session list, and freshness threshold.
5. Distinguish fresh capture, stale capture, missing/delayed capture, unverified calendar, and explicitly declared outage.
6. Preserve source correction/supersession versions and select only versions available at the historical cutoff.
7. Reconcile cross-source observations without majority-vote canonical promotion; retain conflicting values.
8. Keep ShareSansar, Chukul, ShareHub Nepal, Punji, Merolagani, NepseAlpha, ChartNepali, and Bullhouse as unreviewed adapter candidates; no hostnames are guessed.
9. Produce conservative HIGH/LOW coverage quality diagnostics with explicit missing/conflict reasons.
10. Apply read-only quality annotations to OHLCV and floorsheet records; production admission and scanner recommendations remain disabled.

## Important semantics
- A missing capture is not evidence of an outage. An outage requires an explicit, point-in-time lifecycle event.
- A missing floorsheet row is not a zero-trade observation.
- Two or more agreeing sources can be reported as agreement, but this module never selects a canonical value.
- HIGH means only that the supplied diagnostic inputs pass these coverage checks. It is not NEPSE first-party attestation, publisher approval, independent source ownership proof, or canonical promotion.
- This module is not wired to production scan routes. No live calendar, capture policy, source records, correction history, or source adapters are populated by this PR.
