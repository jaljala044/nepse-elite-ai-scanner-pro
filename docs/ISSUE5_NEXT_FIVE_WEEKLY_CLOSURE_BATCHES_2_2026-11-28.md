# Issue #5 — next five weekly-closure review batches (batch 2)

Generated 2026-11-28 from the pinned full candidate artifact used by the merged Issue #5 workload index.

## Reproducible input

- GitHub Actions artifact ID: `15231005676`
- Artifact ZIP SHA-256: `a6173b021416da7543ea58bed75bf0fd37f5d6dfe1d1bc5ffd47001b1f29f555`
- Candidate CSV SHA-256: `a343c1a4c87fb305415b0ce2b62427753250152e74d69cdbb0558b13153cbef1`
- Candidate source: 196,784 rows across the two pinned archives.
- Grouping: `current_date` for rows whose `session_pair_classification=date_not_listed_in_project_calendar`.
- Excluded the ten dates already covered by the prior two five-date packages.

## Ranked date batches

| Current date | Candidate pairs | Symbols | Previous date | Weekday | Review classification |
|---|---:|---:|---|---|---|
| 2026-06-21 | 677 | 351 | 2026-06-20 | Sunday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-06-06 | 665 | 345 | 2026-06-05 | Saturday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-06-07 | 665 | 345 | 2026-06-06 | Sunday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-03-20 | 657 | 341 | 2026-03-19 | Friday | WEEKLY_CLOSED_BEFORE_2026-04-06 |
| 2026-03-21 | 657 | 341 | 2026-03-20 | Saturday | WEEKLY_CLOSED_BEFORE_2026-04-06 |

Total: **3,321 candidate-pair incidences across five dates**. These are pair incidences, not unique source rows.

## Evidence and limitations

- NEPSE's pre-change schedule was Sunday–Thursday, with Friday and Saturday closed; Ratopati's April 6 report explicitly describes the previous schedule and the decision to move trading to Monday–Friday: https://english.ratopati.com/story/57517/stock-trading-closed-on-saturday-and-sunday-open-on-friday
- The April 8 schedule notice is reported as Monday–Friday trading effective April 6: https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08
- Ratopati's April 8 report describes Saturday/Sunday closures under the new schedule: https://english.ratopati.com/story/57946/stock-market-now-trades-from-monday-to-friday
- The classifications are schedule-level evidence (T2/T3), not retained first-party NEPSE notice bytes with response metadata and SHA-256. No date is upgraded to T1.

## Disposition and controls

- All five dates remain `REVIEW_ONLY`; do not set `verified_closed_tier1`.
- A date-level weekly closure does not prove that every security's repeated OHLCV pair is a forward-fill or fabricated candle.
- Do not alter the project session calendar, source OHLCV, row classifications or canonical inputs from this package.
- No deletion, repair, date relabeling, deduplication, training admission or scanner eligibility change.
- Resolve individual pairs only with exact-date, security-identity, rights-authorized execution/session evidence.

## Reproduction checks

The five counts were recomputed from the downloaded candidate CSV. Each date has exactly one previous-date value, and both repositories are represented in each date batch. The output CSV records the pair incidence count and unique-symbol count separately.
