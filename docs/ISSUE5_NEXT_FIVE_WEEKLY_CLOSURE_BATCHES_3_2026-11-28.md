# Issue #5 — next five weekly-closure review batches (batch 3)

Generated 2026-11-28 from pinned full candidate artifact 15231005676.

## Reproducible input

- Candidate artifact ZIP SHA-256: `a6173b021416da7543ea58bed75bf0fd37f5d6dfe1d1bc5ffd47001b1f29f555`
- Candidate CSV SHA-256: `a343c1a4c87fb305415b0ce2b62427753250152e74d69dcb0558b13153cbef1`
- Candidate rows: 196,784 across the two pinned archives.
- Grouping: `current_date` for `date_not_listed_in_project_calendar`.
- Excluded the 15 dates already registered in the prior weekly-closure batches and the five explicit-closure candidate dates in the parallel review package.
- Excluded dates that do not match the weekly closed weekdays under the effective schedule regimes.

## Ranked five-date batch

| Current date | Pairs | Symbols | Previous date | Weekday | Regime |
|---|---:|---:|---|---|---|
| 2026-02-13 | 646 | 335 | 2026-02-12 | Friday | Sunday–Thursday trading |
| 2026-02-14 | 646 | 335 | 2026-02-13 | Saturday | Sunday–Thursday trading |
| 2026-02-27 | 646 | 335 | 2026-02-26 | Friday | Sunday–Thursday trading |
| 2026-02-28 | 646 | 335 | 2026-02-27 | Saturday | Sunday–Thursday trading |
| 2026-04-11 | 645 | 335 | 2026-04-10 | Saturday | Monday–Friday trading |

Total: **3,229 candidate-pair incidences** across five dates. Pair incidences are not unique source rows.

## Evidence boundary

- Before 2026-04-06, NEPSE's reported weekly schedule was Sunday–Thursday; Friday and Saturday were weekly closure days.
- From 2026-04-06, NEPSE's reported schedule changed to Monday–Friday; Saturday and Sunday were weekly closure days.
- Supporting schedule context: https://english.ratopati.com/story/57517/stock-trading-closed-on-saturday-and-sunday-open-on-friday
- Supporting transition report: https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08
- Supporting post-change schedule report: https://english.ratopati.com/story/57946/stock-market-now-trades-from-monday-to-friday
- These are T2/T3 schedule-level references, not retained first-party NEPSE notice bytes with response metadata and SHA-256. No date is promoted to T1 exchange-attested closure.

## Disposition and safeguards

- All five dates remain `REVIEW_ONLY`.
- `canonical_promotion_allowed=false` for every row.
- Weekly closure classification does not prove every repeated OHLCV pair is a carry-forward or fabricated candle.
- No project calendar edits, OHLCV edits, deletion, repair, forward-fill, date relabeling, canonical/training admission or scanner eligibility changes.
- Exact row disposition still requires date-matched, security-identity and rights-authorized execution/session evidence.

## Reproduction checks

Counts were recomputed from the pinned candidate CSV grouped by current date. Each selected date has exactly one previous-date value, includes both source repositories, and has the listed unique-symbol count. The CSV SHA-256 is `1883b9cd0519d57afd72a2b284f27297da3376f40e8125074a06e0f426ad68e2`.
