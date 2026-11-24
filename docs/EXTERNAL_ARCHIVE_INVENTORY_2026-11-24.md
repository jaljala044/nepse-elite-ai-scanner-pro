# External and owner-controlled archive inventory — 2026-11-24

This report records a metadata-only GitHub inventory and targeted sample inspection. It is not a claim that the complete archives have been downloaded, parsed, reconciled or imported into a database.

## Pinned repository snapshots

| Repository | Commit SHA | Files | Bytes | Notes |
|---|---|---:|---:|---|
| `jaljala044/nepse-smc-data` | `737ad091393656de6a8e866673012b6b5fc9bdbb` (tree) | 622 | 39,541,608 | 525 per-symbol OHLCV files; floorsheet and broker summary archive |
| `jaljala044/nepse-history-starter` | `227c2f5e7d6a0b9594b79718afb9a2c0c692492a` (tree) | 602 | 35,557,130 | Same 525 OHLCV path set as SMC repo |
| `jaljala044/nepse-automation` | `4cb97caa83912cdb56aca4238b10d99cf651c223` (tree) | 3 | 4,317 | Private automation scripts/workflows; not a historical archive |
| `socrateai-official/nepse-open-data` | `f602a5b61e68582d28834d16f71151a4bae98d5b` (tree) | 14,460 | 3,173,510,750 | Large MIT-licensed data archive |
| `SamirWagle/Nepse-All-Scraper` | `144cecb36f110bedb741f5d147c7857cdb24c958` (tree) | 1,631 | 839,582,556 | 365 company price files, 179 dated floorsheet files and other outputs |
| `srijankarki07/nepse-data` | `b8c34710c48a23efa9d0088c58781ab02a760c73` (tree) | 4,623 | 70,517,420 | 2011+ EOD archive; data is explicitly excluded from the software MIT license |

Tree SHAs are recorded above, not commit SHAs. The inventory tool records both commit SHA and tree SHA on each future run.

## Jaljala repositories

### `nepse-smc-data`

Observed file groups:
- `03_stock_charts_ohlcv/`: 525 ticker CSVs, 14.01 MB.
- Daily EOD and reference files: six files, 311 KB.
- Floorsheet-related files: raw daily folders include 2026-11-20 and 2026-11-23; additional report/summary/reconciliation files exist.
- `scanner_inputs/broker_summary/`: 41 dated daily broker-summary files, plus audit/reconciliation and market/index inputs.
- Corporate-action inputs include dividend/right-share files and `scanner_inputs/corporate_actions.csv`.

Backfill report claims 500 stock histories / 279,007 bars from 2024-03-04 to 2026-11-20. Treat these as repository-publisher counts pending a fresh row-level audit.

### `nepse-history-starter`

Contains the same 525 ticker OHLCV filenames. All 525 filenames exist in both repositories; 500 blob SHAs are identical and 25 differ. The differing files are the previously reported overlapping histories and must remain source-distinct until row-level reconciliation. Do not import both copies as independent market observations.

### `nepse-automation`

Contains only a floorsheet-fetch script and two workflow files. It calls an unofficial `nepse.AsyncNepse` client for the current floorsheet and writes to Google Sheets. The workflow uses a scheduled GitHub Action and Google service-account secret. It is not a historical backfill archive.

Security finding: the script disables TLS verification. This is not acceptable for a production data collector. Before reuse, remove TLS bypass, validate certificates, pin dependency versions, make timezone explicit, derive the actual exchange session date from verified response metadata, and store immutable raw responses before exporting to Sheets. The scheduled cron and actual GitHub run history must be reviewed before relying on its output.

### Sample anomaly

The Jaljala NABIL sample has repeated identical OHLCV rows on consecutive calendar dates, including dates that appear to be carry-forward values rather than separate sessions. This is a high-priority quarantine rule. Never treat file-row dates as verified sessions without a dated exchange calendar and source-level confirmation.

## Additional sources and selection decision

### SocrateAI NEPSE Open Data

- MIT data license is present in repository root; retain the notice and attribution with any copy.
- 658 dated floorsheet files, 2024-01-01 through 2026-11-19, about 3.117 GB.
- 4,812 unadjusted stock daily files, 2007-01-02 through 2026-11-19, about 25.2 MB.
- 3,618 adjusted stock daily files, 2011-07-15 through 2026-11-19, about 27.0 MB.
- 5,365 index files, 2003-07-17 through 2026-11-19, about 4.53 MB.

The floorsheet archive is large. Download it selectively by date after comparing its session list with Urek/Jaljala/Samir, rather than mirroring all 3.1 GB. The stock EOD and index files are relatively compact and useful as a second source, but adjusted and unadjusted series must stay separate.

A sample 2026-11-19 unadjusted stock file contains date, close, open, high, low, volume and symbol. Sample index files include sector names and index OHLCV-like fields. A sample floorsheet file was confirmed in the tree; its full CSV body was not fetched by the GitHub text tool.

### SamirWagle NEPSE All Scraper

- 179 dated floorsheet files, 2026-02-22 through 2026-11-24, about 734.7 MB.
- 365 company-wise `prices.csv` files.
- Current sample NABIL price file uses `date,open,high,low,ltp,percent_change,qty,turnover`; map `ltp` to a source-specific close candidate only after validation and do not fabricate an adjusted close.
- Its current floorsheet snapshots are useful for coverage comparison and cross-checking recent sessions, but do not assume every file is complete or source-authoritative. The README labels the project/data for educational use and describes upstream sources as ShareSansar and Merolagani; no standalone data license file was found in the inspected repository. Keep Samir data as a validation/cross-check source only until the owner and upstream terms clearly permit NEPSE AI's intended storage, processing and deployment use.

### Hugging Face: Urekmazino69/Nepse-floorsheet-and-indices

- Publisher describes daily floorsheet and index coverage from 2024-01-02 through 2026-08-26.
- Prior measured inventory: 603 floorsheet files / 723.767 MiB and 6,429 index files / 4.257 MiB.
- MIT license declared by dataset publisher.
- Sample schema includes contract number, calculation date, time (often null), symbol, sector, buyer/seller broker codes, quantity, rate and amount.

Use this as the first bulk historical floorsheet candidate for its declared period; verify every file and calendar date. Use SocrateAI and Samir as complementary coverage and reconciliation sources.

### Hugging Face: AnkitSanjyal/nepse-market-data

- 306 Parquet files, approximately 29.3 MB, publisher declares license `other`.
- Previously inspected warehouse has EOD, floorsheet, broker-flow, 1-minute bars and daily stats. Recent floorsheet coverage has a major gap from 2026-08-26 through 2026-11-18.
- Extended EOD table has material OHLC anomalies and 14 close mismatches against recent EOD source; keep tables separate.
- Broker flow is derived aggregation, not raw exchange order flow.

Use for cross-checking and derived feature research only after terms review and source reconciliation. Do not redistribute until the license/terms are clarified.

### GitHub NEPSE Open Data: `srijankarki07/nepse-data`

- Repository README claims 3,600 sessions from 2011 onward and a daily EOD archive.
- Crucial: the LICENSE explicitly states that its MIT license covers software only, not the data, which is republished from ShareSansar. Do not copy its data into NEPSE AI or redistribute it based on the code license. Use the repository documentation to understand provenance and compare only if data-use rights are independently obtained. The README's claim of 3,626 sessions and latest date 2026-11-23 is a publisher-maintained status record, not permission to copy the archive.

## Collection priorities

1. **Jaljala OHLCV** — preserve one source copy per ticker/date and reconcile the 25 differing files; quarantine repeated carry-forward bars.
2. **SocrateAI unadjusted stock EOD** — use as an independent EOD source (2007 onward), retaining file SHA and session provenance. Adjusted EOD is a separate dataset, not a replacement.
3. **Index history** — Jaljala index files + SocrateAI index archive + Urek index CSVs, source-separated.
4. **Floorsheet 2024–2026** — Urek as primary bulk candidate; use SocrateAI files only for dates missing or conflicting after exact session-set comparison; use Samir/Jaljala latest files as independent cross-checks. Avoid downloading all 3.1 GB if only a subset is missing.
5. **Broker summaries** — Jaljala 41 daily summaries are a valuable separate derived dataset; verify input coverage and aggregation formula. Ankit broker flow is a separate derived source. Never merge broker summary with trade-level floorsheet.
6. **Corporate actions** — retain Jaljala dividends/rights/corporate action inputs; cross-check against a separately sourced corporate-action register before adjusting historical candles.
7. **Private automation repo** — use as workflow reference only. No historical data currently stored there.

## Current completion status

- [x] Repository metadata and recursive trees inspected.
- [x] Exact Jaljala OHLCV path overlap measured.
- [x] Selected source schemas sampled.
- [x] SocrateAI data license inspected.
- [x] ShareSansar-derived NEPSE Open Data data-rights restriction identified.
- [ ] Full data-file download.
- [ ] Full row-level audit and date-set reconciliation.
- [ ] Canonical database import.
- [ ] Corporate-action-aware EOD acceptance.
- [ ] Verified session calendar.
- [ ] Point-in-time availability metadata for each dataset.
