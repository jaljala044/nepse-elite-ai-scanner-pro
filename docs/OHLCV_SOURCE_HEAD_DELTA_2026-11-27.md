# Pinned OHLCV audit — source-head delta check (2026-11-27)

## Scope and method

The original exception ledger remains anchored to the reproducible 2026-11-24 source commits:

- `nepse-smc-data`: `937cfcf93d78dfcf28a9f09bb13291447988157b`
- `nepse-history-starter`: `b60728d39f34e0f9e428675d817fd52ed2784da6`

A follow-up compared each source repository's pinned commit to its current `main` head and fetched both versions of every OHLCV path returned by the compare endpoint for row-level inspection. Current heads:

- `nepse-smc-data`: `54fbed963830dd9f064332770309f1ffda5ebe42`
- `nepse-history-starter`: `dfbf96f0322459b2910fe9c3edb4bd2b26efae2c`

The compare endpoint returned 300 changed-file entries for SMC and 27 for History Starter. The SMC response is at the endpoint's 300-entry response limit; therefore this targeted check is **not** a complete source-tree diff or a replacement for the original full 525-file audit.

## OHLCV file changes observed

The compare response identified two changed SMC OHLCV paths and five changed History Starter OHLCV paths. Row-level old/new comparisons found one changed row in each file; row counts and dates were unchanged.

| Repository | Symbol/date | Pinned row | Current-main row | Result |
| --- | --- | --- | --- | --- |
| nepse-smc-data | API 2026-11-19 | 331.0 / 334.2 / 330.2 / 333.0 / 26,717.0 | 331.0 / 334.2 / 330.0 / 331.8 / 105,340.0 | Changed source value; retain as unresolved conflict |
| nepse-smc-data | HRL 2026-11-19 | 483.0 / 488.0 / 480.0 / 486.0 / 18,817.0 | 483.0 / 488.0 / 480.0 / 483.9 / 49,184.0 | Changed source value; retain as unresolved conflict |
| nepse-history-starter | BGWT 2025-07-28 | 940 / 992 / 933.4 / 945.00 / 14,028 | 940 / 992 / 933.4 / 957.17 / 14,028 | Matches user-authoritative resolution |
| nepse-history-starter | MEHL 2025-07-28 | 471.1 / 480.5 / 460 / 470.83 / 29,753 | 471.1 / 480.5 / 460 / 475.63 / 29,753 | Matches user-authoritative resolution |
| nepse-history-starter | RAWA 2025-07-28 | 796 / 811 / 780.3 / 794.83 / 3,165 | 796 / 811 / 780.3 / 796.90 / 3,165 | Matches user-authoritative resolution |
| nepse-history-starter | RHGCL 2025-07-28 | 346.7 / 362 / 341.4 / 350.07 / 296,715 | 346.7 / 362 / 341.4 / 357.05 / 296,715 | Matches user-authoritative resolution |
| nepse-history-starter | ULHC 2025-07-28 | 509 / 515 / 495 / 504.00 / 32,288 | 509 / 515 / 495 / 510.75 / 32,288 | Matches user-authoritative resolution |

OHLCV field order in this table is Open / High / Low / Close / Volume. Current-main file blob SHAs:

| Repository/path | Pinned blob SHA | Current-main blob SHA |
| --- | --- | --- |
| SMC `API_OHLCV.csv` | `0e6a37baea92f4f0032980a46773d50b5f41c56c` | `d29d0442bac03704a80c25c87f23ba97515a9135` |
| SMC `HRL_OHLCV.csv` | `e5f3981f1a7dbcfb1518b2dac22afbde4ddc20de` | `6468714f8119afced04e029018225956212f991a` |
| Starter `BGWT_OHLCV.csv` | `ef024895eaed75d91c2de5fdfc05da4f25c9c9a0` | `c6ff57e0b142440606011f6a41cc8e1da52daded` |
| Starter `MEHL_OHLCV.csv` | `9de45b091c5111af919f1acd9928b63db979b120` | `7f3f9e4171c33d4e0df8c195680e3de11991c2a8` |
| Starter `RAWA_OHLCV.csv` | `91287e46895f6a3ec2fb14b8d80d9381776b3e04` | `bfa54d16d646522bcd6d96f759e75d4b4ca28ef0` |
| Starter `RHGCL_OHLCV.csv` | `c9c3173c3f97d114a172b16467c547a9d65bdd45` | `720917fc8f8b0c44906f1970f8813ee5e9e27a98` |
| Starter `ULHC_OHLCV.csv` | `15b90a3b841a84f0bbbff7cbf602a03e490dbd70` | `fe152229a2e2f3e94310215bb63cc7cd0d21c208` |

The five 2025-07-28 rows now agree with the values the user designated authoritative. Their ledger disposition remains `resolved_with_user_authoritative_evidence`; this source update is not independent authority and does not replace the user's supplied chart/floorsheet evidence.

API and HRL remain unresolved cross-source exceptions. Their current SMC values differ from the pinned SMC values, so the pinned baseline values must remain immutable in the ledger. No selection or correction is authorized from this delta alone.

## Audit disposition

- Do not rewrite the pinned audit ledger or its source commit references.
- Do not mutate raw source files.
- Keep the five user-authoritative resolutions intact.
- Keep API and HRL 2026-11-19 unresolved and quarantined.
- This targeted delta is a supplementary audit observation only. The full source-head refresh and all-525-file rerun remain outstanding because the SMC compare response was truncated at 300 changed files.
- No canonical promotion, training admission or scanner eligibility change is authorized.
