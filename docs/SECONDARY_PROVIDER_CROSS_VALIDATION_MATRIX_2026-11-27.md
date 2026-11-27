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
| ShareHub | Earlier investigation found sharehu.com inaccessible/403 and identified Share Hub Nepal (sharehubnepal.com) as a possibly intended service. Its all-time API documentation requires licensed API access, bearer token and allow-listed server IP; no authorized credentials were available. | Confirm exact provider/domain; obtain authorized API access if desired; capture documented schema, raw responses, coverage and licence terms. | Potential licensed source; no data retrieved |
| Punji | No source-specific capture or validation evidence is recorded in the reviewed P1 investigation log. | Confirm exact official domain/app; inspect dated daily history for target symbols/dates and capture field semantics, provenance and terms. | Not yet audited |
| NEPSE Alpha | No source-specific capture or validation evidence is recorded in the reviewed P1 investigation log. | Confirm exact official domain/app; inspect dated daily history and any export/API, capture field semantics, provenance and terms. | Not yet audited |
| Sharesansar | A ShareSansar-derived daily board/CSV has been compared. Its Close/VWAP aligns with Source B for all five 2025-07-28 securities; another ShareSansar-derived archive aligned with Source A. | Retrieve/retain original publisher page/export for each row; distinguish LTP, official close and full-day VWAP; establish source lineage and historical coverage. | Secondary corroboration; close semantics conflict |
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

Current evidence remains unchanged: MeroLagani and Sharesansar-derived evidence provide partial corroboration; Chukul and ShareHub remain access/coverage limited; Punji and NEPSE Alpha still need a documented audit. The five user-supplied 2025-07-28 records remain authoritative. The 616 dates remain `candidate_unverified` until date-specific session evidence meets the calendar gate. The 196,784 repeated-OHLCV candidates remain quarantined/review-only.