# Expanded NEPSE data-source discovery — 2026-11-24

This is an acquisition lead register, not a claim that any newly found dataset has
already been ingested. All publisher coverage statements below are claims to verify
against actual file manifests, hashes, row counts and source provenance.

## New discovery: ShareSansarScraper public archive

- Landing page: https://omitnomis.github.io/ShareSansarScraper/
- API overview: https://omitnomis.github.io/ShareSansarScraper/about.html
- Bulk downloads: https://omitnomis.github.io/ShareSansarScraper/download.html
- Public JSON endpoints documented by publisher:
  - `api/meta.json`
  - `api/symbols.json`
  - `api/latest.json`
  - `api/history/{SYMBOL}.json`
  - `api/recap/latest.json`
  - `api/index.json` (manifest)
- Publisher reports 927 archived trading days, archive start 2024, last update
  2026-10-30 at time of discovery. Daily CSVs mirror ShareSansar's full daily price
  table. This archive is a second copy of ShareSansar-derived EOD, not an independent
  exchange-origin source.
- The publisher states the archive is unofficial and accuracy depends on ShareSansar.
- Acquisition action: enumerate `api/index.json`, download manifest-listed daily
  JSON/CSV and per-symbol histories, record response bytes and SHA-256, compare the
  exact session set and normalized EOD rows with Jaljala, SocrateAI and other sources.
  Do not infer missing dates from a weekday schedule.

## New discovery: AnkitSanjyal NEPSE Market Data (Hugging Face)

- Dataset: https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data
- Pipeline/provenance notes: https://ankitsanjyal.github.io/projects/nepse-pipeline.html
- Publisher declares:
  - Extended EOD history from 1995-07-20 to present, 653 symbols, sourced from
    ShareSansar as a second source.
  - NEPSE EOD endpoint table for a rolling 365-day window.
  - Floorsheet from 2026-08-19, with a declared gap 2026-08-26 through 2026-11-18.
  - Derived 1-minute bars, daily broker flow and daily stats.
- The publisher's own provenance note says the historical EOD and authoritative
  NEPSE EOD tables are separate and must not be merged blindly. It also reports
  near-complete overlap on a recent 226-day validation window, but that is a
  publisher-reported check, not a substitute for our independent audit.
- Dataset license is described as `other`; review dataset card terms before copying
  or redistributing. Treat broker flow and bars as derived, not raw exchange records.
- Acquisition action: query the Hugging Face dataset-server/parquet manifest and
  download metadata/Parquet only where use is permitted; calculate row-level source
  hashes, date coverage, symbol coverage, missingness and source overlap. Keep
  `eod_history_ext`, `eod_price`, `floorsheet`, `bars_1m`, and
  `broker_flow_daily` as separate source tables.

## New discovery: srijankarki07/nepse-data (GitHub)

- Repository: https://github.com/srijankarki07/nepse-data
- README describes an append-only daily EOD archive from 2011 onward, with daily
  session CSVs, per-symbol histories and index series. It explicitly documents
  a 2026 weekly schedule change.
- Important data-rights condition: repository license says MIT covers software,
  not the data. Do not copy or redistribute its dataset under the software license.
  It may be used as a discovery/provenance reference; obtain separate permission or
  use independently licensed sources for actual data ingestion.
- Its published session list is a valuable candidate calendar for reconciliation,
  but is ShareSansar-derived and is not an official NEPSE calendar. Cross-check each
  date against other independent archives and official NEPSE notices/records.

## New discovery: shawinCreates/Nepse-Market-Data (GitHub)

- Repository: https://github.com/shawinCreates/Nepse-Market-Data
- README describes daily NEPSE OHLCV and market-overview scraping from ShareSansar,
  with history claimed from 2010 onward.
- Acquisition action: inspect LICENSE, README provenance, workflow history, manifest
  and actual file coverage before any ingestion. Treat as another ShareSansar-derived
  corroboration source unless its actual upstream data lineage proves otherwise.
  Do not count this as independent evidence merely because it is a separate repo.

## Official and regulator evidence

- NEPSE current floorsheet page: https://www.nepalstock.com/floor-sheet
  This is an exchange-origin current page and useful for current-session schema/
  spot-checks; its public page does not itself establish a complete historic
  transaction archive.
- SEBON publications include historical securities-market indicators, trading-day
  counts, turnover and index statistics. These are useful annual/quarterly control
  totals and market-regime evidence, not a replacement for daily OHLCV or contract
  rows. Example: https://www.sebon.gov.np/uploads/uploads/J48M3DD7W3fC6lQQCJcaJA8VEKjTk3F4lVWDTDM2.pdf

## Calendar acquisition strategy

Do not derive the canonical calendar from weekday rules alone. Build a candidate
session set from actual dated observations in:
1. Jaljala EOD archives (source-specific; repeated carry-forward rows are not proof).
2. SocrateAI dated stock/index/floorsheet manifests.
3. Urek floorsheet/index manifests (2024 onward).
4. ShareSansarScraper session manifest (2024 onward).
5. srijankarki07 session archive (2011 onward) as a rights-restricted comparison
   reference only unless separate data rights are obtained.
6. Other independently sourced historical session archives discovered by repository
   search.

For each candidate date, store source-specific evidence, not just a boolean:
`date, source_id, evidence_type, observed_row_count, source_file_sha256,
source_published_at, retrieved_at, exchange_notice_url, status_candidate`.
Mark a session as verified only when the source evidence is adequate and conflicts
are resolved. A date with no observations is not automatically a holiday; it may be
a source gap. A date with repeated OHLCV values is not automatically a carry-forward;
it may be a valid unchanged session.

Use government holiday notices and NEPSE notices to explain closures, but require
dated exchange evidence for exceptional trading openings/closures. Record separate
confidence and verification state; never collapse candidate calendar into verified
calendar without audit trail.

## Immediate acquisition queue

- [ ] Fetch and archive ShareSansarScraper `api/index.json`, `meta.json`,
      `symbols.json`; enumerate all session endpoints.
- [ ] Query Hugging Face dataset manifest and card metadata for Ankit dataset;
      verify license terms and actual Parquet partitions.
- [ ] Extract dated file manifests from SocrateAI, Urek, Samir and Jaljala.
- [ ] Build the union/intersection/difference of all source session sets.
- [ ] Obtain NEPSE/SEBON dated notices and government holiday notices for candidate
      gaps and exceptional sessions.
- [ ] Reconcile EOD daily coverage and annual/quarterly SEBON control totals.
- [ ] Only then classify repeated rows and close the OHLCV gate.

## Evidence consulted during discovery

- ShareSansarScraper archive and about/download pages, inspected 2026-11-24.
- Hugging Face AnkitSanjyal dataset card and project provenance page, inspected
  2026-11-24.
- GitHub srijankarki07/nepse-data README and LICENSE, inspected 2026-11-24.
- GitHub shawinCreates/Nepse-Market-Data README, inspected 2026-11-24.
- NEPSE public floorsheet page, inspected 2026-11-24.
- SEBON quarterly securities-market indicators report, inspected 2026-11-24.

## Acquisition verification update — 2026-11-24 (direct repository inspection)

The following are direct GitHub file reads, not only search snippets:

- ShareSansarScraper `docs/api/meta.json` at blob `f3e3931f7c9024d57ffe98e4f3fef67af47510ca` reports `firstDate=2024-03-04`, `lastUpdated=2026-11-23`, `tradingDays=938`, `symbols=525`, `symbolsLatest=360`, `generatedAt=2026-11-23T22:43:20Z`. This supersedes the older 927-session figure previously found in search indexing. The live GitHub Pages endpoint was not readable through the current browser fetch, but the source repository copy of the JSON manifest and metadata was readable. Actual data files remain to be enumerated and downloaded; no claim of ingestion is made.
- ShareSansarScraper `docs/api/index.json` at blob `77a5275002668382157b7400e63a9fb29ea187ee` confirms per-symbol columnar histories with date, OHLC, LTP, VWAP, volume, turnover and percentage change. Its repository LICENSE is MIT for software; the data is described as ShareSansar-sourced and unofficial, with no separate data license grant stated in the inspected manifest. Treat data reuse rights as unconfirmed pending upstream terms/permission.
- srijankarki07/nepse-data `data/latest.json` at blob `5ef32bef26cf14518e6d08c6a1dc80f794cc53c7` reports latest session `2026-11-24`, previous `2026-11-23`, and 3,627 sessions, with per-year counts from 2011 onward. This is an actual current manifest, materially newer than the README's approximate 3,600 count. Its LICENSE explicitly excludes price data from the MIT software license; do not ingest its data without separate permission. Use its session manifest only as a rights-restricted comparison lead unless rights are clarified.
- shawinCreates/Nepse-Market-Data README describes ShareSansar as its EOD source and documents `Data/csv/closed_days.csv` as closed-day evidence. Its calendar helper says Saturday is the only hardcoded weekly closure and other closures are learned from ShareSansar returning “No Record Found”. The repository LICENSE path was not found. This is a useful implementation and candidate-coverage lead, not an independent source of market prices.
- SamirWagle/Nepse-All-Scraper README documents OHLCV history, dividends, rights issues and daily floorsheet CSV/JSON, with floorsheets sourced from Merolagani.com. It labels its license “Educational”; a root LICENSE file was not found. Data rights and actual date coverage need inspection before ingest.
- SocrateAI repository LICENSE inspected at blob `71968390637c7ea3f70c77e936efd6d6d50ab85f` states MIT for the dataset. Upstream lineage and completeness still need source-level validation; a repository license does not by itself prove upstream rights for every record.

### New high-value floorsheet lead

- NepseSignal public floorsheet page: https://nepsesignal.com/nepse/floorsheet/
- The page claims indexed historical floorsheets back to 2018 and search by business date, symbol and broker, with pagination. It also explains that some totals can differ from NEPSE headline turnover because of segment exclusions and late settlement additions. These are publisher claims; current live page returned no floorsheet rows during inspection, so historic coverage, export/API access, row counts, and terms remain unverified. Investigate documented network endpoints and legal export options; do not scrape around authentication or technical access controls.

### Additional alternative source

- vuwon/NEPSEAPI GitHub search result points to a `merolagani` package that advertises a resumable historical floorsheet scraper from 2016 onward, with SQLite storage and CSV export. This is a code/source lead, not proof that all dates remain accessible or that the upstream site permits bulk extraction. Inspect repository source, terms, pagination behavior and test fixtures before use.

### Status after this pass

No new bulk raw dataset has yet been ingested in this pass. We have verified two additional live manifests and clarified data-rights boundaries for several candidate sources. Next acquisition work should prioritize the Ankit Hugging Face Parquet manifest (potentially the broadest EOD + recent floorsheet bundle), Urek's date/file manifest, and authorized floorsheet access through SocrateAI/Samir/Merolagani/NepseSignal. Do not count a lead as acquired data.