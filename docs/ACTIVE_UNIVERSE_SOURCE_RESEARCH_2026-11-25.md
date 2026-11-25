# Active universe source research — 2026-11-25

## Decision

**Do not publish a verified active-universe manifest yet.** The agreed working target is 281 equities and 47 mutual funds, but accessible evidence is inconsistent and does not provide a complete, dated, primary-source instrument registry for 25 November 2026.

## Source observations

| Source | Observation | Evidentiary status |
|---|---|---|
| [NEPSE official stock list](https://www.nepalstock.com.np/stocklist) | Search-index snapshot dated 15 Oct 2026; exposes symbol/price rows but not a complete dated instrument-type/status registry in the accessible extraction | Primary exchange source, stale/incomplete for this manifest |
| [NEPSE official catalogue](https://www.nepalstock.com.np/en/catalogue) | Official catalogue page; accessible indexed snapshot dated 24 Sep 2026 | Primary source, but snapshot is not a complete 25 Nov registry export |
| [NEPSE Alpha listed stocks](https://nepsealpha.com/traded-stocks/) | Page shows 284 entries in the actively traded stock table and a separate 652-record listed-instrument table with Status and Instrument fields (including Equity and Active/Delisted) | Secondary source; useful discrepancy discovery, not authoritative membership |
| [Nepsense mutual-fund directory](https://nepsense.com/sectors/mutual-fund) | Previously retrieved snapshot reports 47 mutual-fund schemes as of 24 Nov 2026 | Secondary; conflicts with other secondary directory |
| [ShareRocketPro mutual-fund directory](https://www.sharerocketpro.com/markets/mutual-funds) | Previously retrieved snapshot reports 47 mutual-fund scrips as of 24 Nov 2026 | Secondary; not an exchange registry |
| [Punji mutual-fund directory](https://punji.app/sectors/mutual-fund) | Search-index snapshot dated 23 Nov 2026 reports 11 funds and 2 delisted or suspended | Secondary; materially conflicts with 47-fund claim |
| [Merolagani listed companies](https://cdn.merolagani.com/CompanyList.aspx) | Displays a sector-organized company list and a mutual-fund section, with examples of fund symbols | Secondary; partial directory, not a dated complete status register |

## Implications

1. The secondary 284 actively traded stock count differs from the agreed 281-equity target. Do not remove three names based on guesswork.
2. Mutual-fund counts differ sharply: two directories report 47 while another reports 11 active/listed funds plus two delisted or suspended. These sources may define funds, schemes, instruments, and statuses differently.
3. A current trading list is not the same as a full listed-instrument register. It can omit suspended instruments and historical lifecycle states.
4. The manifest must separate instrument_type, listing_status, trading_status, and lifecycle effective dates. Do not infer one from another.
5. The 281 + 47 target remains a project scope instruction, not a verified exchange fact.

## Required next evidence

Obtain a dated NEPSE/SEBON registry export or capture a reproducible official endpoint response that includes at least:
- security/instrument ID and symbol;
- issuer or scheme name;
- instrument type (ordinary equity, mutual fund, debt, preference, etc.);
- listing, suspension, resumption and delisting status/effective dates;
- source URL, retrieval timestamp, response hash and published effective date.

Retain the unmodified response and its SHA-256. Normalize into a versioned manifest only after source schema and membership are reviewed. Reconcile the exact 281 + 47 counts at symbol/ID level and explain every discrepancy. Preserve historical lifecycle rows for point-in-time research.

## Guardrails

- Do not fabricate a 281-symbol or 47-fund list from secondary pages.
- Do not treat active trading display as legal listing status.
- Do not silently classify ambiguous preference shares, promoter shares, closed-end funds or debt as ordinary equity.
- Do not drop historical observations when a security becomes suspended or delisted.
- Do not promote OHLCV or floorsheet data into canonical/training use until the manifest, provenance and redistribution rights are verified.


## Additional registry discovery attempts — 2026-11-25

A further search for an official instrument-type and lifecycle registry/API did not surface a reproducible public NEPSE/SEBON endpoint response containing security IDs, symbol, instrument type and effective listing/suspension/delisting dates together. The official catalogue remains a live/indexed catalogue page rather than an accessible dated lifecycle export.

A third-party NEPSE SIMPLE symbol page exposes a broad mixed set of symbols, including ordinary shares, mutual funds and debt-like instruments. This reinforces why symbol-only scraping is unsafe: instrument classes must be identified from an authoritative registry, not guessed from ticker shape or a broad list.

No exact 281 + 47 manifest has been generated. The required next acquisition is an official NEPSE/SEBON/registrar/CDSC data export or documented official endpoint with stable instrument IDs and lifecycle dates. CDSC/registrar data may corroborate units/scheme identities but should not silently replace NEPSE's exchange listing/trading status.

## Official stock-list evidence refresh — 2026-11-25

A fresh public-source check confirms that NEPSE's own [stock-list page](https://www.nepalstock.com.np/stocklist) is indexed with a dated market snapshot (the accessible indexed page reports 2026-10-15, 3:00 PM). The page exposes a search-by-symbol/company-name interface and a long live/dated symbol display. The official [asset list page](https://www.nepalstock.com.np/assetlist.html) also links to corporate information and Listed Securities.

This is stronger source provenance than a third-party ticker list, but it is not yet a machine-captured immutable instrument registry:
- the stock-list page is a market/trading display, not a complete lifecycle registry;
- the accessible page does not expose a verified security-ID / instrument-type / effective listing, suspension, resumption and delisting table in the captured text;
- the indexed stock-list snapshot is dated 2026-10-15, not the requested 2026-11-25 point-in-time snapshot;
- a candidate /api/nots/security?nonDelisted=true route appears in third-party NEPSE API client documentation, but the endpoint response was not retrievable through the current research connector and has not been independently confirmed as a stable official contract.

Accordingly, the page is retained as a primary-source discovery lead, not as the 281-equity + 47-fund manifest. No symbols are promoted from the page into the target universe based solely on display presence or ticker shape. The next evidence capture must preserve the official raw response, retrieval timestamp, SHA-256, security ID, symbol, instrument type, status and effective dates, then reconcile every difference to the exact target counts.


## SEBON registry-source refresh — 2026-11-25

The official SEBON site exposes separate catalogues for [MFS Approved](https://sebon.gov.np/mfs-approved), [MFS Pipeline](https://sebon.gov.np/mfs-pipeline), and [Securities Registered](https://sebon.gov.np/securities-registered). These are useful primary source collections, but they are not, by themselves, a single exchange listing/trading lifecycle manifest.

- The SEBON MFS Approved page's search index currently surfaces an approved-list item dated **2026-10-05** (2083-06-19), and the MFS Pipeline index surfaces filings dated **2026-10-28** and **2026-10-30**. The page opened through the current research renderer returned an older July 2026 page snapshot, so the October search-index entries need exact PDF-byte capture and validation before they can be used as a frozen register.
- The latest directly opened approved PDF in the page renderer is dated **2026-07-09**, "Mutual Fund Scheme Approved", as of 2083/03/25. It contains 33 approval/additional-unit registration rows across six PDF pages; repeated rows include later additional-unit registrations for already named schemes. It reports unit/issue totals, not the number of distinct exchange-listed and currently tradable mutual-fund scrips.
- The official SEBON Securities Registered page was accessible as a catalogue heading, but its extracted page content exposed no row-level registry table or downloadable instrument/status export during this review.
- A current prospectus list contains offers and new fund names, but a prospectus is not proof that the resulting unit is already listed and trading on NEPSE.

Therefore these SEBON primary sources improve the regulator-side scheme and registration evidence, but they do **not** yet validate a current 47-fund NEPSE trading list. The 281-equity + 47-fund scope remains an explicit project target, not an independently verified registry count. The next step is to capture exact dated PDFs/registrar records and crosswalk scheme names to NEPSE security IDs, ticker symbols and actual first/last trading dates.


## 2026-11-25 official-source cross-check

### NEPSE official stock-list snapshot

The NEPSE [official stock-list page](https://www.nepalstock.com.np/stocklist) is indexed with a market snapshot dated **2026-10-15 15:00**. Its page summary reports **349 total scrips traded** for that session, alongside daily transaction and turnover totals. That is a traded-scrip count across the exchange's mixed instrument population, not a count of 281 ordinary equities plus 47 mutual funds. The page is not a complete dated instrument-type/lifecycle export. The same indexed snapshot carries a 2026-10-15 BHDC security suspension/revocation notice, illustrating why page display presence must not be treated as definitive trading status without effective-dated status evidence.

### SEBON primary mutual-fund records

The latest directly opened SEBON [MFS Approved PDF](https://www.sebon.gov.np/uploads/2026/10/28/InwxdsnP05pazi2Y3vSl4HeeBikPKO89pJ3BSG97.pdf), dated 2026-10-28 and stated as of 2083/07/11, records six scheme/registration rows: NIBL Sabhagita Fund (open-end), Muktinath Mutual Fund 2 (close-end), NIC Asia Equity Opportunity Fund (close-end), Citizens Super 50 (close-end), Shubha Laxmi Kosh (open-end), and Nabil Growth Fund (close-end). Some rows are additional unit registrations for existing schemes. This is a regulator approval/registration history, not a complete NEPSE trading list.

The SEBON [Mutual Fund Scheme Pipeline Status PDF](https://www.sebon.gov.np/uploads/2026/10/30/4TXSEQWU4MveZ7z1ZQHWwbiEnhHHwrYolGKonX8h.pdf), as of 2083/07/13 (2026-10-30), lists six schemes under preliminary review and two in the "Reviewed and Comment Sent" section. Pipeline/approval status must not be interpreted as exchange listing or trading commencement.

### Secondary discrepancy evidence

A 2026-11-08 secondary industry overview reports 47 closed-end schemes, with 45 trading on NEPSE and two newly issued but not yet trading. A separate secondary directory dated 2026-11-24 reports 43 listed schemes. These may use different definitions or update cutoffs; neither can replace an official exchange registry.

### Priority 99 outcome

Primary-source discovery improved, but **the exact dated 281-equity + 47-mutual-fund active trading register remains unverified**. The 2026-11-24 floorsheet sample contains 347 distinct symbols in one source file, which is 19 more than the arithmetic target of 328. Those 19 symbols are not automatically errors or excluded classes. They must be mapped to official security IDs, instrument types and effective lifecycle dates.

Do not promote any symbol-only list into the canonical target universe. The next required source is a raw NEPSE security-list response or official dated export that can be preserved with retrieval time, source hash, security IDs, instrument types, and status effective dates. SEBON approvals and pipeline rows should be cross-references, not substitutes for exchange listing/trading status.
