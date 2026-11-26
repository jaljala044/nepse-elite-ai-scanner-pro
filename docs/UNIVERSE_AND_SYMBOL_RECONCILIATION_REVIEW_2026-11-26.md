# NEPSE target universe and historical symbol reconciliation — 2026-11-26

## Evidence policy
Project-level historical OHLCV evidence may be accepted from ShareHub, Chukul, ShareSansar and NepseAlpha. Preserve provider attribution, capture date, symbol/date, raw evidence URI/hash and any conflicts. Direct NEPSE evidence is not mandatory.

## Target universe audit
The existing candidate CSV contains 325 unique records: 278 Equity and 47 Mutual Fund. It contains no duplicate symbols. Therefore the earlier note claiming duplicate USLB and SYPNL rows is not supported by this file and is corrected here.

The 278/47 file is a candidate list, not a verified 281/47 manifest. Do not force the count.

## Additional active equity candidates requiring manifest review
The 2026-11-25 security snapshot and the 281-row provisional equity coverage file identify three additional symbols absent from the 2026-11-26 rendered company-list capture:
- NESDO — security ID 8041 — NESDO Sambridha Laghubitta Bittiya Sanstha Limited — status A in the 2026-11-25 security snapshot — OHLCV file present.
- ULBSL — security ID 8063 — Upakar Laghubitta Bittiya Sanstha Limited — status A in the 2026-11-25 security snapshot — OHLCV file present.
- YMHL — security ID 9342 — Yambaling Hydropower Limited — status A in the 2026-11-25 security snapshot — OHLCV file present.

A fresh row-level comparison confirms that the 281-row 2026-11-26 company-list CSV contains only 278 unique active-equity symbols because USLB is repeated once and SYPNL is repeated twice. All 278 unique symbols match the 278-symbol candidate-equity list. The separate 281-symbol provisional OHLCV coverage set differs by exactly NESDO, ULBSL and YMHL. The dated security snapshot records all three as status A, but that snapshot does not itself prove instrument type or effective lifecycle dates. Treat all three as strong candidates requiring an authoritative instrument-type/status cross-check; do not silently promote them to the canonical 281-equity register.

EDBL (ID 274) is already present in both the 278-symbol list and the 281-symbol provisional OHLCV coverage set and must not be counted as missing.

Secondary evidence: NepseAlpha's listed-securities page reports active equity records and identifies instrument/status fields; NEPSEAlpha live-market results include EDBL. NEPSEDATA's 26 Nov 2026 development-bank list includes EDBL. These are corroborating leads, not a complete 281-member manifest:
- https://nepsealpha.com/traded-stocks/
- https://nepsedata.com/stock/development-banks/

## Historical filename reconciliation
Eight of the 37 unmatched filenames are now confirmed as URL-encoding aliases of exact security-snapshot symbols:
- GBILD84~2F85 → GBILD84/85 (ID 9168)
- GBILD86~2F87 → GBILD86/87 (ID 8004)
- MND84~2F85 → MND84/85 (ID 4969)
- NICAD85~2F86 → NICAD85/86 (ID 2825)
- NIFRAUR85~2F86 → NIFRAUR85/86 (ID 9141)
- NMBD87~2F88 → NMBD87/88 (ID 4963)
- NMBD89~2F90 → NMBD89/90 (ID 9180)
- NMBUR93~2F94 → NMBUR93/94 (ID 8105)

These are debt instruments, not equity or mutual-fund targets. Their original filenames must remain as aliases; do not rename or rewrite raw OHLCV files. The updated review CSV records these eight as resolved_filename_encoding and leaves 29 unresolved historical identities.

## Remaining work
1. Establish the exact 281 equity list by reconciling the dated provider instrument tables symbol-by-symbol; identify the third discrepancy rather than guessing.
2. Verify the effective listing/status lifecycle for NESDO and ULBSL and then update a versioned candidate manifest only with evidence.
3. Research the remaining 29 historical aliases against approved providers and archived security catalogues; retain unresolved rows as unresolved.
4. Acquire NICEF history from first actual trading date; do not expect pre-listing rows.
5. Build and run separate per-provider historical coverage reports against a verified instrument manifest and an evidence-backed session calendar.

## Guardrails
- No synthetic OHLCV rows.
- No raw price mutation or alias-based overwrite.
- No treating a candidate list or a current trading table as a complete historical lifecycle registry.
- No combining separate provider rows into one coverage numerator.


## Dated listing and equity-class evidence expansion — 2026-11-26

The three candidates now have multiple provider records supporting their equity classification and listing/trading-start timeline. This is stronger than a current active-security snapshot alone:

| Symbol | Security ID (2026-11-25 snapshot) | Listing date | First trading date | Classification evidence |
|---|---:|---|---|---|
| NESDO | 8041 | 2022-03-27 | 2022-03-28 (secondary profile reference) | ShareSansar listing notice links the NEPSE listing PDF; ShareHub and Laganilab classify it as active microfinance equity |
| ULBSL | 8063 | 2022-05-26 | 2022-05-27 | Merolagani reports NEPSE's listing and first trade and assigns ULBSL; ShareHub and Laganilab corroborate active microfinance classification |
| YMHL | 9342 | 2026-06-19 | 2026-06-22 | ShareSansar listing notice links the NEPSE listing PDF; NepseBajar and NepseLabs corroborate dates and hydropower equity classification |

Source URLs and the exact claim each supports are stored in `data/reference/nepse_equity_candidate_additions_2026-11-26.json` (commit `b78a9fca080b0763d8ffdcae2d6e1e826ab5ae5c`). The current IDs also appear in the dated 2026-11-25 security snapshot and the 2026-11-19 NEPSE OHLCV capture. The latter supports contemporary symbol/ID association, not proof of unbroken historical stable-ID continuity.

**Decision:** the three records are now well-supported active-equity additions for the candidate manifest, not mutual funds. However, do not claim the full 281-member universe is verified: full dated membership reconciliation, instrument-ID continuity, and complete primary-source provenance are still open. The canonical target manifest remains unpromoted pending those gates; no raw OHLCV files or finalized historical records were changed.
