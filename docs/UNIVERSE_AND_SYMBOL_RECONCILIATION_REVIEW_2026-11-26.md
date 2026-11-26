# NEPSE target universe and historical symbol reconciliation — 2026-11-26

## Evidence policy
Project-level historical OHLCV evidence may be accepted from ShareHub, Chukul, ShareSansar and NepseAlpha. Preserve provider attribution, capture date, symbol/date, raw evidence URI/hash and any conflicts. Direct NEPSE evidence is not mandatory.

## Target universe audit
The existing candidate CSV contains 325 unique records: 278 Equity and 47 Mutual Fund. It contains no duplicate symbols. Therefore the earlier note claiming duplicate USLB and SYPNL rows is not supported by this file and is corrected here.

The 278/47 file is a candidate list, not a verified 281/47 manifest. Do not force the count.

## Additional active equity candidates requiring manifest review
The 2026-11-25 security snapshot includes:
- NESDO — security ID 8041 — NESDO Sambridha Laghubitta Bittiya Sanstha Limited — active — OHLCV file present.
- ULBSL — security ID 8063 — Upakar Laghubitta Bittiya Sanstha Limited — active — OHLCV file present.

Both are absent from the 2026-11-26 target candidate CSV. This identifies two concrete omissions to investigate. It does not yet identify a third missing equity. EDBL (ID 274) is already present in the candidate CSV and must not be counted as missing.

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
