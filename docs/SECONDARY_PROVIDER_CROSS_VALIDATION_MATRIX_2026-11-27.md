# Secondary NEPSE data-provider cross-validation matrix — 2026-11-27

## User-approved acceptance policy

The project owner approved the revised secondary-provider rule and accepted the recommended threshold of **4 of 6 providers**.

For a stock/date record, assign `verified_secondary_consensus` and approve it for the project dataset only when all of the following pass:

1. The same security (symbol and, where available, security ID) and the same Nepal trading date are matched across at least **4 of the 6 named providers**: Chukul, ShareHub, Punji, NEPSE Alpha, Sharesansar and MeroLagani.
2. The four or more agreeing providers represent at least **two genuinely independent upstream source lineages**. Providers shown to copy/repackage the same upstream feed count as one lineage, regardless of the number of websites.
3. Compare Open, High, Low and Close separately; compare traded quantity/volume and turnover separately. Agreement on one field does not imply agreement on another. Record tolerances and rounding rules before comparison; do not silently round away a material difference.
4. Resolve field semantics before comparing close values. Preserve LTP/last-traded price, exchange-designated close, weighted-average close and VWAP as distinct fields unless provider documentation or authoritative evidence establishes equivalence. Do not count a semantic mismatch as a match.
5. No material unresolved conflict remains for a field being approved. A record may be approved only for the fields that independently pass; do not promote an unresolved field by majority vote.
6. Preserve provider URLs/endpoints, request parameters, retrieval timestamps, raw captures/exports, SHA-256 hashes, field labels, source lineage notes, coverage and access/licence limitations.

Use `verified_secondary_consensus` to mean **project-verified by secondary-provider consensus**. It does not mean exchange-certified, NEPSE-issued, or officially authenticated.

If fewer than four providers are accessible/audited, fewer than two independent lineages can be established, field semantics remain unclear, or evidence conflicts, retain the affected record/field under review. Access-blocked and not-audited providers are neither positive votes nor evidence of failure.

## User-requested providers and current audit status

| Provider | Evidence/status recorded in repository | Next validation action | Classification |
|---|---|---|---|
| Chukul | Public dashboard/live ticker inspected; no dated 2025-07-28 daily OHLCV or public historical route obtained. Login/subscription entitlement was not tested. | With the project owner's authorized account, inspect dated daily history and record exact field labels, coverage, export/API contract and terms. | Access-limited / historical result not verified |
| ShareHub | Official documentation at https://sharehubnepal.com/data/nepse-data-documentation/ documents `GET /data/api/v1/nepse-data/price-history/{symbol}` as daily OHLCV history from listing, but requires a Data API account, bearer token, allow-listed server IP and enabled licence. No authorized historical response has been captured. | Obtain authorized access; capture a dated symbol response, raw bytes, field schema, coverage and licence terms; establish upstream lineage. | Historical API documented; record-level audit blocked pending access |
| Punji | Public product/support pages say Punji reads NEPSE-published data through its own service; its terms say market data is sourced from public NEPSE endpoints and also mention a small number of third-party service providers. Homepage advertises published closing prices, but no dated raw OHLCV response for the target securities has been captured. Sources: https://punji.app/ and https://punji.app/terms | Capture dated records for target symbols/dates and exact field labels; document which fields come directly from NEPSE, which third parties are involved, and whether any upstream feed is shared with other providers. | Source claim documented; historical row and lineage not yet audited |
| NEPSE Alpha | Its about page advertises full historical adjusted price data for all listed companies and live market/floorsheet features. The public statement does not identify the underlying historical feed, adjustment methodology, or field schema. Source: https://nepsealpha.com/about-nepsealpha | Capture dated raw history for target symbols/dates; record adjusted/unadjusted status, OHLCV/turnover fields, correction policy, source lineage and terms. | Historical-data capability advertised; underlying lineage and record-level audit not established |
| Sharesansar | Captured the full 2025-07-28 daily board from the ShareSansar-derived OmitNomis archive; all five target symbols are present. The archive README says its rows are scraped from ShareSansar `today-share-price`. O/H/L, volume and turnover agree with prior MeroLagani query notes; literal LTP differs. | Preserve original publisher-side capture if possible; establish upstream lineage and resolve Close/LTP/VWAP field semantics. | Dated secondary row capture; one lineage; not enough for consensus |
| MeroLagani | Dated Price History queries were completed for all five symbols on 2025-07-28. Its LTP and O/H/L/quantity match Source A. The field is explicitly labelled LTP. | Preserve source pages/raw captures and recheck turnover/quantity and historical coverage; do not relabel LTP as exchange-designated close without evidence. | Secondary corroboration for five rows; not exchange certification |

## Required validation protocol for every provider

1. Record exact canonical domain, page/API endpoint, request method, parameters, retrieval time and access mode (public, login or licensed API).
2. Preserve raw response/export bytes and response headers/metadata where available; calculate SHA-256 before parsing.
3. Record literal field names. Keep LTP, last trade, official close, VWAP, adjusted close and previous close distinct unless a documented mapping proves equivalence.
4. Capture OHLC, quantity, turnover, trade count, date, symbol/security ID, currency/units, adjustment status and missing/null semantics where available.
5. Record source publication/update time, historical coverage, pagination, timezone/session-date convention, corrections and provider terms/licence.
6. Compare every field independently. Do not majority-vote incompatible field definitions.
7. Classify outcomes as match, field_semantics_mismatch, value_conflict, missing, access_blocked, coverage_gap or not_audited. A failed page load or empty response is not proof of no data.
8. Maintain source independence: sites that repackage the same upstream feed count as one lineage. Record upstream/source attribution whenever discoverable.
9. Apply the 4/6 and two-independent-lineage gate above. Approval is field-specific; unresolved fields remain under review.

## Separate acceptance criteria

### Stock/date records

- The 4/6 threshold applies to each security/date and each field independently.
- OHLC, volume and turnover must be checked separately; volume and turnover are not interchangeable.
- A record can receive `verified_secondary_consensus` only for the fields that pass all source, lineage and semantic checks.
- The project owner's supplied values for BGWT, MEHL, RAWA, RHGCL and ULHC on 2025-07-28 remain authoritative for the project. Secondary discrepancies are not grounds to overwrite them. Preserve the user's OHLC chart readings and floorsheet quantity/turnover.

### 616-date session calendar

- Apply a 4-of-6 provider threshold only where at least four providers provide positive, date-specific evidence that the market session occurred, and those providers represent at least two independent upstream lineages.
- Evidence must explicitly identify a market session/date or show positive market-wide activity for that date. A dated stock trade proves that the stock traded; a no-row response does not prove the market was closed.
- A provider's omission from a calendar, an empty stock history, or absence from a holiday list is unknown, not closed.
- Keep `market_session_date` distinct from `stock_trading_date`; an open market session does not imply every listed security traded.
- Preserve official NEPSE session/closure notices where available. Secondary consensus is project verification, not exchange certification.

## Current decision and execution status

The acceptance policy is now set to **4 of 6 providers plus at least two independent source lineages**, with field-specific approval and explicit close-field semantic resolution. This policy change does not itself verify any new records.

Current evidence: A complete ShareSansar-derived daily CSV for 2025-07-28 is now preserved with extracted rows for BGWT, MEHL, RAWA, RHGCL and ULHC. Its O/H/L, volume and turnover agree with prior MeroLagani query notes, while literal LTP values differ; the prior MeroLagani raw page payloads are not in the new evidence bundle, so that prior query is corroboration but not yet a fully replayable vote. ShareHub's public company/live pages returned current data, not the target date; its all-time OHLCV endpoint requires licensed/token/IP-allow-listed access. Punji publicly claims NEPSE sourcing and discloses third-party providers, but no dated target row or lineage proof is captured. NEPSE Alpha advertises historical/adjusted data, but no dated target row or lineage proof is captured. Chukul's historical target rows remain unverified. The 4/6 plus two-independent-lineage gate is not met; no record/field is promoted by this capture. The five user-supplied 2025-07-28 records remain authoritative. The 616 dates remain `candidate_unverified` until date-specific session evidence meets the calendar gate. The 196,784 repeated-OHLCV candidates remain quarantined/review-only.

## Evidence reuse audit — 2026-11-27

Re-read the existing conflict ledger, P1 investigation log, cross-repository audit, both ShareSansar-derived archives, extracted five-row CSV, and issue #5. No new provider capture was performed and no authoritative value was changed.

- `data/evidence/raw/secondary/share-sansar-archive/2025-07-28.csv` (blob `329146bbdb0ef66722933f8aba0542c7e4ec78f8`) contains all five rows with Source A close values. The OmitNomis daily-board extract (blob `3cacf0dfa78692ea18cd64d0be202ba632df08cd`) contains Source B close values plus literal LTP, VWAP and transaction counts. Both archives derive from ShareSansar; do not count them twice. Their close fields differ materially.
- MeroLagani has five completed dated query results in the investigation log; raw page responses have not been established in this audit. Its LTP matches Source A. O/H/L, quantity and turnover agree with both archives. Literal OmitNomis LTP differs for all five.
- Existing SocrateAI floorsheet aggregation (external raw blob `9c5533626b354d5fefca06d6762d51e0b9beaac6`, revision `7648ec7ce9988e032975d6cf8bcc876ba7da7ae5`) gives trades/quantity/full-day VWAP: BGWT 194/14028/944.9918; MEHL 333/29753/470.8399; RAWA 74/3165/794.8381; RHGCL 1030/296715/350.0754; ULHC 300/32288/504.0059. These are existing documented aggregates, not a fresh raw-byte replay. BGWT has a one-share 925 trade below daily-board low 933.4; trade-type filtering unresolved. No timestamps or proven upstream lineage.
- All five securities: O/H/L/quantity/turnover have secondary agreement but fail the formal evidence gate; close and LTP also have semantic/value conflicts; VWAP and transactions have archive/tape corroboration but fail provider count and independence. Zero fields promoted. Twenty dated provider rows across Chukul, ShareHub, Punji and NEPSE Alpha are still missing. MeroLagani original raw capture and archive SHA-256 provenance remain outstanding. Do not re-run completed queries except to recover genuinely missing raw evidence.
- ShareHub authorized historical API access remains unestablished; Chukul historical access not obtained; Punji and NEPSE Alpha date-specific rows remain unaudited. No fresh access tests were performed during this repository-only audit. No new independent lineage was established.

Next: obtain missing dated records and lineage statements, resolve official close semantics with timestamped tape or official EOD documentation, preserve original bytes and SHA-256; retain P1 gate and existing quarantines. No AI/app development authorized by this audit.


## Field semantics, integrity and outstanding-gap follow-up — 2026-11-27

Continuation from `86a7b7478898a98eb396de0c42b08930567eaaab`. Source A's stored Close values (BGWT 957.17, MEHL 475.63, RAWA 796.90, RHGCL 357.05, ULHC 510.75) match MeroLagani's labelled LTP, not a confirmed exchange-designated close. Source B reported Close approximates full-day VWAP; neither establishes official close. Keep all fields distinct and owner-authoritative data unchanged.

Integrity: existing OmitNomis daily-board bytes match upstream base64 contents and Git blob `28b5edf90ea5ebfe7e419c5162eedd0f30a9ce82`; 54,019 bytes SHA-256 `36730b61430c2a42f7f1e33231c6b1b39e58037acc27bf24a62ac40ffed7a37d`. Manifest updated in `ffe47550c90c83e6cf797a9d7254339813552e36`. This closes this archive checksum gap, not HTTP metadata or upstream data accuracy.

BGWT one-share Rs 925 exception: classify investigation `suspected_odd_lot_pending_trade_type_confirmation`. MeroLagani company profile https://merolagani.com/CompanyDetail.aspx?symbol=BGWT reports paid-up value 100; contemporary July 17 2025 reporting https://eng.merolagani.com/NewsDetail.aspx?newsID=116589 describes 10-share board lot for Rs 100 face value, with smaller trades odd lots. https://www.newbusinessage.com/news/44702/nepse-enhances-odd-lot-trading-transparency-to-address-investor-concerns/ reports odd lots do not affect official market price/index. This is a plausible explanation, not contract-level confirmation. Require contract ID and exchange trade-type/segment flag or official confirmation; preserve original row, quantity, amount and rate; no exclusion, deletion or alteration approved.

Punji public features https://www.punji.app/features advertises charts up to a year of candles; target date is outside that advertised span as of audit. Terms https://punji.app/terms claim public NEPSE endpoint sourcing, not independent lineage proof. No dated target rows captured. ShareHub documentation https://sharehubnepal.com/data/nepse-data-documentation/ rechecked; no authorized target-date response obtained. Chukul and NEPSE Alpha dated coverage remains outstanding. No new qualifying provider vote; 4/6 plus two independent lineages remains unmet, P1 open. No canonical promotion or development gate changes.


## Public historical-page access check — 2026-11-27

A focused public-page check was performed for NEPSE Alpha and Punji. This did not repeat or alter the already-captured five-stock ShareSansar/MeroLagani evidence.

- **NEPSE Alpha:** the public `/nepse-data/` page exposes a History Price Filters interface with Daily/Weekly/Monthly intervals, filter option, price type, start date, end date, symbol/index selection, and Copy/Print/CSV controls. The page extraction returned only a current-date table snapshot; it did not execute the date filter or expose a dated 2025-07-28 response. This establishes a visible public historical-query UI, not that the target date is accessible, complete, unadjusted, or exportable without login. Follow-up requires a controlled interactive query and preservation of the raw CSV/export and field labels.
- **Punji:** public pages for BGWT, MEHL, RAWA, RHGCL and ULHC were inspected. The published history tables cover 12 months, December 2025 through November 2026; the target date 2025-07-28 is outside that displayed window. The pages describe monthly open/high/low/close and shares traded, with adjustment note that pre-bonus closes are divided by (1 + bonus), while cash dividends and rights are not adjusted. Punji's stock pages state that prices are NEPSE's as-traded data, and its terms say market data is sourced from public NEPSE endpoints but also disclose reliance on a small number of third-party service providers. This is a source claim, not proof of independent upstream lineage. No target-date row was captured.
- **ShareHub and Chukul:** no licensed account, bearer token, allow-listed IP, or Chukul historical entitlement was available in this check. No protected data was accessed or authentication attempted.

Disposition: the NEPSE Alpha date-filter UI is a concrete next public-access path; Punji's presently displayed public stock-page history does not cover the target date. No new dated provider row, independent source lineage, or qualifying 4-of-6 vote was obtained. Existing user-authoritative records, field quarantines and no-promotion decisions remain unchanged.


## Raw floorsheet replay and contract identification follow-up

Fetched the original SocrateAI Git blob `9c5533626b354d5fefca06d6762d51e0b9beaac6` (returned text length 10,026,040), parsed the five symbols and independently recomputed counts, quantity, turnover and extrema. All five counts/quantities/turnovers match the archived board. BGWT 194/14028/13256345/925–992; MEHL 333/29753/14008898.10/460–480.5; RAWA 74/3165/2515662.50/780.3–811; RHGCL 1030/296715/103872614.40/341.4–362; ULHC 300/32288/16273342.10/495–515. All 1,931 target contracts have the same two-character substring `01` at positions 9–10; this includes nine sub-10-share executions (BGWT 3, RHGCL 5, ULHC 1), so that substring cannot by itself discriminate the suspected odd lot from the other executions. No official mapping or trade-type flag verified. Exact BGWT exception row: `2025072801025823,BGWT,54,48,1.0,925.0,925.0,2025-07-28`. Preserve unchanged. No timestamps in source; official close remains unverified. Raw tape upstream independence remains unproven. 

Outstanding provider coverage: historical NEPSE Alpha chart endpoint candidate documented by community at https://github.com/globalpolicy/NepseWatcher/blob/main/MDD.txt; read-only BGWT date-window request https://www.nepsealpha.com/trading/1/history?symbol=BGWT&resolution=1D&from=1753574400&to=1753833600&currencyCode=NRS was inaccessible to retrieval tool, no HTTP status/raw response available. Chukul https://chukul.com/technical-desk/details advertises adjusted prices and sign-in; no dated response obtained. ShareHub documentation continues to require authorized data API access; no new dated response. Punji historical coverage remains unresolved. No new qualifying votes or lineage proof. P1 open; 4/6 gate unchanged, no official close confirmed, no record promoted, no source data edited.


## Regulatory rule check and targeted public-source recheck — 2026-11-27

### BGWT one-share exception: legal context, not contract proof

- The Securities Board of Nepal's 2019 English compendium reproduces the Securities Trading Byelaws, 2018, By-Rule 5. It states board lots of 100 units for Rs 10 nominated-price shares and 10 units for Rs 100 nominated-price shares; below-board-lot securities are described in the bylaw as **de-prioritized transactions**, excluded from price-change-limit and market-index calculations. The compendium itself says its English text is an unofficial translation and that the Nepali version controls in case of ambiguity: https://www.sebon.gov.np/uploads/uploads/UUqlgCkhxAnGbqkZMirCcGEdtFnx4KBmNeQqdicw.pdf (printed pages 633–634; PDF text lines 16725–16734).
- Contemporary reporting on 2025-07-17 says NEPSE had just made odd-lot orders visible in website market depth; it describes 10 shares as the board lot for Rs 100 face-value securities and says odd-lot transactions do not affect price limits or index calculations: https://eng.merolagani.com/NewsDetail.aspx?newsID=116589 and https://www.sharesansar.com/newsdetail/nepse-enables-market-depth-visibility-for-odd-lot-orders-from-shrawan-1-2025-07-17.
- This supports the **plausibility** that a one-share BGWT contract at Rs 925 could be an odd-lot/de-prioritized execution that does not set the published daily low. It does not prove the actual contract was flagged that way. Preserve `2025072801025823,BGWT,54,48,1.0,925.0,925.0,2025-07-28` unchanged and retain `suspected_odd_lot_pending_trade_type_confirmation`. Do not infer the exchange trade-type from quantity alone; obtain the contract's exchange segment/order-type flag or written NEPSE confirmation. Also verify the applicable Nepali bylaw text and amendments effective on 2025-07-28 before treating the 2019 English compendium as the definitive legal text.

### Additional public-provider coverage observations

- **Punji:** its current public BGWT page labels its snapshot date and exposes only the 12 monthly rows from December 2025 through November 2026. Its seasonality page says company price history begins 11 May 2025 and that account users can see company history from the start. This creates a possible authorized-account follow-up for 2025-07-28, but no dated daily OHLCV row or export for the target date was obtained in this public-source check. The 12-month public table is not a target-date vote: https://punji.app/stocks/BGWT and https://punji.app/seasonality.
- **NEPSE Alpha:** the public `/nepse-data/` page exposes daily/weekly/monthly history filters, symbol selection, start/end dates and CSV controls. Search/index extraction still returns only a current-date snapshot; the documented chart-history URL candidate for BGWT (and equivalent symbols) could not be retrieved through the available public page reader. No raw 2025-07-28 response, export, HTTP status or provider vote was obtained. Do not count the UI or advertised historical capability as a dated row: https://nepsealpha.com/nepse-data/.
- **Chukul and ShareHub:** no new dated rows or authorized-access response were found in this public-source pass. Existing access/coverage limitations remain unchanged.

### Disposition

No additional dated provider record was recovered in this pass. Dated evidence remains 2/6 at most, with only one demonstrated ShareSansar-derived lineage plus incomplete MeroLagani replay evidence; the formal 4/6 and two-independent-lineage gate remains unmet. Official exchange-designated close remains unverified for all five securities. No record was promoted, no raw market data was modified, and P1 remains open.

## Evidence-first, field-level approval policy — 2026-11-27

This section supersedes the earlier interpretation that every field must first satisfy a universal 4-of-6 secondary-provider vote. The 4/6 plus two-independent-lineage rule remains the project's **secondary-source consensus fallback**, not a NEPSE regulatory requirement and not a veto over sufficient authoritative exchange evidence.

### Approval hierarchy

1. **Authoritative official exchange evidence:** An authentic NEPSE record may establish a field directly when the record is date/security-specific, its field definition and applicable calculation method are known, its adjustment status is known, and integrity/provenance are preserved. A qualifying official record does not need four secondary websites to repeat it. Do not call a secondary chart or a public page an official exchange record merely because it displays NEPSE data.
2. **Reconstructed floorsheet evidence:** Existing contract-level floorsheet data may establish derived measures only to the extent that the required fields, ordering/timestamps, trade eligibility and calculation rules are present. Preserve raw contracts; calculate in a reproducible script or ledger; record the inclusion/exclusion rule and contract IDs. Do not infer trade type from quantity or an undocumented contract-code substring.
3. **Secondary-source reconciliation:** Where an authoritative exchange record or fully reproducible eligible-trade reconstruction is unavailable, use the 4-of-6 provider / at-least-two-independent-lineage rule as the secondary consensus route. Multiple websites that republish the same upstream feed count as one lineage. A blocked or unaudited provider is neither a vote nor evidence of failure.
4. **Field-specific disposition:** Approve fields that pass their own evidence and semantic checks; quarantine only unresolved fields. A conflict in Close must not automatically invalidate independently supported Open, High, Low, volume or turnover. Never overwrite the user's owner-authoritative values for BGWT, MEHL, RAWA, RHGCL and ULHC on 2025-07-28.

### Reuse-first calculation plan for the five securities — 2025-07-28

Use the existing SocrateAI floorsheet archive, extracted daily-board rows, ShareSansar-derived chart/archive evidence and the already recorded MeroLagani date-filtered results. Do not repeat completed captures or purchase API access unless a specific missing field cannot be resolved from these artifacts.

| Field | Existing-evidence treatment | Conditions / unresolved points |
|---|---|---|
| Open | Derive from the first eligible regular-session execution, then compare with existing chart Open | Requires reliable execution chronology and the applicable opening-session / trade-eligibility rules. The archived floorsheet has no timestamps; file order alone is not accepted as chronology. |
| High / Low | Derive extrema from eligible executions, then compare with chart High / Low | Requires trade-type eligibility. Preserve the BGWT one-share Rs 925 contract as suspected_odd_lot_pending_trade_type_confirmation; do not silently include/exclude it from official OHLC. |
| LTP | Identify the last execution only when reliable sequence/time is available; preserve literal provider LTP labels | LTP is not automatically the official closing price. |
| Official Close | Keep distinct from LTP and full-day VWAP | Accept only from an authenticated official exchange record with the historical method/field semantics established, or a fully reproducible calculation using the official method and eligible trades. |
| Quantity / volume | Sum contract quantities using the documented session scope; reconcile to chart totals | Preserve raw contract IDs and exact quantity. Explain any trade-category exclusions or inclusion rules. |
| Turnover | Sum contract consideration using documented units/rounding; reconcile to chart totals | Keep currency and rounding explicit; do not substitute VWAP or price times rounded volume for exact turnover. |
| VWAP | Recompute as eligible traded consideration divided by eligible quantity; compare to archived VWAP | State whether odd-lot/de-prioritized executions are included. Do not store VWAP in Close. |
| Odd-lot classification | Use an explicit exchange trade-type/segment/order flag or official confirmation | Quantity alone, contract-code substring, or a price outside chart Low/High is not proof of classification. |

### Current five-stock evidence facts retained

The existing replayed floorsheet aggregation reports:

| Symbol | Contracts | Quantity | Turnover (Rs) | Floorsheet min–max (Rs) | Full-day VWAP (Rs) |
|---|---:|---:|---:|---:|---:|
| BGWT | 194 | 14,028 | 13,256,345.00 | 925.00–992.00 | 944.9918 |
| MEHL | 333 | 29,753 | 14,008,898.10 | 460.00–480.50 | 470.8399 |
| RAWA | 74 | 3,165 | 2,515,662.50 | 780.30–811.00 | 794.8381 |
| RHGCL | 1,030 | 296,715 | 103,872,614.40 | 341.40–362.00 | 350.0754 |
| ULHC | 300 | 32,288 | 16,273,342.10 | 495.00–515.00 | 504.0059 |

These are existing archived/replayed calculations, not newly acquired data. They establish arithmetic consistency for the captured tape, but do not by themselves establish official trade eligibility, opening/last execution chronology, official Close methodology, or upstream lineage. The BGWT one-share Rs 925 execution remains preserved and pending its explicit trade-type flag.

### Decision and next actions

- Reuse the current raw floorsheet and chart artifacts; no broad recapture and no API purchase authorized or required at this stage.
- Build/verify a reproducible field-level comparison from the existing files, with raw contract references and per-field pass/quarantine results.
- Resolve only the missing chronology and eligibility details that materially affect Open, High, Low, LTP, VWAP or official Close. If those details are absent from existing artifacts, identify that exact gap before requesting any additional evidence.
- Keep Close, LTP and VWAP as separate fields. The five Source A values match MeroLagani's dated LTP; the competing ShareSansar-derived Close/VWAP values remain a distinct measure. No official exchange Close has yet been established.
- No canonical promotion or training until each field's own gate passes. P1 remains open; 616 session-date candidates and 196,784 repeated-OHLCV candidates retain their existing statuses.
