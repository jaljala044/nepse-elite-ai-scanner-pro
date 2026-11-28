# Priority 1 — review of 44 populated lifecycle starts (2026-11-27)

## Decision

The 281-row current-equity lifecycle input was re-read and structurally audited. **44/281 starts are populated, all 44 remain secondary-source records; 237/281 remain blank and unverified.** No first-trade date was upgraded to primary from this review. The review is evidence inventory and exception triage, not approval for canonical admission, backtesting or trading decisions.

## Pinned input and reproduced counts

- Input: `data/reference/nepse_equity_lifecycle_coverage_input_2026-11-26.csv`
- Git blob: `be1567fadb69bdca11b0d7890da10ebc8df96d51`
- Rows: 281; unique symbols: 281; unique current security IDs: 281.
- Populated `valid_from`: 44; blank/unverified: 237.
- Populated dates: 44 valid ISO `YYYY-MM-DD` values; 44 non-empty evidence URIs; 44 non-empty rationale notes; no duplicate symbols among populated records.
- Evidence statuses: 30 `verified_secondary_first_trade_archive_match`; 14 `verified_secondary_notice`; zero `verified_primary_notice`.
- Populated start-date years: 2022: 2; 2024: 2; 2025: 18; 2026: 22.

These labels describe the project's current secondary evidence register. They do not certify first execution from an exchange-origin contract record.

## Eight records retained for explicit exception review

| Symbol | Recorded date | Review note |
|---|---|---|
| APHL | 2026-06-10 | Scheduled 2026-06-09 attempt reportedly did not match; first execution reported next day. Keep scheduled and executed dates distinct. |
| BENH | 2026-10-15 | Scheduled commencement reported for 2026-10-14; first positive-volume archive row is 2026-10-15. Official NEPSE per-security history captured below provides direct activity evidence, but does not independently prove completeness before 2026-10-14. |
| CREST | 2025-04-10 | Secondary commencement notice and first positive-volume archive row agree; no contract-level exchange payload captured. |
| ECL | 2026-07-17 | Start date agrees with the cited notice and archive boundary; the separate 2026-07-24/25 provider date-shift exception remains unresolved. |
| HIMSTAR | 2025-09-01 | 2025-08-31 scheduled attempt reportedly failed to match; 2025-09-01 is the reported first execution and archive match. |
| MABEL | 2025-11-04 | Dated listing notice and archive match; a conflicting month in another debut article is preserved in the note. |
| SAIL | 2025-11-23 | Secondary sources report first trade on 2025-11-23, while the pinned OHLCV archive begins 2025-11-24. Preserve the one-session discrepancy; do not shift the lifecycle date. |
| TTL | 2025-07-17 | 2025-07-16 scheduled pre-open reportedly had no matched trade; 2025-07-17 is the reported first execution and archive match. |

The remaining 36 populated records have no duplicate-symbol/date or missing-URI/note issue in this structural pass. Their linked source content has not been re-fetched and independently authenticated as part of this review.

## Primary-source observation found for BENH

The repository contains a captured NEPSE per-security history response for BENH:

- Path: `data/evidence/raw/nepse/security-history/2026-10-05_to_2026-11-26/symbols/BENH/response-01.bin`
- SHA-256 recorded in the capture manifest: `76e420614abd0a095bb6b3954d16b2ef4bb758b592d47b0cd999eda8d93215cb`
- Git blob: `920fdb4d6560be69f9cc12b12bec832883d52623`
- Response contains 22 rows, from 2026-10-14 through 2026-11-26.
- 2026-10-14: 0 trades, 0 shares, NPR 0.
- 2026-10-15: 9 trades, 90 shares, NPR 26,634.
- The next positive row is 2026-10-16: 4 trades, 40 shares.

This is direct NEPSE-origin per-security activity evidence for the captured dates and corroborates the first positive observation on 2026-10-15. The response does not contain pre-2026-10-14 records and the scheduled commencement date is still represented by secondary notice evidence in the lifecycle input. Therefore this review does **not** rewrite BENH's lifecycle evidence status or assert a complete lifetime first-trade proof.

## Merger/successor handling

The current-universe policy remains in force: use the dated 2026-11-25 successor snapshot for current scanning. Retired predecessors are not reintroduced as current instruments and their histories are not spliced into successor series. Current successor mappings recorded by the project are:

- SLBSL/2804 ← BPW
- NMLBBL/396 ← MMFDB, NLBBL
- MATRI/694 ← JALPA, KLBSL
- SMATA/2761 ← MKLB
- SMPDA/2896 ← SABSL, SDLBSL
- GBLBS/583 ← SAMAJ
- PFL/236 ← SFCL

Historical predecessor IDs and boundaries remain separate research questions; they are not blockers to using the current successor IDs for current-scope lookups where the source row is itself for that successor.

The six-row typed event ledger includes two NEPSE primary listing-PDF references (NMLBBL and SMPDA), but those notices establish listing/release events, not first executed transactions. The original PDF bytes and raw hashes are not archived in the event ledger. No first-trade date is inferred from those listing events.

## Priority 1 disposition

- Structural review of the 44 populated rows: complete for schema, date, URI, rationale and duplicate checks.
- Independent content/authenticity review of all 44 linked secondary pages: partial; not re-fetched in this pass.
- Primary first-trade evidence: 0/281 lifecycle starts currently classified as primary in the coverage input. BENH has a separate official activity observation, but its lifecycle status was not upgraded.
- Unverified starts: 237 remain blank.
- Historical stable-ID continuity and corporate-action price-basis gates remain separate and blocked.
- No lifecycle input, raw OHLCV, floorsheet, session calendar, canonical rows, training data or scanner eligibility was changed.

## Next execution

1. Acquire primary NEPSE/SEBON listing and first-execution evidence for the 237 unverified current-equity starts, starting with the largest missing historical cohorts and retaining exact successor/current symbols.
2. Re-fetch and content-review the 44 linked secondary records; retain all date conflicts and scheduled-versus-executed distinctions.
3. Capture original NEPSE listing PDFs and date-scoped floorsheet/API payloads as immutable bytes with UTC retrieval times and SHA-256.
4. Keep all unsupported starts blank. Do not infer from earliest archive rows, file presence, current security IDs, or weekday calendars.
