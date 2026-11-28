# Issue #5 — next five weekly-closure review batches

Generated 2026-11-28 from the merged deterministic workload index in PR #336 and pinned candidate artifact 15231005676.

Candidate CSV SHA-256: `a343c1a4c87fb305415b0ce2b62427753250152e74d69dcb0558b13153cbef1`.

## Ranked date batches

| Current date | Candidate pairs | Symbols | Previous date | Weekday | Review classification |
|---|---:|---:|---|---|---|
| 2026-05-03 | 655 | 340 | 2026-05-02 | Sunday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-06-13 | 651 | 338 | 2026-06-12 | Saturday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-06-14 | 651 | 338 | 2026-06-13 | Sunday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-05-16 | 649 | 337 | 2026-05-15 | Saturday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-05-17 | 649 | 337 | 2026-05-16 | Sunday | WEEKLY_CLOSED_AFTER_2026-04-06 |

Total: **3,255 candidate-pair incidences across 5 date batches**. These are pair incidences, not unique source rows.

## Evidence and tier limits

- ShareSansar reports that NEPSE's Board of Directors aligned regular trading to Monday–Friday effective 6 April 2026: https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08
- Ratopati independently reports the Saturday/Sunday closure and Monday–Friday trading decision: https://english.ratopati.com/story/57946/stock-market-now-trades-from-monday-to-friday
- Nepal Rastra Bank's official 2083 holiday list is effective 2026-04-14 to 2027-04-13 and records Saturday as the full weekly holiday: https://www.nrb.org.np/contents/uploads/2026/03/Holiday-List-2083-English.pdf
- The Sunday classification depends on the reported NEPSE schedule change; the Saturday classification has the additional official NRB weekly-holiday calendar support.
- No directly captured NEPSE-hosted notice bytes, response metadata or SHA-256 for the schedule decision is included in this package. These rows are schedule-supported review classifications only, not T1 exchange-attested closures.

## Disposition and controls

- Keep all five date batches `REVIEW_ONLY`; do not promote them to `verified_closed_tier1`.
- Identical adjacent OHLCV does not prove carry-forward, fabrication, no-trade or market closure.
- Do not modify the project calendar or source OHLCV based on this schedule-only classification.
- No row deletion, repair, forward-fill, canonical admission, training admission or scanner eligibility change.
- Resolve exact source-row dispositions only with date-matched, rights-authorized NEPSE/provider/floorsheet evidence.

## Reproducibility

- Input artifact: `15231005676`.
- Input candidate CSV SHA-256: `a343c1a4c87fb305415b0ce2b62427753250152e74d69dcb0558b13153cbef1`.
- Workload-index grouping key: `current_date` in `date_not_listed_in_project_calendar`.
- Counts remain candidate-pair counts; do not interpret them as unique records or exchange sessions.
