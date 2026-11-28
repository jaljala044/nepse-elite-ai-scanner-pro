# Issue #5 — independent candidate-row integrity review (2026-11-28)

## Scope and input integrity

- Source artifact: GitHub Actions artifact `15231005676`.
- Downloaded ZIP SHA-256: `a6173b021416da7543ea58bed75bf0fd37f5d6dfe1d1bc5ffd47001b1f29f555`.
- Candidate CSV SHA-256: `a343c1a4c87fb305415b0ce2b62427753250152e74d69cdbb0558b13153cbef1`.
- Candidate rows inspected: **196,784**.
- Source CSV paths represented: **945** (across both repositories).

## Results on candidate extract

| Check | Result |
|---|---:|
| Duplicate `(repository, symbol, current_date)` keys | 0 |
| Duplicate candidate-pair keys | 0 |
| Reversed / noncanonical candidate date pairs | 0 |
| Invalid source-line pairs | 0 |
| Candidate source-order regressions | 0 |
| Candidate rows with invalid current OHLC geometry | 2 |
| Candidate rows incorrectly marked outside review-only state | 0 |

The two invalid current OHLC candidates are:
- AHPC — candidate CSV line 1,122; current date and row values are retained in the source artifact.
- API — candidate CSV line 2,735; current date and row values are retained in the source artifact.

Both were already separately identified by the extractor as invalid-OHLC exceptions and remain review-only.

## Important scope limitation

This artifact contains only repeated-adjacent candidate pairs, not every row from the 945 source files. Therefore this audit **does not assess**:
- duplicate dates among all source rows that are not candidate pairs;
- missing rows across each instrument's expected session dates;
- every source row's OHLC geometry;
- source-file order outside the represented candidate pairs.

Those checks require the complete pinned source CSV archives. This report does not mark the full Issue #5 acceptance checklist complete.

## Safeguards

- Original source CSVs and candidate artifact were read-only.
- No row was deleted, sorted, repaired, forward-filled or rewritten.
- No calendar status was inferred from weekday or candidate adjacency.
- All 196,784 candidates remain `REVIEW_ONLY`.
- No canonical, training, backtest or scanner promotion is authorized.

## Reproducibility

Run:

```bash
python backend/audit_issue5_candidate_row_integrity.py \
  --input repeated_adjacent_ohlcv_candidates.csv \
  --output issue5_candidate_row_integrity.json
```

The validator and unit tests check duplicate candidate keys, date order, source-line order, source identity consistency, OHLC geometry and review-only classification. Full-source missing-row and duplicate-date checks are intentionally reported as `NOT_ASSESSED`, not as passes.
