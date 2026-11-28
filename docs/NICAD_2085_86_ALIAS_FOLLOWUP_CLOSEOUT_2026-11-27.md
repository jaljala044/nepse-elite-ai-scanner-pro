# NICAD 2085/86 historical alias — supplementary follow-up closeout

Date: 2026-11-27

## Disposition

The supplementary debenture alias follow-up is **closed as unverified and retained**. The historical ticker `NICAD~2085~2F86` is a probable name/format alias for `NICAD85/86` (candidate NEPSE security ID `2825`), but exact ticker-to-security identity equivalence and effective dates are not proven. Per the agreed supplementary-instrument scope, no further verification work is required.

This is not an identity resolution. Do not rewrite the historical ticker, merge its history, assign stable ID 2825 to it, or include it in an equity scanner universe.

## Preserved raw history

Both OHLCV repositories contain byte-identical files for each of the two ticker spellings:

| Repository path | Rows | First row | Last row | Git blob SHA |
| --- | ---: | --- | --- | --- |
| `NICAD~2085~2F86_OHLCV.csv` | 2 | 2024-05-07, O/H/L/C 1000.00/1000.00/1000.00/1000.00, volume 900 | 2024-05-08, 1014.00/1015.20/1014.00/1015.10, volume 65 | `c4ce9b17cd34190be4f91ddcf800a42d5c154809` |
| `NICAD85~2F86_OHLCV.csv` | 312 | 2024-05-09, 1010.10/1020.00/1010.10/1015.50, volume 210 | 2026-10-15, 1141.00/1141.00/1141.00/1141.00, volume 100 | `5e22cc7e22d08f5b725f2dcc3c3caf098fa99b68` |

The same paths and blob SHAs were independently fetched from both `jaljala044/nepse-smc-data` and `jaljala044/nepse-history-starter`. The two filenames are distinct source histories, not permission to concatenate them. Preserve the original two-row history separately from the 312-row history.

## Identity evidence and limits

- CDSC register row 55 supports the instrument label `NICAD85/86` and ISIN `NPE029A11037`.
- A secondary listing maps `NICAD 85/86` to candidate NEPSE ID `2825`.
- NepseAlpha financial-report and announcement pages provide name/format corroboration for the probable alias.
- No acquired source establishes that the historical file stem `NICAD~2085~2F86` is exactly the same security as `NICAD85/86`, nor its stable ID or effective interval.

Sources: https://cdsc.com.np/BondandDebenture · https://bishaludash.com.np/NEPSE-Api/templates/listedCompany.html · https://www.nepsealpha.com/financials-reports?page=40 · https://www.nepsealpha.com/announcement?page=418

## Data and scanner controls

- Raw source files remain untouched.
- The unmatched-symbol review continues to classify `NICAD~2085~2F86` as `unresolved_historical_identity`.
- The identity-evidence JSON records `follow_up_disposition=closed_unverified_alias_retained`, both repository paths, blob SHAs, row counts and boundary rows.
- No canonical identity mapping, history splice, price promotion or scanner admission is authorized.
- No further supplementary alias follow-up is required unless new primary evidence is supplied.


## CI dependency alignment — 2026-11-27

This documentation PR is now based on `research/issue-20-historical-segment-eligibility` at `86ad9200aa1a427bab3d03b2e25ddb8381ee81ea`, which supplies the evaluator module imported by the repository's historical-segment regression test. The earlier backend run `45932272657` tested the previous `main` base and failed on that missing module; it does not validate the retargeted PR composition. The separate historical identity regression run `45932272651` passed for the identity evidence change. The alias remains unresolved and retained; no identity mapping, history splice, or scanner admission is authorized. A new exact-head backend run is required.
