# NEPSE session-calendar source research — 2026-11-25

## Decision

A complete primary-source, date-level NEPSE trading calendar has **not** yet been obtained. Do not promote a weekday rule, bank holiday list, news article or index-observation date list into a verified exchange calendar.

## Evidence located

| Source | Evidence | What it can support | Limitation |
|---|---|---|---|
| [NEPSE official catalogue](https://www.nepalstock.com.np/en/catalogue) | Official exchange catalogue; indexed snapshot 2026-09-24 | Primary exchange source for catalogue observations at that snapshot | Search/open extraction has no usable historical session calendar or dated holiday registry |
| [NEPSE official stock list](https://www.nepalstock.com.np/stocklist) | Official exchange stock-list page; indexed snapshot 2026-10-15 | Primary exchange page for listed/traded symbol observations at that snapshot | Not a session calendar; accessible snapshot is not current as of 2026-11-25 |
| [ShareSansar, 2026-04-08](https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08) | Reports that NEPSE Board meeting on 22 Chaitra 2082 decided trading Monday-Friday, including Friday, following government Saturday/Sunday holiday change | Secondary report of the schedule transition and date | Not the original signed NEPSE circular; should be corroborated with official notice before treating as authoritative |
| [Nepal Rastra Bank holiday list 2083](https://www.nrb.org.np/contents/uploads/2026/03/Holiday-List-2083-English.pdf) | Official NRB document effective 2026-04-14 to 2027-04-13; its own office hours are Sunday-Thursday and every Friday is a half holiday; Saturdays are full holidays | Corroborates public/bank holiday dates and shows bank operating calendar | **Not NEPSE's exchange calendar.** Its Sunday-Thursday banking schedule differs from the reported NEPSE Monday-Friday schedule, proving it must not be used as a proxy for exchange sessions |

## Historical regime implications

The existing weekday helper contains candidate regimes, not a verified calendar:
- Through 2022-05-14: Sunday-Thursday candidates.
- 2022-05-15 through 2022-06-14: Monday-Friday candidates.
- 2022-06-15 through 2022-09-16: Sunday-Friday candidates.
- 2022-09-17 through 2026-04-05: Sunday-Thursday candidates.
- From 2026-04-06: Monday-Friday candidates (the transition date is supported by secondary reporting, official NEPSE circular still required).

Do not infer holidays from a missing OHLCV/floorsheet date, nor infer exchange closure from bank/public holiday data alone. Trading can be exceptionally opened or suspended. Distinguish candidate weekday, published holiday, announced exchange closure, confirmed trading session, and unknown.

## Immediate acquisition tasks

1. Locate original NEPSE public notice/circular dated around 2026-04-06 and retain the official document or official page response.
2. Find NEPSE notices/holiday lists for fiscal/calendar years covering all source history needed, including historical weekday-regime changes in 2022.
3. Locate official exceptional opening/closure/suspension notices; record effective date and whether all securities or only a segment were affected.
4. Search NEPSE official site/API for historical trading-date or market-summary endpoints; if found, preserve raw responses and hashes. An index row is evidence that an index observation exists, not automatically proof of a full normal session for every security.
5. Cross-check against exchange-origin market summary, floorsheet publication and official notice records. Keep evidence source-specific.
6. Produce a versioned CSV with one row per Gregorian date: date, weekday candidate, calendar status, scope, notice ID, official URL, publication timestamp, retrieval timestamp, raw evidence SHA-256, notes, confidence, reviewer.
7. Keep all unresolved dates `unverified`; no forced backfilling.

## Current conclusion

The research establishes that the April 2026 weekly schedule changed and that NRB's 2083 banking calendar is not a valid substitute for NEPSE's trading calendar. It does **not** establish a complete primary-source session calendar. Calendar verification remains the blocker for classifying the 196,784 repeated-row review candidates.
