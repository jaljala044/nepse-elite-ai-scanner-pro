# 3A.01 — NepseAlpha catalogue table-scope verification

**Audit date:** 2026-11-27  
**Source:** https://www.nepsealpha.com/traded-stocks  
**Disposition:** **Secondary catalogue scope verified; complete 652-row payload not acquired.**  
**No candidate manifest, reviewed-row manifest, or OHLCV data was changed.

## What the page exposes

The current public page presents two distinct tables:

1. **Active Stocks table**
   - Explicit page text: "Only actively Traded Stocks in NEPSE are listed in the table."
   - Publicly indexed pagination: 1 to 10 of **284 entries**, 29 pages.
   - Fields shown: Symbol, Company, LTP, Share Outstanding, Floated Shares, Market Cap (NPR), Floated Market Cap, Impact in NEPSE and 50D Avg Volume.
   - The table does not provide lifecycle or instrument classification fields in the indexed header.
2. **Nepal Stock Exchange Data table**
   - Publicly indexed pagination: 1 to 10 of **652 entries**, 66 pages.
   - Fields shown: S.n, Name, Symbol, Status, Sector, Instrument, Email and Website.
   - The first indexed page includes examples of both Active and Delisted statuses, with Instrument shown as Equity for those examples.
   - This broader table is materially more useful for candidate-universe discrepancy discovery than the 284-entry actively-traded table.

Sources:
- Current search-rendered page showing both tables, their headers, counts and first ten rows: https://www.nepsealpha.com/traded-stocks
- Current page fetch (2026-11-27) confirms the Nepal-local page date ११ मंसिर २०८३, शुक्रबार and returns the first 10 active-stock rows and the 284-entry pagination. It does not expose the second table's complete rows in the extraction response.
- Earlier search-indexed snapshots also showed the 652-entry table, but no complete 652-row export or stable API contract was obtained.

## Extraction limits and reconciliation safety

- The 652 figure is the pagination count of the second table, not the active-traded table and not a verified count of active ordinary equities.
- The first page's 10 rows are not a complete data capture. Do not extrapolate all 652 rows from the first page.
- A separate browser automation attempt to inspect network requests could not start because the external browser automation wallet balance was negative. No XHR endpoint, pagination parameter, export URL, or API schema is asserted.
- The fetched page extraction response returned only the 284-entry active-stock table; the search-rendered page exposed the second 652-entry table's first ten rows and pagination. This is an extraction-scope difference, not evidence that either table has been deleted.
- The provider's Status and Instrument labels are secondary-source classifications. They do not establish exchange-authenticated status, effective dates, complete lifecycle history, or source completeness.
- No comparison of all 652 symbols to the 281 candidate symbols was possible. No unmatched/additional/inactive counts are claimed.

## Impact on 3A.01

1. Retain the 281-symbol list as the development candidate universe.
2. Use the 652-entry secondary table as a prioritized next cross-check only after its complete paginated payload is acquired and preserved with retrieval metadata and a hash.
3. Do not use the 284 actively-traded count as complete listed-equity membership.
4. Do not promote status/instrument classifications from this provider to primary exchange facts.
5. Keep `membership_authoritatively_verified=false`, `promotion_allowed=false`, and the canonical reviewed-row manifest empty.

## Next action

Acquire all 66 pages (or a documented full export) of the 652-entry table in a reproducible, permitted manner; preserve the raw response, pagination metadata, retrieval timestamp, and SHA-256. Reconcile exact symbols, names, statuses and instrument types to the 281 candidates. Independently authenticate any material discrepancies with NEPSE/SEBON/CDSC primary records before changing universe membership.
