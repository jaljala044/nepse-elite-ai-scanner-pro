# P4.11 lifecycle / first-trade evidence batch — 2026-11-26

## Scope and baseline

The 281-row equity lifecycle input had 9 populated `valid_from` values and 272 blank/unverified values. This batch adds only dates supported by dated secondary-source reporting and/or a documented listing notice plus matching first-positive-volume project archive observation.

## Added records

| Symbol | First trade / first positive-volume date | Evidence status |
|---|---|---|
| BENH | 2026-10-15 | `verified_secondary_first_trade_archive_match` |
| ECL | 2026-07-17 | `verified_secondary_notice` |
| KAHL | 2026-07-02 | `verified_secondary_first_trade_archive_match` |
| MEPDL | 2026-08-12 | `verified_secondary_notice` |
| NESDO | 2022-03-28 | `verified_secondary_notice` |
| SAPIL | 2026-08-13 | `verified_secondary_first_trade_archive_match` |
| SGHL | 2026-07-02 | `verified_secondary_first_trade_archive_match` |
| SNORL | 2026-06-26 | `verified_secondary_first_trade_archive_match` |
| SOPL | 2026-06-08 | `verified_secondary_first_trade_archive_match` |
| TPKHL | 2026-06-22 | `verified_secondary_notice` |
| ULBSL | 2022-05-27 | `verified_secondary_notice` |

The register stores the effective first executed-trade/observed start in `valid_from`, not the IPO listing date or scheduled commencement date. The notes retain the distinction and identify the evidence limitations.

## Specific controls

- **BENH:** scheduled commencement 2026-10-14; dated Merolagani reporting describes first special pre-open execution on 2026-10-15. Keep 2026-10-14 as an unresolved execution check; do not synthesize a bar.
- **NESDO / ULBSL:** listing and first-trade dates have multiple secondary-provider corroboration. No raw exchange contract-level floorsheet was captured.
- **ECL:** 2026-07-17 is the reviewed commencement/first-positive-volume boundary. A separate 2026-07-24/25 date-shift candidate remains quarantined and is not resolved by this record.
- **MEPDL / TPKHL:** listing notices plus matching project archive first-positive-volume dates; not independently confirmed against complete floorsheets.
- **SAPIL / KAHL / SGHL / SNORL / SOPL:** dated debut/commencement reporting and archive boundary alignment; secondary evidence only.

## Evidence source references

- **BENH:** https://eng.merolagani.com/NewsDetail.aspx?newsID=131897
- **ECL:** https://www.sharesansar.com/eventdetail/listing-ipo-share-of-everest-colour-limited-ecl-2026-07-16
- **KAHL:** https://eng.merolagani.com/NewsDetail.aspx?newsID=128111
- **MEPDL:** https://www.sharesansar.com/eventdetail/listing-ipo-share-of-mount-everest-power-development-limited-mepdl-2026-08-11
- **NESDO:** https://www.sharesansar.com/eventdetail/listing-ipo-shares-of-nesdo-sambridha-laghubitta-bittiya-sanstha-limited-nesdo-2022-03-27
- **SAPIL:** https://merolagani.com/NewsDetail.aspx?newsID=129634
- **SGHL:** https://eng.merolagani.com/NewsDetail.aspx?newsID=128111
- **SNORL:** https://nepalisharemarket.com/news/IPO/snow-rivers-limited-snorl-commences-secondary-market-trading-with-first-transaction-in-pre-open-session
- **SOPL:** https://cdn.merolagani.com/NewsDetail.aspx?newsID=127198
- **TPKHL:** https://www.sharesansar.com/index.php/eventdetail/listing-ipo-share-of-taksar-pikhuwa-khola-hydropower-limited-tpkhl-2026-06-19
- **ULBSL:** https://eng.merolagani.com/NewsDetail.aspx?newsID=81372

Additional listing notices and cross-checks are recorded in `reference/later_start_equity_lifecycle_validation_2026-11-26.md` and `data/reference/nepse_equity_candidate_additions_2026-11-26.json` in the data/research repository.

## Outcome

- Lifecycle input remains 281 rows / 281 unique equity symbols.
- 11 additional start dates entered in this batch (8 later-start cases plus BENH, NESDO and ULBSL; existing records were not duplicated).
- Expected populated `valid_from` count after this batch: 20 of 281. Evidence-status values are restricted to the validator's approved vocabulary.
- Evidence tier remains secondary/project-observation; no exchange-authoritative certification.
- No raw OHLCV mutation, no synthesized rows, no canonical/training promotion, and no BUY eligibility change.
- Full session-level floorsheet completeness, corporate-action intervals, historical security-ID continuity, and later-session OHLCV provenance remain blocked.
