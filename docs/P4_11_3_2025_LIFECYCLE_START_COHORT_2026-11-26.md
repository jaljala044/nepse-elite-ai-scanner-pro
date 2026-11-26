# P4.11.3 — 2025 equity lifecycle start cohort — 2026-11-26

## Scope and method

The 2026 observed-date audit identified 18 equities whose pinned OHLCV files first begin during 2025 while the lifecycle register had no populated start date. Each file's first row was inspected directly; all 18 archive first rows have positive volume. Dated secondary reporting and listing notices were checked to distinguish scheduled commencement from actual first execution.

The register now records a supported first-trade date for all 18. Evidence remains secondary/provider evidence, not raw exchange contract-level floorsheet proof.

## Cohort disposition

| Symbol | First trade date entered | First archive row | Volume | Evidence basis / disposition |
|---|---|---|---:|---|
| GMLI | 2025-02-09 | 2025-02-09 | 490 | Merolagani first special pre-open transaction report; archive match |
| NMIC | 2025-04-08 | 2025-04-08 | 210 | Merolagani first special pre-open transaction report; archive match |
| CREST | 2025-04-10 | 2025-04-10 | 210 | Insurance Khabar scheduled trading notice; archive match |
| OMPL | 2025-05-04 | 2025-05-04 | 160 | NepseLabs and SRAN independently record trading start / first trade; archive match |
| PURE | 2025-05-27 | 2025-05-27 | 120 | Merolagani first special pre-open transaction report; archive match |
| TTL | 2025-07-17 | 2025-07-17 | 590 | Merolagani confirms first execution; 16 July scheduled session did not match |
| SANVI | 2025-07-20 | 2025-07-20 | 350 | Merolagani first special pre-open transaction report; archive match |
| BHCL | 2025-08-20 | 2025-08-20 | 320 | Merolagani first special pre-open transaction report; archive match |
| HIMSTAR | 2025-09-01 | 2025-09-01 | 60 | Merolagani confirms no match on 31 Aug and next-day debut required; archive confirms positive-volume row on 1 Sep |
| MABEL | 2025-11-04 | 2025-11-04 | 110 | ShareSansar notice states trading commencement; archive match; conflicting month typo in a debut article not relied upon |
| DHEL | 2025-11-06 | 2025-11-06 | 460 | ShareSansar notice states trading commencement; archive match |
| SAGAR | 2025-11-09 | 2025-11-09 | 100 | Merolagani debut report and listing notice; archive match |
| BUNGAL | 2025-11-10 | 2025-11-10 | 190 | ShareHub/Mero Lagani first-trading report; archive match |
| BANDIPUR | 2025-11-11 | 2025-11-11 | 270 | ShareHub/Mero Lagani first-trading report; archive match |
| SWASTIK | 2025-11-11 | 2025-11-11 | 30 | ShareHub/Mero Lagani first-trading report; archive match |
| JHAPA | 2025-11-16 | 2025-11-16 | 60 | ShareSansar commencement notice and SRAN first-trade record; archive match |
| SAIL | 2025-11-23 | 2025-11-24 | 250 | SRAN first-trade record and ShareSansar scheduled commencement report 23 Nov; archive begins one session later — keep discrepancy open |
| SYPNL | 2025-12-10 | 2025-12-10 | 300 | Nepalytix first-trade report; archive match |

## Source references

- GMLI: https://merolagani.com/NewsDetail.aspx?newsID=111373
- NMIC: https://eng.merolagani.com/NewsDetail.aspx?newsID=113328
- CREST: https://english.insurancekhabar.com/crest-micro-life-shares-will-be-trading-from-tomorrow-what-is-the-opening-range-2/
- OMPL: https://nepselabs.com/stocks/OMPL ; corroborating first-trade field: https://sran.com.np/companies/ompl
- PURE: https://www.merolagani.com/NewsDetail.aspx?newsID=114869
- TTL: https://eng.merolagani.com/NewsDetail.aspx?newsID=116573
- SANVI: https://eng.merolagani.com/NewsDetail.aspx?newsID=116647
- BHCL: https://eng.merolagani.com/NewsDetail.aspx?newsID=117621
- HIMSTAR: https://eng.merolagani.com/NewsDetail.aspx?newsID=117902
- MABEL: https://www.sharesansar.com/eventdetail/listing-ipo-share-of-mabilung-energy-limited-mabel-2025-11-03
- DHEL: https://www.sharesansar.com/eventdetail/listing-ipo-share-of-daramkhola-hydro-energy-limited-dhel-2025-11-05
- SAGAR: https://eng.merolagani.com/NewsDetail.aspx?newsID=120012
- BUNGAL: https://sharehubnepal.com/news/99821-mero-lagani-bungal-hydro-limited-first-trading-session-nepse
- BANDIPUR / SWASTIK: https://sharehubnepal.com/news/100208-mero-lagani-bandipur-cable-car-swastik-microfinance-first-trading
- JHAPA: https://www.sharesansar.com/eventdetail/listing-ipo-share-of-jhapa-energy-limited-jhapa-2025-11-14 ; SRAN first-trade record: https://sran.com.np/companies/jhapa
- SAIL: https://sran.com.np/companies/sail ; ShareSansar listing/commencement notice: https://www.sharesansar.com/eventdetail/listing-ipo-share-of-shreenagar-agritech-industries-limited-sail-2025-11-21
- SYPNL: https://nepalytix.com/news/sy-panel-nepal-makes-market-debut-at-rs-31980-in-special-pre-open-session

## Important exceptions and controls

1. **SAIL:** source-reported first trade is 23 Nov while the pinned OHLCV file starts 24 Nov. This is not normalized away. Obtain the 23 Nov complete floorsheet or exchange trade confirmation and repair only through a separately versioned, provenance-backed derived dataset if the missing trade is confirmed.
2. **HIMSTAR:** 31 Aug scheduled debut failed due to unmatched orders; the 1 Sep archive row is consistent with the stated next-day retry. Do not treat 31 Aug as an executed session for HIMSTAR.
3. **TTL:** scheduled 16 July attempt did not match; first execution occurred 17 July. The register records actual first trade, not scheduled date.
4. **MABEL / SAGAR / JHAPA:** some secondary debut articles contain an inconsistent month in their narrative body. The register relies on date-specific listing/commencement records plus matching archive first-positive-volume dates; the inconsistency is preserved in the source note rather than hidden.
5. No contract-level floorsheet payloads were acquired in this batch. A positive-volume archive row is a project observation, not independent exchange execution proof.
6. No raw OHLCV was modified, no missing row was synthesized, and no historical price series was spliced.

## Outcome

- 18 additional lifecycle starts populated from the 2025 cohort.
- Cohort register boundary count is 18/18, with SAIL's first-trade/archive mismatch explicitly quarantined.
- Combined lifecycle input now targets 281 rows; the PR's validation will report the total populated start count.
- Historical security-ID continuity, full expected-session completeness, corporate-action price-basis treatment, raw row provenance and liquidity remain separate Stage 1 gates.
- No canonical/training promotion and no BUY eligibility change.
