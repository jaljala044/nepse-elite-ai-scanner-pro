# Priority 95 — Resolve four unmapped Yonepse stock IDs (2026-11-26)

## Result

The four stock IDs previously unresolved in the 2026-11-24 Yonepse floorsheet mapping audit are now matched to symbols and security names in the repository's dated 2026-11-25 NEPSE security-ID snapshot:

| Security ID | Symbol | Security name | Snapshot status | OHLCV file present |
|---:|---|---|---|---|
| 8111 | HIDCLP | Hydorelectricity Investment and Development Company Limited Promoter | A | yes |
| 469 | NIMBPO | Nepal Investment Mega Bank Ltd. Promoter Share | A | yes |
| 700 | HEIP | Himalayan Everest Insurance Limited Promoter | A | yes |
| 661 | NMLBBLP | Nerude Mirmire Laghubitta Bittiya Sanstha Limited Promoter | A | yes |

Source snapshot: `data/reference/nepse_security_id_snapshot_2026-11-25.csv`, snapshot date 2026-11-25, source blob `eed3bbb3152e83d4abcb0ee8d03d720c33c63cef`.

## Disposition

- **Mapping coverage:** 4/4 previously unmapped IDs now have dated snapshot symbol/name matches.
- **Classification:** all four names explicitly identify promoter/promoter-share securities. They must not be mistaken for ordinary public-share symbols or added to the standard active-equity scanner universe solely because the security snapshot marks them active and an OHLCV file exists.
- **Raw evidence:** preserve their floorsheet rows and OHLCV artifacts for auditability. Do not delete or rewrite raw records.
- **Historical identity limitation:** this is a single dated snapshot. It does not establish the complete effective-dated lifecycle, conversion/merger history, or whether these instruments belong in a separate promoter-share coverage universe.
- **No canonical promotion:** no change to the canonical target universe, training set, or raw market data is authorized by this mapping result.

## Follow-up

1. Add an explicit instrument-subtype policy for promoter shares versus ordinary public shares in the universe manifest.
2. Reconcile the four IDs against dated historical security-master snapshots and corporate-action/listing notices.
3. Report ordinary-equity and promoter-share coverage separately so raw floorsheet completeness is not confused with scanner-universe membership.

## Reproducibility

The mapping was resolved by exact security-ID matches against the committed 2026-11-25 snapshot. No external source inference was used to guess the four symbols.
