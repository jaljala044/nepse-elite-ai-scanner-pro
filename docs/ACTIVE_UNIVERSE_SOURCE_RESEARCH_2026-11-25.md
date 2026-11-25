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
