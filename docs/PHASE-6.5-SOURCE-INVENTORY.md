# Phase 6.5 — Multi-source NEPSE archive inventory

Inventory date: 2026-11-24
Application repository: `jaljala044/nepse-elite-ai-scanner-pro`

This is a repository-tree inventory and targeted file inspection. It is not a full download, row-level audit or canonical import. File counts are from GitHub recursive trees on the recorded refs.

## 1. Owner-controlled Jaljala repositories

The owner confirmed that the `jaljala044` account and repositories belong to them and authorized NEPSE AI to store and use their repository data.

| Repository | Visibility | Tree revision | Files | Bytes | Finding |
|---|---|---|---:|---:|---|
| `jaljala044/nepse-smc-data` | Public | `737ad091393656de6a8e866673012b6b5fc9bdbb` | 622 | 39,541,608 | Primary owned archive |
| `jaljala044/nepse-history-starter` | Public | `227c2f5e7d6a0b9594b79718afb9a2c0c692492a` | 602 | 35,557,130 | OHLCV helper/archive; overlaps primary |
| `jaljala044/nepse-automation` | Private | `4cb97caa83912cdb56aca4238b10d99cf651c223` | 3 | 4,317 | Daily current-session floorsheet to Google Sheets; no historical files in repository |

### 1.1 Jaljala OHLCV duplication and differences

Both `nepse-smc-data` and `nepse-history-starter` contain exactly 525 files under `03_stock_charts_ohlcv/`, with identical filename sets.

- 500 of 525 corresponding Git blob SHA values are identical.
- 25 files have different blob SHA values; these are the pre-existing ticker histories that the backfill report says were retained and compared against the newer history.
- The NABIL sample has identical blob SHA in both repositories.
- The backfill report says 500 added stock files contain 279,007 bars from 2024-03-04 through 2026-11-20. It reports 8 differing OHLCV rows across 14,856 overlapping rows in 25 pre-existing ticker histories.

**Import rule:** do not ingest both repositories as two independent price sources. Treat the history-starter files as the source revision used for the backfill, retain both commit references, and reconcile the 25 changed files row-by-row. Preserve all source rows and the price-basis ambiguity.

The NABIL sample contains repeated identical OHLCV rows across adjacent calendar dates, including weekend dates. These are not automatically valid exchange sessions. Preserve them in raw storage and quarantine or exclude from session-level features until checked against an authoritative session calendar.

### 1.2 Jaljala market, floorsheet and broker records

The primary repository contains:
- Two daily raw floorsheet files under `floorsheet/`: 2026-11-20 and 2026-11-23 (about 3.86 MB combined).
- Two additional small daily floorsheet files under `02_floorsheet_daily/`: 2026-11-19 and 2026-11-20. Do not assume these are full raw execution archives; compare row counts and schemas.
- 41 dated `scanner_inputs/broker_summary/` CSVs spanning 2026-07-24 and 2026-09-10 through 2026-11-20 (gaps exist). These are broker-by-symbol session aggregates, not full multi-year raw floorsheets.
- Market, benchmark, sector and index-history inputs; corporate-action CSV; audit and reconciliation reports.
- Daily market summary, EOD and scanner packages.

A broker-summary row is a derived aggregate. Retain its aggregation window and provenance. Broker IDs remain execution-channel identifiers, not beneficial-owner identities or proof of institutional intent.

### 1.3 Jaljala automation repository

The private repository contains a scheduled workflow and `fetch_floorsheet.py`. It fetches the current NEPSE floorsheet and writes a date-named Google Sheets tab. It does not maintain a versioned raw historical archive in Git.

**Security issue found:** the current script explicitly disables TLS certificate verification with `nepse.setTLSVerification(False)`. Do not use this collector for production ingestion until TLS verification is restored and the endpoint/certificate issue is resolved safely. Never solve certificate failures by disabling verification. The workflow depends on the `GCP_SERVICE_ACCOUNT_JSON` secret; no secret value was read.

## 2. Additional public sources

### 2.1 SocrateAI NEPSE Open Data — GitHub

Repository: `socrateai-official/nepse-open-data`  
Tree revision: `f602a5b61e68582d28834d16f71151a4bae98d5b`  
License file: MIT; the inspected license expressly applies to the dataset (“Data”) as well as documentation.

| Folder | Files including placeholder | Bytes | Date-stamped files | Path-date range |
|---|---:|---:|---:|---|
| `floorsheet/` | 659 | 3,116,744,322 | 658 | 2024-01-01 to 2026-11-19 |
| `ohlc_unadjusted_stock/` | 4,813 | 25,221,934 | 4,812 | 2007-01-02 to 2026-11-19 |
| `ohlc_adjusted_stock/` | 3,619 | 27,009,684 | 3,618 | 2011-07-15 to 2026-11-19 |
| `ohlc_index/` | 5,366 | 4,532,297 | 5,365 | 2003-07-17 to 2026-11-19 |

Findings:
- Floorsheet file dates begin 2024-01-01, which must be checked as a likely non-session/exception before acceptance.
- The latest published floorsheet and OHLC/index path date observed is 2026-11-19.
- The sample unadjusted stock file contains all symbols in a daily file with columns `date,close,open,high,low,volume,symbol`.
- The sampled adjusted and unadjusted OHLC files for 2026-11-19 had identical blob SHA. Do not assume adjusted values are distinct or validly adjusted until a full corporate-action reconciliation is done.
- The sample index file is named `adj_2026-11-19.csv` and contains timestamped index OHLC rows. Its timestamp/timezone semantics need validation.
- The large floorsheet CSV files were inventoried but not fully fetched into this runtime.

**Use:** primary candidate to supplement daily unadjusted OHLC/index coverage from 2007 onward and floorsheet sessions absent from Urek/Jaljala. It is not yet approved as canonical until all files are downloaded, audited and reconciled.

### 2.2 Urekmazino69 NEPSE Floorsheet and Indices — Hugging Face

Dataset: `urekmazino69/Nepse-floorsheet-and-indices`  
The project source register records MIT licensing and an inventory of 603 daily floorsheet files (2024-01-02 to 2026-08-26) plus 6,429 index files (1997-07-20 to 2026-08-26), about 728.024 MiB compressed.

**Use:** principal candidate historical transaction-level floorsheet segment through 2026-08-26 and long index history. A one-session smoke test has passed, but the complete archive has not yet been downloaded and audited. Do not infer full coverage from the file inventory alone.

### 2.3 AnkitSanjyal NEPSE Market Data — Hugging Face

Dataset: `AnkitSanjyal/nepse-market-data`  
Dataset card currently reports license `other`. Existing project inspection recorded 306 Parquet files and 1,139,853 rows across EOD, floorsheet, broker-flow, 1-minute bars and daily-stat tables.

Known caveats already recorded in `PIPELINE_STATUS_2026-11-23.md`:
- Recent floorsheet/broker-flow coverage is not continuous; 2026-08-26 through 2026-11-18 is a documented gap.
- The extended EOD table has substantial OHLC anomalies and 14 close mismatches in overlap with the recent EOD table.
- The recent EOD and extended-history tables must remain separate.
- Broker flow is derived data, not raw beneficial-owner activity.

**Use:** comparison and research staging only until dataset rights and all QA exceptions are resolved. Do not publish or redistribute the data based only on the `other` label.

### 2.4 SamirWagle NEPSE All Scraper — GitHub

Repository: `SamirWagle/Nepse-All-Scraper`  
Tree revision: `144cecb36f110bedb741f5d147c7857cdb24c958`

- 1,631 files, about 839.6 MB total.
- 365 per-company price files.
- 179 dated floorsheet files, 2026-02-22 through 2026-11-24.
- Per-company dividend/right-share files and company mapping.
- Public API and flat-file outputs are described by the project as educational use; no unambiguous general commercial data license was verified.

**Use:** recent independent floorsheet cross-check and corporate-action discovery after rights review. Keep separate from canonical data. The repository's own README says full OHLC history is produced by a local first-time scrape and the daily workflow updates floorsheets/dividends/right shares. Do not assume all price histories are current or complete.

### 2.5 srijankarki07 NEPSE Data — GitHub

Repository: `srijankarki07/nepse-data`  
The code license is MIT, but its LICENSE explicitly states that the price data is not covered by that license and is redistributed from ShareSansar/NEPSE. Do not copy or redistribute its price data without separate permission. Its 2011-to-present daily EOD archive is a possible coverage reference only, not an approved data source.

## 3. Coverage strategy and source precedence

| Data family | Primary candidate | Supplement/cross-check | Do not do |
|---|---|---|---|
| Daily unadjusted stock OHLCV | Jaljala 500-file history (2024+) plus Socrate unadjusted daily files (2007+) | Ankit extended EOD (1995+) only after QA/rights; Samir only for comparison | Merge sources by date without conflict ledger |
| Adjusted OHLCV | Separate Socrate adjusted dataset after corporate-action validation | Ankit source if rights and schema pass | Assume adjusted/unadjusted files differ because of folder names |
| Floorsheet raw trades | Urek daily archive through 2026-08-26 | Socrate files to fill gaps and extend to 2026-11-19; Samir recent archive; Jaljala raw sessions | Treat broker summaries as raw trades or invent missing execution times |
| Latest daily floorsheet | Owner's authorized NEPSE collector after TLS is fixed and capture is audited | Samir/Socrate/Jaljala same-day cross-check | Disable TLS verification or trust a filename as proof of session date |
| Sector/index history | Urek index archive; Socrate index daily files | Jaljala index-history CSVs | Mix index definitions or adjusted/unadjusted series |
| Broker flow | Jaljala broker summaries and Ankit derived flow as separate sources | Recompute from raw floorsheets where possible | Infer beneficial owners, intent or manipulation from broker codes |
| Corporate actions | Jaljala corporate-action inputs and Samir company-wise dividend/right-share files after rights review | Provider/exchange evidence | Use unverified actions to adjust historical prices |

The earliest known EOD extension candidate is Ankit 1995-07-20, but it currently has material quality exceptions and unresolved data rights. Socrate unadjusted daily OHLC starts 2007-01-02. Jaljala's added backfill starts 2024-03-04.

## 4. Required acquisition and validation sequence

1. Pin immutable commit/revision IDs and create a per-file SHA-256 manifest for every source batch.
2. Download the complete Jaljala primary archive once. Use Git blob IDs to avoid downloading the 500 identical OHLCV files from the history-starter repository twice; separately fetch and reconcile the 25 differing files.
3. Acquire Urek's full floorsheet/index archive to private staging; preserve its published LFS SHA-256 and source revision.
4. Acquire Socrate unadjusted OHLC and index history, plus only floorsheet sessions that are missing from Urek or needed for independent reconciliation. Keep adjusted OHLC separate.
5. Acquire Samir recent floorsheets and corporate-action files only after confirming the applicable data-use terms. Keep its OHLCV as comparison until completeness and rights are established.
6. Keep Ankit Parquet files in a restricted comparison area until the `other` license is clarified and flagged EOD anomalies are reviewed.
7. Generate date/symbol/session coverage matrices and per-session row counts; compare trade keys and arithmetic across overlapping floorsheets.
8. Reconcile OHLC values and corporate actions by symbol/date; never overwrite conflicting rows.
9. Preserve raw data, null execution times, source timezones, publication/retrieval timestamps and parser versions.
10. Promote only accepted rows to canonical silver after independent QA and point-in-time/no-lookahead tests.

## 5. Storage and current execution status

The inspected Socrate repository alone contains about 3.12 GB of floorsheet CSV data. The complete Urek archive is about 728 MiB compressed. The combined raw archive is too large and too mutable for the application Git repository.

Keep raw data in a private data volume/object store or owner-controlled private archive. Git stores source code, source manifests, schemas, small fixtures and QA reports only. A persistent external storage destination has not yet been configured for this project.

**This inventory did not download the complete external archives, import any records into the database, or run a full-history row audit.** It establishes which data is available and what must be acquired next. Do not label the historical database complete until those steps have passed.
