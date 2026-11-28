# Steps 230–239: independent sector evidence reconciliation

1. Define a typed evidence observation contract with symbol, sector, source, publisher, capture/availability timestamps, effective interval, payload digest and source-record reference.
2. Validate publisher/source identity, sector codes, payload hashes and source classes.
3. Require timezone-aware capture and availability timestamps; reject availability preceding capture.
4. Apply point-in-time decision cutoffs and exclude evidence not yet available.
5. Apply effective-dated membership using the requested Nepal local calendar date.
6. Count independent publishers, not duplicated records or multiple pages from one publisher.
7. Withhold sector assignments on disagreement; do not rank sources silently.
8. Require at least two independent publishers for corroborated membership; distinguish primary-class corroboration from secondary-only corroboration.
9. Produce per-symbol source references, coverage and explicit evidence quality states.
10. Add adversarial tests and document that corroboration does not establish official NEPSE membership.

## Output states
- `corroborated_primary`: independent publishers agree and at least one evidence class is primary NEPSE/CDSC/issuer.
- `corroborated_secondary`: independent secondary sources agree, but no primary-class evidence exists.
- `conflicting_sources`: source publishers disagree; sector code withheld.
- `single_source_only`: fewer than two independent publishers; sector code withheld.
- `missing_evidence`: no eligible point-in-time evidence.

This module is descriptive and research-only. It is not wired as a production score or BUY/SELL input. Registry reviewer HMAC and publisher reconciliation remain distinct controls. No sector membership is populated from assumptions.
