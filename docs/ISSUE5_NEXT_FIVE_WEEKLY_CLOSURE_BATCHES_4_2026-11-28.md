# Issue #5 — next five weekly-closure review batches (batch 4)

Generated 2026-11-28 from pinned full candidate artifact 15231005676.

## Reproducible input

- Candidate artifact ZIP SHA-256: `a6173b021416da7543ea58bed75bf0fd37f5d6dfe1d1bc5ffd47001b1f29f555`
- Candidate CSV SHA-256: `a343c1a4c87fb305415b0ce2b62427753250152e74d69cdbb0558b13153cbef1`
- Candidate rows: 196,784 across the two pinned archives.
- Grouping: `current_date` for `date_not_listed_in_project_calendar`.
- Excluded the 20 date groups already recorded in prior weekly-closure and unknown-session review packages (PRs #356, #367, #370 and #376).
- Applied the effective weekly schedule: Sunday–Thursday trading before 2026-04-06; Monday–Friday trading from 2026-04-06.

## Ranked five-date batch

| Current date | Pairs | Symbols | Previous date | Weekday |
|---|---:|---:|---|---|
| 2026-05-24 | 645 | 335 | 2026-05-23 | Sunday |
| 2026-05-23 | 645 | 335 | 2026-05-22 | Saturday |
| 2026-04-19 | 645 | 335 | 2026-04-18 | Sunday |
| 2026-04-18 | 645 | 335 | 2026-04-17 | Saturday |
| 2026-04-12 | 645 | 335 | 2026-04-11 | Sunday |

Total: **3,225 candidate-pair incidences** across five dates. Each date includes both source repositories; counts are pair incidences, not unique source rows.

## Evidence boundary

- NEPSE's reported schedule changed to Monday–Friday effective 2026-04-06. Earlier schedule was Sunday–Thursday.
- Supporting pre-change schedule report: https://english.ratopati.com/story/57517/stock-trading-closed-on-saturday-and-sunday-open-on-friday
- Supporting transition report: https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08
- Supporting post-change schedule report: https://english.ratopati.com/story/57946/stock-market-now-trades-from-monday-to-friday
- These are T2/T3 schedule-level references, not retained first-party NEPSE notice bytes with response metadata and SHA-256. No date is promoted to T1 exchange-attested closure.

## Disposition and safeguards

- All five dates remain `REVIEW_ONLY`.
- `canonical_promotion_allowed=false` for every row.
- Weekly closure classification does not prove every repeated OHLCV pair is a carry-forward, fabricated candle or no-trade.
- No project calendar edits, OHLCV edits, deletion, repair, forward-fill, date relabeling, canonical/training admission or scanner eligibility changes.
- Exact row disposition still requires date-matched, security-identity and rights-authorized execution/session evidence.

## Reproduction checks

The five counts were recomputed from the pinned candidate CSV grouped by current date. Each selected date has exactly one previous-date value, 335 unique symbols, and both approved source repositories. Prior registered weekly-closure dates were excluded before ranking.
