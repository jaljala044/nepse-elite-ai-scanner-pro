# Steps 230–239: independent sector evidence reconciliation

1. Define typed observations with symbol, sector, source, publisher, capture/availability timestamps, effective interval, payload digest and source-record reference.
2. Validate publisher identity, source class, sector codes and payload hashes.
3. Require timezone-aware timestamps and reject availability before capture.
4. Exclude evidence not yet available at the decision cutoff.
5. Apply effective-dated membership using Nepal local calendar dates; reject future as-of dates.
6. Count independent publishers, not duplicate records from one publisher.
7. Withhold assignments when sources disagree.
8. Require two independent publishers and distinguish primary-class from secondary-only corroboration.
9. Report per-symbol source references, coverage and evidence states.
10. Add adversarial tests and point-in-time reclassification coverage.

States: corroborated_primary, corroborated_secondary, conflicting_sources, single_source_only, missing_evidence. Agreement is corroboration, not proof of official NEPSE membership. This module is descriptive and research-only; it does not feed scanner scores or trade actions. No sector membership is populated from assumptions.
