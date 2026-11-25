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


## Additional cross-publisher corroboration located — 2026-11-25

Two further reports support the 2026 weekly schedule transition:
- [Ratopati, 2026-04-06](https://english.ratopati.com/story/57517/stock-trading-closed-on-saturday-and-sunday-open-on-friday) reports a NEPSE Board decision to trade Monday-Friday, effective that week, with Friday replacing Sunday.
- [The Himalayan Times, 2026-04-08](https://thehimalayantimes.com/business/nepse-shifts-to-mondayfriday-trading-week) reports the Monday-Friday schedule effective 2026-04-06 and attributes it to a NEPSE Board decision on the same date.

These independently corroborate the date and weekly schedule change reported by ShareSansar. They remain secondary publisher reports; no original NEPSE circular or official signed notice has been retrieved. Accordingly, the post-2026-04-06 Monday-Friday weekday regime has stronger corroboration but the official primary artifact is still an acquisition gap.

The NRB holiday document's Sunday-Thursday office hours remain a separate NRB calendar, not a contradiction of the reported NEPSE schedule and not a substitute for NEPSE dates.

## Latest artifact verification

The enriched repeated-row artifact `14985599288` was downloaded and rechecked locally:
- ZIP SHA-256 matches GitHub artifact digest: `4b8b7c27c642fee768eb3b031928e785a5ef296dc346b4d5c3b8212ba09def67`.
- CSV has 196,784 records and 196,784 unique (repository, path, current CSV line) identities.
- Breakdown matches summary exactly: 196,542 consecutive-calendar-date + OHLC-valid candidates; 240 date-gap/unparseable candidates; 2 invalid-OHLC-bound repeated signatures.
- All records remain review-only with calendar status unverified.


## Primary-source session-regime notice located — 2026-11-25

An official NEPSE-hosted PDF was located through the exchange's own file endpoint:
- [NEPSE market-session notice, hosted at nepalstock.com.np](https://www.nepalstock.com.np/api/nots/security/fetchFiles?fileLocation=santosh_thapa%2F2022-06-16%2Fmarket+session+notice_1655356331971.PDF)
- The notice states that, following the Government decision to revoke the two-day public-holiday arrangement, the NEPSE Board decision of 2079/02/25 set the secondary market schedule from Asar 1 (2022-06-16): Sunday–Thursday 11:00–15:00 and Friday 11:00–13:00.
- This is primary exchange evidence for the 2022-06-16 schedule change and confirms Friday as a shortened trading session in that regime. It supports the weekday candidate regime through 2022-09-16, but it does not prove that every candidate date actually traded; date-specific holidays, closures and exceptional sessions still require evidence.
- The PDF is linked from NEPSE's official host. Exact raw-byte SHA-256 and a locally preserved immutable copy have **not yet** been recorded; do not mark the evidence capture/hash requirement complete.

### Calendar research update

The previous gap statement that no original NEPSE session-regime notice had been retrieved is now narrowed: a primary NEPSE notice for the June 2022 regime transition has been found. The April 2026 Monday–Friday change remains supported only by secondary reports in the evidence currently captured; an original NEPSE notice is still outstanding. A complete date-level calendar remains unverified.
