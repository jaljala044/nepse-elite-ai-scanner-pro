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
