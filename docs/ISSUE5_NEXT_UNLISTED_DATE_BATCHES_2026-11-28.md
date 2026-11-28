# Issue #5 — next five unlisted-date batches

**Generated:** 2026-11-28  
**Input workflow artifact:** `15230486904` (`repeated-adjacent-ohlcv-candidates`)  
**Artifact ZIP SHA-256:** `85a0b5750ab1b772aab12f4e55861106106ca76f9c49263c8c45bb6cfd3d8157`  
**Candidate CSV SHA-256:** `a343c1a4c87fb305415b0ce2b62427753250152e74d69cdbb0558b13153cbef1`  
**Project calendar SHA-256 from artifact summary:** `fd02700706be90524540bf06386376a5adecbe2c2f8e0e2db509a425944b93e5`

## Five execution steps completed

1. Downloaded and independently hash-checked the pinned full-candidate workflow artifact.
2. Rechecked all 196,784 candidate source occurrences: 94,543 SMC and 102,241 History Starter.
3. Revalidated structural integrity: 196,784 unique source occurrence keys, zero duplicate occurrences, zero malformed ISO dates, zero non-adjacent CSV line references.
4. Reconciled the existing session-pair partition: 194 adjacent project sessions, 176 intervening project sessions omitted from source rows, 15,559 pairs touching an explicit closure date, and 180,855 pairs with at least one date unlisted in the project calendar.
5. Ranked the next five unlisted **current dates** after excluding the 15 dates already included in the current-main and queued Issue #5 packages. Added a reproducible ranking script, regression tests and this report.

## Next five ranked date batches

Counts are candidate source-pair occurrences whose `current_date` equals the listed date. Each source occurrence is counted once for its current endpoint. Distinct symbols are the union across both archives.

| Date | Pairs | Symbols | SMC pairs | History Starter pairs | Schedule context |
|---|---:|---:|---:|---:|---|
| 2026-02-20 | 680 | 352 | 328 | 352 | Friday; scheduled non-session candidate |
| 2026-05-30 | 679 | 352 | 327 | 352 | Saturday; scheduled non-session candidate |
| 2026-03-28 | 657 | 341 | 316 | 341 | Saturday; scheduled non-session candidate |
| 2026-05-02 | 655 | 340 | 315 | 340 | Saturday; scheduled non-session candidate |
| 2025-12-30 | 648 | 336 | 312 | 336 | Tuesday; scheduled open candidate |
| **Total** | **3,319** | — | **1,598** | **1,696** | — |

## Evidence boundary

- All five dates are absent from the project-accepted session calendar in this artifact.
- Schedule context is a T2/T3 research aid only. It is not a NEPSE notice, verified closure, or proof that a repeated OHLCV row is carried forward.
- 2025-12-30 is a scheduled-open candidate, not a closure candidate; it remains unlisted and unresolved.
- Exchange-session disposition for every date remains `UNKNOWN_NO_T1_NOTICE`.
- All candidate rows remain review-only and `canonical_promotion_allowed=false`.
- No OHLCV row, project calendar entry, raw source file or training dataset was changed.

## Structural integrity observations

- Total candidate rows: 196,784.
- Source counts: 94,543 SMC; 102,241 History Starter.
- Unique source occurrence keys: 196,784; duplicates: 0.
- ISO date parse/canonical failures: 0.
- Candidate source-line adjacency failures: 0.
- Repeated-signature candidates with invalid OHLC bounds: 2; these remain independently flagged and are not counted as valid candles.
- Session-pair classes sum exactly to 196,784: 194 + 176 + 15,559 + 180,855.

The full candidate artifact does not contain every non-candidate row from each OHLCV file. Therefore this pass does not certify the complete per-symbol dataset for duplicate dates, missing rows, or out-of-order records outside the adjacent-repeat candidate pairs. Those checks require the pinned source archives and remain separate work.

## Reproduction

```bash
python scripts/rank_unlisted_date_batches.py \
  --input /path/to/repeated_adjacent_ohlcv_candidates.csv \
  --csv-output data/reports/issue5_next_unlisted_date_batches_2026-11-28.csv \
  --json-output data/reports/issue5_next_unlisted_date_batches_2026-11-28.json
python -m unittest discover -s tests -p 'test_rank_unlisted_date_batches.py' -v
```
