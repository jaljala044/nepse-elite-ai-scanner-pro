# Issue #5 — five highest-incidence unlisted-date batches

Generated 2026-11-28 from workflow artifact 15231005676 (candidate CSV SHA-256: a343c1a4c87fb305415b0ce2b62427753250152e74d69cdbb0558b13153cbef1). Counts independently recomputed from the CSV grouped by current_date.

| Current date | Pairs | Symbols | Previous date | Day | Review disposition |
|---|---:|---:|---|---|---|
| 2026-06-27 | 683 | 354 | 2026-06-26 | Saturday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-06-28 | 683 | 354 | 2026-06-27 | Sunday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-02-21 | 680 | 352 | 2026-02-20 | Saturday | WEEKLY_CLOSED_BEFORE_2026-04-06 |
| 2026-05-31 | 679 | 352 | 2026-05-30 | Sunday | WEEKLY_CLOSED_AFTER_2026-04-06 |
| 2026-06-20 | 677 | 351 | 2026-06-19 | Saturday | WEEKLY_CLOSED_AFTER_2026-04-06 |

## Evidence and limits

- NEPSE Monday–Friday schedule announced effective 6 April 2026; ShareSansar reports NEPSE's Board notice: https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08
- Nepal Rastra Bank 2083 holiday list records Saturday as a full holiday: https://www.nrb.org.np/contents/uploads/2026/03/Holiday-List-2083-English.pdf
- Nepal News reports the April 6 schedule change and Saturday/Sunday closures: https://english.nepalnews.com/s/business/nepse-to-operate-five-days-a-week-closed-on-saturdays-and-sundays/
- These sources support weekly-closure review. This package does not contain directly captured NEPSE-hosted notice bytes/hash. Do not upgrade these dates to T1/NEPSE-primary verified closure; retain T2/T3-supported review status.
- Identical OHLCV on adjacent CSV rows does not prove fabricated or forward-filled data. Do not alter source rows or promote data from this classification alone.

## Controls

- 2026-06-27/28 and 2026-05-31 fall after the Monday–Friday change.
- 2026-02-21 falls before the change; Saturday was already the weekly holiday.
- 2026-06-20 is Saturday after the change.
- All 3,402 candidate pairs across these five date batches remain REVIEW_ONLY; canonical promotion is false.
- Source rows and files remain immutable.
