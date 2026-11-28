# Steps 290–299 — Source reliability and historical lifecycle

## Delivered scope
1. Added a candidate catalogue for ShareSansar, Chukul, ShareHub Nepal, Punji, Merolagani, NepseAlpha, ChartNepali and Bullhouse Investment.
2. Kept every candidate unreviewed, unapproved and without guessed hostnames.
3. Added append-only source lifecycle event batch validation and deterministic SHA-256 manifests.
4. Added timezone-aware capture, receipt, publication and effective-date cutoff validation.
5. Added hostname-change events that require distinct old/new host values and trigger review.
6. Added ownership-group-change events that preserve both old and new identifiers and trigger review.
7. Added explicit source suspension, recovery, outage-start and outage-resolution transitions.
8. Added capture-success validation requiring HTTPS provenance and a payload SHA-256.
9. Added per-source successful-capture coverage against caller-supplied verified session dates; no weekday/calendar inference.
10. Added historical replay tests for future-event exclusion, corrections, outage/suspension, missing sessions and fail-closed production status.

## Integration and evidence boundaries
This is a research adapter and deterministic replay function. It is not yet connected to live source acquisition, the persistent evidence store, the scanner API or production readiness. Existing reviewed source registry remains authoritative for actual source admission; this module does not approve candidate sources or populate host/ownership claims. ShareSansar archive evidence already recorded elsewhere in the repository remains a research lead, not an endorsement of the publisher or an extracted market-data validation result. Chukul, ShareHub Nepal and Punji hostnames are deliberately not guessed.

Verified session dates must come from the separately validated NEPSE calendar evidence pipeline. If no dates are supplied, session coverage is null and no outage is inferred. A successful retrieval is not proof of correctness, completeness, exchange authority or redistribution rights. HMAC/signature and hash integrity do not prove legal ownership or authenticity.

## Validation
Ten synthetic unit tests cover the ten-step scope. CI results are pending until GitHub Actions runs against this branch. No live market data, source outage, publisher affiliation or calendar date is newly verified by this change. Production admission and recommendation overrides remain disabled.
