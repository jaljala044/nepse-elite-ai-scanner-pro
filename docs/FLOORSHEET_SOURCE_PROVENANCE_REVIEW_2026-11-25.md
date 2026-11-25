# Floorsheet source provenance review — 2026-11-25

## Purpose

This review distinguishes exchange-origin evidence, third-party acquisition claims, and downstream copies. It does not select a canonical source or make a legal determination.

## Findings

| Candidate | What was verified | Provenance assessment | Use decision |
|---|---|---|---|
| [Urekmazino HF dataset](https://huggingface.co/datasets/urekmazino69/Nepse-floorsheet-and-indices) | The live data card declares MIT, describes daily floorsheets as compiled from public NEPSE data, lists the 11-column schema, and gives a published coverage window ending 2026-08-26. A preview row is dated 2024-01-02. | Publisher-level claim only. The card does not identify an exact NEPSE endpoint, acquisition code, response archive or independent source lineage. Its licence declaration must not be read as proof that the publisher owns all upstream data rights. | Use for bounded parsing/reconciliation research only; keep raw bytes and hashes; no canonical promotion yet. |
| [SocrateAI NEPSE Open Data](https://github.com/socrateai-official/nepse-open-data) | Public README describes daily floorsheet and OHLC/indices data. The repository includes an MIT licence file. | The reviewed README does not document the original acquisition endpoint or a reproducible source chain. Earlier 70-date overlap review with Urek found matching shared rows, but matching values do not establish independent lineage. | Retain as a separate publisher copy for comparisons; do not call it independent confirmation without upstream evidence. |
| [SamirWagle NEPSE All Scraper](https://github.com/SamirWagle/Nepse-All-Scraper) | README states floorsheets are scraped from Merolagani. The inspected \`scraper/core/floorsheet.py\` sets the request URL to \`https://merolagani.com/Floorsheet.aspx\`, paginates the displayed table and stamps each scraped row with \`date.today()\`. | This is a documented Merolagani-derived capture path, not a direct NEPSE API path. The code uses the local capture date rather than an independently parsed trade date, so the date field must be checked against the source page and file-level context before historical use. | A useful separate comparison lead; a daily scraper snapshot is not proof of multi-year backfill. |
| [YONEPSE source credits](https://shubhamnpk.github.io/yonepse/pages/sources.html) | Its source page credits the NEPSE Official API for live prices, index snapshots, disclosures, floorsheets and index history for the trailing year; it credits SocrateAI for longer historic sub-index/headline index series. | This is a third-party description of its own source architecture, not an exchange-issued API contract. It supports pursuing official exchange-origin data for recent floorsheets, but does not itself provide the required frozen data archive or rights. | Use as a discovery lead for official endpoints; verify any endpoint and preserve each response independently. |

## Cross-source implications

1. A common publisher licence is not proof of common or independent origin. Keep each publisher and each pinned revision separate.
2. A matching transaction set across two public archives is a data consistency observation, not proof that two independent acquisition events occurred.
3. Merolagani-derived rows must not be assigned a historical trade date solely from a scraper's current-date stamp.
4. Broker codes identify trading-member channels in the reported transaction, not beneficial owners.
5. Do not treat a third-party source's "complete" or "all transactions" description as a verified universe/date completeness result.

## Implementation note

The repository now contains an explicit Urek source profile in \`backend/app/floorsheet_source_profiles.py\`. It maps:

- \`calculation_date\` → \`trade_date\`
- \`contract_no\` → \`contract_id\`
- \`stock_symbol\` → \`symbol\`
- \`buyer\` / \`seller\` → buyer/seller broker codes
- \`quantity\`, \`rate\`, \`amount\` → corresponding canonical values

The profile records \`time\`, \`sector\` and \`id\` as source-only fields. The underlying raw CSV must remain immutable so those fields remain available. The public preview's \`time\` is null; execution timestamps are not synthesized.

The profile is intentionally marked \`publisher_schema_declared_raw_header_not_yet_reviewed\`. Its synthetic fixture test validates mapping behavior, not the exact physical CSV header or payload hash.

## Next acquisition/reconciliation actions

- Retrieve one small raw sample file from a pinned Urek revision and record its exact SHA-256, byte count, response metadata and physical CSV header.
- Obtain one same-date Merolagani-derived sample from an independently traceable capture and compare date, contract number, symbol, broker codes, quantity, rate and amount.
- Compare the Urek and SocrateAI same-date files at contract level while keeping lineage status explicitly unresolved.
- Obtain written or published terms for storage and intended analytics use before any redistribution or public release.
- Keep all samples in a non-canonical review area until data rights, date correctness, coverage and control totals are accepted.


## Pinned MeroLagani-derived capture audit — 2026-11-25

A source CSV from SamirWagle was fully acquired and inspected for one date. See [MEROLAGANI_FLOORSHEET_CAPTURE_AUDIT_2026-11-24.md](MEROLAGANI_FLOORSHEET_CAPTURE_AUDIT_2026-11-24.md).

- Pinned file: \`SamirWagle/Nepse-All-Scraper@e6160adc6bdf3d19562167388e3d9d4f645c455a:data/floorsheet/floorsheet_2026-11-24.csv\`.
- Size 3,538,179 bytes; Git blob SHA-1 \`22eaa891b30aac2fe4cf197053efa014953351c0\`; computed full-payload SHA-256 \`2687b7ed6bc5ebd737fa459ca8dd620941bb3ec1da6613fbd620550495018f55\`.
- The pinned scraper code requests \`https://merolagani.com/Floorsheet.aspx\`, paginates the displayed table and writes Python \`date.today()\` to the CSV date field. This must be treated as capture date until confirmed against the original page/date context.
- The complete file has 52,369 rows, unique contract IDs, 347 symbols and no quantity × rate = amount exceptions.
- The first eight CSV rows match the indexed MeroLagani page snippet for 2026-11-24. The indexed MeroLagani page displays total quantity 14,670,177 and total amount NPR 5,553,019,249.46; the Samir CSV sums to quantity 14,662,346 and NPR 5,551,668,556.66. The mismatch is unresolved and the CSV's serial column has 16 gaps.
- The pinned repo README uses a license badge marked “Educational”; the pinned repository tree contains no LICENSE or COPYING file. No data reuse / redistribution grant was established.

Decision: the file is a valuable dated sample and MeroLagani-derived comparison lead, but is **not** accepted as a complete daily dataset. Keep the control-total conflict, serial gaps, capture-date semantics and licensing status attached to the source. No canonical or training promotion.
