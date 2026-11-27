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


## Visual reinspection and date correction — 2026-11-25

The one-page NEPSE-hosted PDF was opened and its page image visually inspected. The Nepali text records:
- Government decision dated 2079/02/23 to revoke the two-day public-holiday arrangement.
- NEPSE Board decision dated **2079/02/24** (not 2079/02/25 as stated in the earlier note).
- Effective date Asar 1, 2079 (2022-06-16).
- Sunday–Thursday 11:00–15:00 and Friday 11:00–13:00.

This corrects the Board-decision date in the prior entry. The PDF is a one-page official NEPSE-hosted document and the image is legible enough to verify the date and hours. The web-rendered PDF could be inspected, but the exact original PDF bytes could not be downloaded into the repository/container during this run; therefore no raw-byte SHA-256 or immutable evidence file is claimed.

## April 2026 weekday transition — refreshed source check

A fresh search found additional reporting:
- [ShareSansar, 2026-04-08](https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08) says NEPSE issued a public notice and attributes the Monday–Friday schedule to the Board decision on 22 Chaitra 2082.
- [Khabarhub, 2026-04-08](https://english.khabarhub.com/2026/08/543190/) likewise reports that NEPSE issued a notice on Wednesday.
- [Ratopati, 2026-04-08](https://english.ratopati.com/story/57946/stock-market-now-trades-from-monday-to-friday) reports that a notice was issued and Saturday/Sunday were excluded.

These sources improve corroboration and provide a narrower retrieval target (NEPSE notice issued 2026-04-08, Board decision 22 Chaitra 2082). They are still secondary reports: the primary notice PDF or NEPSE-hosted notice record has not yet been captured. Do not upgrade the April 2026 weekday schedule to primary-source verified solely on these articles.


## Calendar-source refresh for acquisition window — 2026-11-25

A further search targeted the NEPSE-hosted notices index and the reported April 2026 change. The NEPSE notice/file index is publicly reachable, and the exchange-hosted 2022 schedule notice remains available, but no pinned original NEPSE notice PDF for the **2026-04-06 Monday–Friday transition** was found in the retrieved results. Secondary reports place the effective change on Monday 2026-04-06 and state that a NEPSE notice was issued on Wednesday 2026-04-08; the reported Board decision is 22 Chaitra 2082 (2026-04-05). These remain leads for a targeted search of the NEPSE notices archive, not primary calendar evidence.

The date-file coverage from the two floorsheet archives also cannot be treated as a trading-session calendar. Their manifests include some dates not independently verified as exchange sessions and omit some dates present in the other publisher's archive. Do not infer that a missing file means a holiday, nor that a present dated file proves a full session. The 196,784 repeated-row candidate set remains unclassified for holiday/suspension purposes until a primary date-level calendar is built.

Current evidence state:
- 2022-06-16 weekly regime change: primary NEPSE notice located and visually reviewed; raw PDF hash still absent.
- 2026-04-06 weekly regime change: secondary reports corroborate; original NEPSE notice/raw hash still absent.
- Daily market-open/closed date list: not yet acquired from NEPSE.


## Work-session update — 2026-11-27 (official NEPSE endpoint refresh)

### First-party pages rechecked
- Official NEPSE homepage: https://nepalstock.com.np/
  - Search-indexed page content exposed a dated market summary for 2026-11-26, including a market-closed status at 15:00 and aggregate index/turnover figures.
  - This is useful evidence that the exchange homepage publishes dated daily market observations. It is **not** a historical date-level calendar, and the search-indexed representation is not a preserved raw HTTP response.
- Official NEPSE notice/file endpoint: https://www.nepalstock.com.np/nots/fetchFiles
  - The page is discoverable, but the available retrieval returned no readable lines. No notice list, pagination contract, date filters, raw response or response hash was obtained.
- Official NEPSE site search results also expose dated notice records, but the retrieved results do not establish a complete sequence of open/closed sessions.

### Findings and limits
1. The first-party site is demonstrably publishing dated market status/summary observations, so a historical market-summary or index-history endpoint remains a promising acquisition route.
2. The public notice archive route is not yet machine-readable through the current retrieval path. Do not infer the archive is empty or that notices do not exist.
3. No exact endpoint request contract, raw bytes, HTTP status, content type, TLS capture, response hash, historical coverage range or pagination behavior has been captured in this session.
4. No dates have been added to the verified-open or verified-closed calendar. The 196,784 repeated-row candidates remain unclassified and review-only.

### Next acquisition actions
- Inspect the official NEPSE site's own frontend/network calls for daily market summary, historical index graph and notice listing; capture method, URL, non-secret headers, request body/query and response schema.
- Obtain representative official responses for several known dates across each historical schedule regime, preserve original bytes and SHA-256, and validate date semantics.
- Determine whether daily market summary/index observations prove an exchange session for the relevant market segment; do not equate a missing observation with a closure.
- Retrieve the original NEPSE notice for the Monday–Friday schedule effective 2026-04-06 and the official historical schedule notice PDFs, preserving original files and hashes.
- Build a date-level evidence table only after the response semantics and source authority are established.

### Status after this refresh
- 2022-06-16 schedule transition: primary NEPSE-hosted notice located and visually reviewed; immutable raw PDF/hash still outstanding.
- 2026-04-06 schedule transition: secondary corroboration only; original NEPSE notice/raw hash outstanding.
- Daily open/closed calendar: not acquired.
- Priority 1: **in progress; acceptance not met**.
