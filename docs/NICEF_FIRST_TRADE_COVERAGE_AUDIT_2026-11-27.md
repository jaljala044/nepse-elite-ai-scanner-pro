# NICEF first-trade and historical-coverage audit — 2026-11-27

## Decision

NICEF is a listed closed-end mutual fund, but the freely accessible ShareSansar-derived daily archive inspected for this audit contains **no NICEF price row and no NICEF symbol-history endpoint** through its latest published session, 2026-11-26. The archive's complete symbol index contains 525 symbols and does not include NICEF.

**Do not manufacture an OHLCV row or infer that the expected first-trading date was an actual trade.** Close the outstanding NICEF first-trading-date OHLCV follow-up as an evidence-availability result: no free-provider trading observation was found in this archive through 2026-11-26. Retain NICEF in the existing 47-fund candidate set and preserve the listing evidence. Reopen only if a later freely accessible source supplies an actual dated trade record.

## Listing evidence

- Merolagani announcement 68146 identifies NICEF (NIC ASIA Equity Opportunity Fund) and states that 100,000,000 units were listed on NEPSE on 2026-11-04: https://merolagani.com/AnnouncementDetail.aspx?id=68146
- ShareSansar's 2026-11-04 listing report states that trading was **expected** to begin Thursday; it does not report an executed trade or an OHLCV row: https://www.sharesansar.com/newsdetail/nic-asia-equity-opportunity-fund-have-been-listed-on-nepse-2026-11-04

Listing date and expected commencement are not proof of first actual trading date.

## Reproducible free-archive check

Source: OmitNomis/ShareSansarScraper, a public, unofficial archive of ShareSansar daily price tables. Its README describes daily CSVs under `docs/Data/YYYY_MM_DD.csv`, a symbol index, and a per-symbol history JSON endpoint. Data is sourced from ShareSansar; this is corroboration, not NEPSE-primary evidence.

Archive metadata at the audit time:

- `docs/api/meta.json` blob SHA: `144edc92f00b3e7f5b6e312b25fb2d9c5ac2a926`
- Metadata: last updated 2026-11-26; 941 archived trading days; 525 symbols; 355 symbols in the latest session.
- `docs/api/symbols.json` blob SHA: `14bd398265111dc6852b81132bace1992027ef5d`
- The complete 525-symbol index does not contain `NICEF`.
- `docs/api/history/NICEF.json` is absent (GitHub contents lookup returned 404).

Daily CSV checks: exact symbol-column equality (`Symbol == NICEF`) returned zero rows in every file below.

| Session date | CSV blob SHA |
|---|---|
| 2026-11-04 | `aa11f2684fb3fad1de8fcad57e54859e3af71982` |
| 2026-11-05 | `b53a7c5178ce83af9fe8cc2408d51e762b1f2670` |
| 2026-11-06 | `24536e94c677645f1f27b9670ab06d83af9f1768` |
| 2026-11-13 | `9b16558fd72dd630a606b0bdc5540fd08504eef3` |
| 2026-11-17 | `53f885bd609d61952a01c8f066510ccd918f46ec` |
| 2026-11-18 | `e5901695dac2c0ac2ed7dfea77494052ed99bf30` |
| 2026-11-19 | `4177a091f7ce5900b2a1e745ab27ca06781e2dd1` |
| 2026-11-20 | `97236741d2e26c55c3f3a88c151d778e448c8c35` |
| 2026-11-23 | `2091c9d42f98f36ddb89f77639fbb7319c7b6b7a` |
| 2026-11-24 | `4f25e1913c3e3c681cb660b78587aab90b500867` |
| 2026-11-25 | `19a3ff67f9a33cb55678521de5528b4e4efed2ac` |
| 2026-11-26 | `bb32701ba263096f8f51741da71c06bb4e85504f` |

The archive's README: https://github.com/OmitNomis/ShareSansarScraper/blob/master/README.md

## Limitations and handling

- The archive is unofficial and mirrors ShareSansar; absence means no observation in this provider archive, not proof that NEPSE had no trade.
- ShareSansar's listing article only forecasts the first session; no first-trade date is certified here.
- No OHLCV values, zero-volume placeholders, floorsheet contracts, or synthetic dates were added.
- No raw repository data was changed.
- NICEF remains a mutual-fund candidate; its historical OHLCV coverage remains zero/unknown until a real dated record is acquired from an approved provider.
- This audit does not certify the complete 47-fund universe or the 281-equity manifest.


## CI dependency alignment — 2026-11-27

The documentation PR is now based on `research/issue-20-historical-segment-eligibility` at `86ad9200aa1a427bab3d03b2e25ddb8381ee81ea`, so the existing historical-segment test and its evaluator module are present together. The earlier backend run `45930820570` tested the old `main` base and failed with `ModuleNotFoundError` for that module; it is not a result for this retargeted PR composition. No NICEF evidence disposition or raw market data was changed by this dependency alignment. A new exact-head run is required after this documentation update.
