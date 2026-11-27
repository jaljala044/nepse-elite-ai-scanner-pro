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