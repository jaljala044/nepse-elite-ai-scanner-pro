# Issue #5 — next five weekly-closure review batches (batch 3)

Generated 2026-11-28 by ranking the pinned, calendar-joined 196,784-candidate workload index.

- Input artifact: 15231005676
- Candidate CSV SHA-256: `a343c1a4c87fb305415b0ce2b62427753250152e74d69dcb0558b13153cbef1`
- Excluded the ten dates already covered in batches 1 and 2.
- Ranking key: candidate-pair incidences grouped by `current_date`, descending; ties by date ascending.
- Source identity and source-level pair counts are retained. Pair incidences are not unique source rows.

## Ranked date batches

| Current date | Pairs | Symbols | SMC | History Starter | Previous date | Schedule context |
|---|---:|---:|---:|---:|---|---|
| 2026-06-21 | 677 | 351 | 326 | 351 | 2026-06-20 | Sunday; weekly closure after 2026-04-06 |
| 2026-06-06 | 665 | 345 | 320 | 345 | 2026-06-05 | Saturday; weekly closure after 2026-04-06 |
| 2026-06-07 | 665 | 345 | 320 | 345 | 2026-06-06 | Sunday; weekly closure after 2026-04-06 |
| 2026-03-20 | 657 | 341 | 316 | 341 | 2026-03-19 | Friday; weekly closure before 2026-04-06 |
| 2026-03-21 | 657 | 341 | 316 | 341 | 2026-03-20 | Saturday; weekly closure before 2026-04-06 |

Total: **3,321 candidate-pair incidences across five date batches**.

## Evidence tier and controls

- Dates are ranked from the project workload index, not from official exchange closure notices.
- The schedule regimes are contextual evidence only. Saturday has additional NRB holiday-calendar context; the pre-2026-04-06 Friday/Saturday and post-2026-04-06 Sunday/Saturday schedule interpretations remain non-T1 unless retained NEPSE notice bytes are captured.
- Keep all five rows `REVIEW_ONLY`; no `verified_closed_tier1` classification is asserted.
- Identical adjacent OHLCV does not prove closure, carry-forward, fabrication or no-trade.
- Do not alter project calendar or source OHLCV. No deletion, repair, forward-fill, canonical admission, training admission or scanner eligibility change.

## Reproducibility

The source artifact summary records 196,784 candidates, 3,630 project-accepted open dates, 41 explicit closure dates and 180,855 date-not-listed pairs. The candidate archive SHA-256 is recorded above. The ranking excludes the ten previously processed dates:
2026-06-27, 2026-06-28, 2026-02-21, 2026-05-31, 2026-06-20, 2026-05-03, 2026-06-13, 2026-06-14, 2026-05-16 and 2026-05-17.
