# 3A.01 — Official NEPSE Listed Securities UI access audit

**Audit date:** 2026-11-27  
**Primary source:** https://www.nepalstock.com.np/company  
**Disposition:** **Official interactive security register discovered; complete export not captured.**  
**No candidate manifest, reviewed-row manifest, or OHLCV data was modified.

## Primary-source findings

The current NEPSE website's own navigation links to a **Listed Securities** interface at `/company`. Unlike the older stocklist page shell, this route is server-rendered by the browser extraction and exposes the following controls and fields:

- Status filters: Active, Suspended, Delisted.
- Sector filters: Commercial Banks, Manufacturing And Processing, Hotels And Tourism, Others, Hydro Power, Tradings, Non Life Insurance, Development Banks, Finance, Microfinance, Life Insurance, Investment.
- Instrument filters: Equity, All Instrument, Mutual Funds, Non-Convertible Debentures, Preference Shares.
- Page-size options: 10, 20, 50, 200, 300, 500.
- Table fields: SN, Name, Symbol, Status, Sector, Instrument, Email, Website.
- Default page size observed: 20; pagination control shows page 1 through page 15.
- First-page extraction returned 20 records, SN 1–20. All 20 are labelled Active / Equity. Examples include NABIL, NIMB, SCB, HBL, SBI, EBL, NICA, MBL, LSL, KBL, SBL, SHL, TRH, OHL, NHPC, BPCL, CHCL, STC, BBC and NUBL.

The separate NEPSE homepage/dashboard extraction exposed an "As of Nov 26, 2026, 3:00:00 PM" market snapshot and a current market summary of 355 scrips traded. This is a daily activity count, not total listed securities or active-equity membership.

## API access check

A public reverse-engineered NEPSE client repository identifies the following routes as its company/security list calls:

- `GET /api/nots/company/list`
- `GET /api/nots/security?nonDelisted=true`

The checked-in third-party route map is at:
https://raw.githubusercontent.com/basic-bgnr/NepseUnofficialApi/master/nepse/data/API_ENDPOINTS.json

A read-only, unauthenticated request to both routes on the current official host returned HTTP **401 Unauthorized** on 2026-11-27. No authentication headers, token-generation logic, or undocumented access mechanism was attempted. The client is reverse-engineered third-party evidence, not an official API contract. The observed 401 confirms that these direct unauthenticated requests cannot currently supply the raw security master.

## What remains unverified

- The extractor did not expose a complete page-size-500 result or page traversal, and no raw JSON/API response, export file, or stable documented pagination contract was captured.
- Fifteen pages at the default 20-row setting is a UI page count, not a certified total number of securities.
- First-page status and instrument values cannot be generalized to later pages.
- The official `/holiday-listing` route returned only a loading shell in the extraction. No official holiday calendar rows were captured in this audit.
- Public reporting says NEPSE changed its trading week to Monday–Friday in April 2026, but that secondary reporting is not a complete exchange holiday/session calendar. Do not infer open sessions from weekday alone.
- No complete dated official listing snapshot or lifecycle history has been preserved.

## Safe next steps

1. Use the NEPSE Listed Securities UI directly to select **Equity** and **Active**, then increase page size to 500 and capture every returned row. Preserve the raw response and retrieval metadata if an export/API response becomes available.
2. Repeat with Suspended and Delisted statuses, and separately inspect other instrument classes so the universe does not silently mix equities, funds, debentures or preference shares.
3. Hash the unmodified raw capture; record retrieval time, filters, page-size, pagination, source URL and all visible row fields.
4. Compare the resulting exact symbol/name/sector/status/instrument rows with the 281-symbol candidate manifest. Record all unmatched, duplicate, inactive, non-equity and name/symbol-change cases without automatically changing the manifest.
5. Acquire official exchange holiday notices and dated closure evidence before labeling a historical date as a valid trading session.

## Scanner gate

The official primary-source UI materially improves the acquisition path, but the full rows and raw response are still missing. Keep `membership_authoritatively_verified=false`, `promotion_allowed=false`, and the canonical reviewed-row manifest empty. The 281 symbols remain development candidates only.
