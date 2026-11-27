# Secondary NEPSE data-provider cross-validation matrix — 2026-11-27

## User-requested providers

The project owner recommends cross-checking data against Chukul, ShareHub, Punji, NEPSE Alpha, Sharesansar and MeroLagani. Add all six to the secondary-source validation programme. This supplements, but does not replace, exchange-origin evidence.

## Current recorded status

| Provider | Evidence/status recorded in repository | Next validation action | Classification |
|---|---|---|---|
| Chukul | Public dashboard/live ticker inspected; no dated 2025-07-28 daily OHLCV or public historical route obtained. Login/subscription entitlement was not tested. | With the project owner's authorized account, inspect dated daily history and record exact field labels, coverage, export/API contract and terms. | Access-limited / historical result not verified |
| ShareHub | Earlier investigation found sharehu.com inaccessible/403 and identified Share Hub Nepal (sharehubnepal.com) as a possibly intended service. Its all-time API documentation requires licensed API access, bearer token and allow-listed server IP; no authorized credentials were available. | Confirm exact provider/domain; obtain authorized API access if desired; capture documented schema, raw responses, coverage and licence terms. | Potential licensed source; no data retrieved |
| Punji | No source-specific capture or validation evidence is recorded in the reviewed P1 investigation log. | Confirm exact official domain/app; inspect dated daily history for target symbols/dates and capture field semantics, provenance and terms. | Not yet audited |
| NEPSE Alpha | No source-specific capture or validation evidence is recorded in the reviewed P1 investigation log. | Confirm exact official domain/app; inspect dated daily history and any export/API, capture field semantics, provenance and terms. | Not yet audited |
| Sharesansar | A ShareSansar-derived daily board/CSV has been compared. Its Close/VWAP aligns with Source B for all five 2025-07-28 securities; another ShareSansar-derived archive aligned with Source A. | Retrieve/retain original publisher page/export for each row; distinguish LTP, official close and full-day VWAP; establish source lineage and historical coverage. | Secondary corroboration; close semantics conflict |
| MeroLagani | Dated Price History queries were completed for all five symbols on 2025-07-28. Its LTP and O/H/L/quantity match Source A. The field is explicitly labelled LTP. | Preserve source pages/raw captures and recheck turnover/quantity and historical coverage; do not relabel LTP as exchange-designated close without NEPSE confirmation. | Secondary corroboration for five rows; not exchange certification |

## Required validation protocol for every provider

1. Record exact canonical domain, page/API endpoint, request method, parameters, retrieval time and access mode (public, login or licensed API).
2. Preserve raw response/export bytes and response headers/metadata where available; calculate SHA-256 before parsing.
3. Record literal field names. Keep LTP, last trade, official close, VWAP, adjusted close and previous close distinct unless a documented mapping proves equivalence.
4. Capture OHLC, quantity, turnover, trade count, date, symbol/security ID, currency/units, adjustment status and missing/null semantics where available.
5. Record source publication/update time, historical coverage, pagination, timezone/session-date convention, corrections and provider terms/licence.
6. Compare every field independently against other providers and NEPSE primary evidence. Do not majority-vote incompatible field definitions.
7. Classify outcomes as match, field_semantics_mismatch, value_conflict, missing, access_blocked, coverage_gap or not_audited. A failed page load or empty response is not proof of no data.
8. Maintain source independence: two sites that repackage the same upstream feed count as one lineage for corroboration, not two independent confirmations. Record upstream/source attribution whenever discoverable.
9. Maintain quarantine until project-specific acceptance criteria are met. Secondary agreement raises confidence but cannot satisfy a gate requiring exchange-origin session evidence or official close-method confirmation.

## Separate acceptance criteria

### Five disputed securities on 2025-07-28

- Complete all six secondary-provider checks where accessible and authorized.
- Reconcile exact security/date identity and every OHLCV field.
- Resolve LTP versus weighted-average close versus full-day VWAP semantics.
- Obtain NEPSE's original EOD record or written confirmation of the designated close methodology before promoting the close field as official.
- The project owner's supplied values for BGWT, MEHL, RAWA, RHGCL and ULHC remain authoritative for the project as previously instructed; secondary discrepancies are not grounds to overwrite them.

### 616-date session calendar

- Use provider calendars/market summaries as independent cross-checks, not automatic open/closed labels.
- Prefer date-scoped NEPSE session register, official daily market-summary/index records and closure/suspension notices.
- For each date, record strongest evidence and its scope. Absence from a provider calendar or a no-row response is unknown, not closed.
- Do not promote a date solely by multi-provider majority unless evidence lineage, coverage and meaning are understood and the project's acceptance policy explicitly permits it.

## Current decision

This matrix expands the secondary-source programme but does not change any existing gate. MeroLagani and Sharesansar-derived evidence already provide useful corroboration; Chukul and ShareHub remain access/coverage limited; Punji and NEPSE Alpha still need a documented audit. No primary NEPSE records have been received through this work. The 616 dates remain candidate_unverified; the 196,784 repeated-OHLCV candidates remain quarantined.