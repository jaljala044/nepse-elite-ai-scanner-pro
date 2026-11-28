# NEPSE data-source register and collection plan

Updated: 2026-11-23. This register separates observed public interfaces from feeds that
need a provider account, a licence, or an exact endpoint supplied by the provider.

## Collection tiers

| Source | Data/use | Access status | Collector status |
|---|---|---|---|
| OmitNomis ShareSansarScraper | Historical daily OHLCV archive, latest session, symbols | Public JSON archive; unofficial ShareSansar-derived data | Verified JSON snapshot endpoints implemented |
| Kaggle: qramkrishna/nepal-stock-exchange-data | Historical trade-level floorsheet, per-company CSVs | Public Kaggle dataset; description says data through 2019-10-10, 218 companies, noncommercial/educational use | Identified; local Kaggle-authenticated staging helper added; date field/schema validation required |
| Hugging Face: urekmazino69/Nepse-floorsheet-and-indices | Daily trade-level floorsheet and sector indices | Public dataset; floorsheets 2024-01-02 to 2026-08-26; index files 1997-07-20 to 2026-08-26; MIT | Inventory measured 7,032 files / 728.024 MiB; gzip download, normalization and sample audit passed |
| Hugging Face: AnkitSanjyal/nepse-market-data | Long daily OHLCV history, recent floorsheet, minute bars and derived broker flow | Public Parquet dataset; 306 files / ~29.3 MB; 1,139,853 rows across six tables | All files downloaded and inspected; source-separated DuckDB warehouse built in CI; quality report available; EOD history needs review |
| SamirWagle/Nepse-All-Scraper | Daily floorsheet CSV/JSON, sector-index CSVs, company list | Public GitHub Pages API and flat files; current repository snapshot may be behind current session | Collector configured; inspect last available session before relying on it |
| jaljala044/nepse-history-starter | User-maintained OHLCV imports and source records | Public GitHub repository at inspection time | GitHub raw-file collector implemented |
| jaljala044/nepse-smc-data | EOD prices, market indices, daily floorsheet, OHLCV charts and scanner packages | Public GitHub repository at inspection time | GitHub raw-file collector implemented |
| nepsepy / nepse-client / nepse-data-api | Market, prices, floorsheets, indices, history, company data | Unofficial clients/APIs; availability and exact endpoints vary by project | Configurable provider endpoint only; no guessed API paths |
| Chukul | Broker desk and broker-flow analytics based on floorsheet | No public developer API contract verified | Requires provider-authorized API/export or manual file import |
| ShareHub | Market, sector indices, historical charts, raw floorsheet and broker analytics | User-identified API; endpoint, licensing and auth terms still need provider confirmation | Endpoint/token configuration supported; requires provider-issued docs and authorization |
| Hamro Share | App advertises prices, floorsheet, charts and broker analysis | No public developer API contract verified | Requires provider-authorized API/export or manual file import |
| NEPSE Alpha | Public market page displays market/floorsheet information | No stable public developer API contract verified | Manual exports or provider-authorized endpoint only |
| nepse.link MCP | Pre-computed broker-flow summaries | User-identified MCP service; API schema, lag and coverage not independently verified | Configurable provider endpoint only after validating schema and terms |

## Run the collectors and normalizer

### Inventory and bounded Hugging Face downloads

Run these commands from `backend/` after `pip install -r requirements.txt`:

```bash
# Inventory both public datasets without downloading data
python collect_hf_datasets.py

# Download a small 50 MiB test sample
python collect_hf_datasets.py --dataset floorsheet_indices_2024 --download --max-total-mb 50

# Download the full observed Urek archive (inventory size ~728 MiB compressed)
# Re-running is safe: completed files are skipped only when size + LFS SHA-256 match.
python collect_hf_datasets.py --dataset floorsheet_indices_2024 --download \
  --max-total-mb 800 --max-file-mb 20 --max-files 10000

# Download selected daily sessions only (path-based date filter)
python collect_hf_datasets.py --dataset floorsheet_indices_2024 --download \
  --from-date 2026-08-01 --to-date 2026-08-26 --max-total-mb 50

# Inventory Ankit's Parquet data without downloading the full archive
python collect_hf_datasets.py --dataset market_data_2026
```

Downloads are byte-limited and stored under `data/raw/huggingface/`; they are not committed
to GitHub. Date filtering applies to date-stamped file paths, not rows inside an unpartitioned
Parquet file. Ankit Parquet schemas, row counts, null counts and date ranges have been inspected,
and the current six-table DuckDB warehouse is source-separated. See the measured QA results below.

### Normalize downloaded daily floorsheets and indices

```bash
python normalize_floorsheet_csv.py ../data/raw/huggingface/urekmazino69__Nepse-floorsheet-and-indices/main/floorsheet \
  --source urekmazino69/Nepse-floorsheet-and-indices

python normalize_indices_csv.py ../data/raw/huggingface/urekmazino69__Nepse-floorsheet-and-indices/main/indices \
  --source urekmazino69/Nepse-floorsheet-and-indices

python audit_silver_floorsheet.py
python audit_silver_indices.py
```

The normalizers support `.csv` and `.csv.gz`, writing separate deduplicated daily partitions
under `data/silver/floorsheet/date=YYYY-MM-DD/` and `data/silver/indices/date=YYYY-MM-DD/`.
Rows with invalid dates, missing trade keys, invalid OHLC values or inconsistent trade arithmetic
are quarantined under `data/quarantine/`. A source file is rejected if more than 10% of its rows
fail validation. Already-downloaded files are only treated as complete when both byte size and
the Hugging Face LFS SHA-256 match; otherwise the collector re-downloads them.

### Download the identified Kaggle archive

Install and configure the Kaggle CLI locally using your own Kaggle account first. Do not add
Kaggle credentials to this repository.

```bash
python ingest_kaggle_floorsheet.py --confirm-download
```

The script checks archive/member sizes, rejects unsafe ZIP paths, extracts only CSV/JSON/TXT
files into `data/raw/kaggle/`, and writes a SHA-256/schema inspection manifest. It stages
raw files only; it does not assume the old Kaggle schema or merge those files into silver.


From the backend folder after installing requirements:

```bash
python collect_sources.py
```

Choose sources:

```bash
python collect_sources.py --source sharesansar_archive --source samirwagle_archive
python collect_sources.py --source jaljala_history_starter --source jaljala_smc_data
python collect_sources.py --source samirwagle_archive
```

For a provider-authorized endpoint, configure its exact URL and optional bearer token in
the deployment environment (never commit secrets):

- `CHUKUL_DATA_URL`, optional `CHUKUL_API_TOKEN`
- `SHAREHUB_DATA_URL`, optional `SHAREHUB_API_TOKEN`
- `HAMROSHARE_DATA_URL`, optional `HAMROSHARE_API_TOKEN`
- `NEPSEALPHA_DATA_URL`, optional `NEPSEALPHA_API_TOKEN`
- `NEPSEPY_DATA_URL`, optional `NEPSEPY_API_TOKEN`
- `NEPSE_CLIENT_DATA_URL`, optional `NEPSE_CLIENT_API_TOKEN`
- `NEPSE_DATA_API_DATA_URL`, optional `NEPSE_DATA_API_API_TOKEN`
- `NEPSE_LINK_DATA_URL`, optional `NEPSE_LINK_API_TOKEN`

The collector deliberately does not guess private app endpoints or bypass authentication.
For any paid or private provider, obtain the current API specification, permission to store
the returned data, authentication method and rate limits directly from that provider before
configuring the endpoint. Never commit API tokens to Git.

## Data integrity rules

1. Store raw responses unchanged with retrieval time, source URL, content type and SHA-256.
2. Do not merge raw files directly into canonical price/floorsheet tables.
3. Parse each schema separately; record source session date separately from retrieval time.
4. Check symbol/date duplicates, OHLC bounds, volume, timezone, missing sessions and stale data.
5. Cross-check ShareSansar-derived figures against NEPSE-origin records where available.
6. Treat floorsheet buyer/seller broker codes as execution channels, not beneficial-owner identity.
7. Broker-flow summaries are derived measures; keep their source and aggregation window visible.
8. Do not use adjusted prices as raw prices. Corporate actions need their own adjustment ledger.
9. Do not enable automated collection schedules until permissions, rate limits, coverage and
   reconciliation tests are complete.

### Build and query the Ankit DuckDB warehouse

After downloading the Ankit Parquet files with `collect_hf_datasets.py`:

```bash
python inspect_parquet_datasets.py \
  --input ../data/raw/huggingface/AnkitSanjyal__nepse-market-data/main \
  --output ../data/reports/ankit-parquet-inspection.json

python load_ankit_warehouse.py \
  --input ../data/raw/huggingface/AnkitSanjyal__nepse-market-data/main \
  --database ../data/warehouse/nepse-analytics.duckdb \
  --report ../data/reports/ankit-warehouse-load.json
```

Tables are created in DuckDB under schema `ankit`: `floorsheet`, `eod_price`,
`eod_history_ext`, `broker_flow_daily`, `bars_1m`, and `daily_stats`.
The raw files, report and DuckDB are excluded from Git by `.gitignore` and should be
stored in a private data volume or backed-up object store rather than in source control.

## Historical coverage finding (2026-11-23)

The Kaggle dataset currently identified is
[`qramkrishna/nepal-stock-exchange-data`](https://www.kaggle.com/datasets/qramkrishna/nepal-stock-exchange-data).
Its dataset description states that it contains historical NEPSE floorsheet transactions
through 2019-10-10, split into one CSV for each of 218 companies. The published field list
includes contract number, stock symbol, buyer/seller broker, quantity, rate and amount, but
does not list a separate trade-date column. It does **not** establish coverage through 2026,
and the listing does not establish a reliable 2014 start date. It is a legacy historical segment,
not a complete continuous 2014–2026 archive. The trade date must not be inferred from the
contract number until its encoding is independently verified against known records.

A newer public non-Kaggle alternative is
[`urekmazino69/Nepse-floorsheet-and-indices`](https://huggingface.co/datasets/urekmazino69/Nepse-floorsheet-and-indices).
Its published data card says daily floorsheet and indices cover 2024-01-02 through 2026-08-26.
The dataset exposes trade-level contract number, date, symbol, buyer/seller broker codes,
quantity, rate and amount. Its visible schema has 11 fields: contract_no, calculation_date,
time, stock_symbol, sector, buyer, seller, quantity, rate, amount and id. The publisher notes
that corporate actions are not adjusted. The repository collector and normalizer support
this schema while preserving broker codes as execution-channel IDs.

#### Measured repository inventory (2026-11-23)

A GitHub Actions inventory traversed the public dataset tree without bulk-downloading it:

| Folder | Files | Compressed size | Path-date range |
|---|---:|---:|---|
| `floorsheet/` | 603 | 723.767 MiB | 2024-01-02 to 2026-08-26 |
| `indices/` | 6,429 | 4.257 MiB | 1997-07-20 to 2026-08-26 |
| **Total** | **7,032** | **728.024 MiB** | 1997-07-20 to 2026-08-26 |

These are file-tree counts and dates, not a claim that all dates are valid NEPSE trading
sessions or that every file is complete. Index path dates extend earlier than the floorsheet
date range. Large calendar gaps are flagged for a trading-calendar-aware review, not
automatically classified as missing exchange sessions.

#### One-session end-to-end validation

The project downloaded and normalized the 2024-01-02 floorsheet and sector-index files
in a GitHub Actions smoke run:

- Floorsheet: 85,435 rows accepted, 0 rejected; 11,185,712 shares; reported turnover
  NPR 4,044,659,922.73; no duplicate `(trade_date, contract_no)` keys, date mismatches
  or quantity × price arithmetic errors under the configured NPR 1 tolerance.
- Sector indices: 16 rows accepted; no duplicate `(index_date, sector)` keys,
  date mismatches or OHLC range errors.

This validates only one session and the parser path. It is not validation of the other 602
floorsheet files, all 6,429 index files, or full dataset completeness.


#### Ankit Parquet inventory and warehouse QA (2026-11-23)

All **306 Parquet files** from `AnkitSanjyal/nepse-market-data` were downloaded to a
GitHub Actions workspace, read successfully, and loaded into the DuckDB schema `ankit`.
The workflow produced a DuckDB warehouse and JSON report. The six tables remain separate:

| Table | Rows | Files | Date range |
|---|---:|---:|---|
| `eod_history_ext` | 516,620 | 1 | 1995-07-20 to 2026-08-19 |
| `eod_price` | 93,859 | 277 | 2025-08-19 to 2026-11-20 |
| `floorsheet` | 330,978 | 7 | 2026-08-19 to 2026-11-20 |
| `broker_flow_daily` | 81,418 | 7 | 2026-08-19 to 2026-11-20 |
| `bars_1m` | 114,537 | 7 | 2026-08-19 to 2026-11-20 |
| `daily_stats` | 2,441 | 7 | 2026-08-19 to 2026-11-20 |
| **Total** | **1,139,853** | **306** | Mixed by source table |

Data-quality results:

- Floorsheet: 330,978 rows; zero duplicate trade keys; zero invalid trade values;
  zero quantity × rate mismatches greater than NPR 1; 399 symbols.
- Broker-flow summary: 81,418 rows; zero duplicate symbol/broker/date keys;
  every `net_qty` equals `buy_qty - sell_qty`; all net-value arithmetic agrees within NPR 1.
- One-minute bars: 114,537 rows; zero duplicate bar keys and zero OHLC range violations.
- Daily statistics: 2,441 rows; zero duplicate symbol/date keys and no negative volume,
  turnover or trade counts.
- Recent `eod_price`: 93,859 rows; zero duplicate symbol/date keys; 578 records have a
  close outside the reported high/low range. All 578 carry the source flag
  `close_outside_range`; none are unflagged. They are preserved and flagged for review.
- Extended `eod_history_ext`: 516,620 rows; zero duplicate symbol/date keys; 40,373 rows
  have OHLC range anomalies. The detailed audit counts 39,380 open-outside-range cases,
  1,067 close-outside-range cases and 130 nonpositive-price cases (categories may overlap).
  This source has no corresponding quality-flag field. Do not use its raw OHLC candles for
  pattern analysis until these historical anomalies and corporate actions are reviewed.

EOD overlap comparison between `eod_history_ext` and `eod_price`:

- 75,671 matched symbol/date records from 2025-08-19 to 2026-08-19.
- Exact traded-volume match on all 75,671 records.
- Exact close match on 75,657 records; 14 close mismatches remain (99.98% of matched
  records agree exactly, while all 75,671 traded-volume values agree exactly).
- The maximum absolute close difference is NPR 60. The largest mismatches include
  ULBSL on 2026-03-01 (3,118 vs 3,178), ICFCD83 on 2026-07-17
  (1,154 vs 1,211.7), and NCCD86 on 2026-07-07 (1,180 vs 1,144.6).
  The corresponding traded quantities match exactly in all 14 mismatches. Their cause
  has not been established; all 14 are listed in the machine-readable report. Keep the
  two source tables distinct.

The warehouse loader preserves all source rows, reports EOD OHLC anomalies rather than
silently adjusting or dropping them, and blocks only duplicate business keys, invalid
trade values and floorsheet arithmetic failures. Broker codes are still execution-channel
identifiers, not evidence of beneficial-owner identity or intent.

The full Ankit dataset and generated DuckDB warehouse are available in the conversation's
downloadable archive. The GitHub Actions copy is temporary (14-day artifact retention);
it has not been committed to the source repository or deployed to a persistent server.

Another public dataset,
[`AnkitSanjyal/nepse-market-data`](https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data),
shows 306 Parquet files totaling 29.3 MB in the repository file inventory (the dataset card
reports approximately 1.14M rows). Its card states that extended daily
price history begins 1995-07-20, while its trade-level floorsheet begins 2026-08-19 and has
a gap from 2026-08-26 through 2026-11-18. The repository inventory contains 277 `eod_price` daily Parquet files from 2025-08-19
through 2026-11-20, one `eod_history_ext` Parquet file (10.34 MiB), and 7 recent partitions
each for `floorsheet`, `broker_flow_daily`, `bars_1m`, and `daily_stats`. No files were
returned from the declared `index_intraday` folder in this inventory. The recent floorsheet
partitions have path dates 2026-08-19, 20, 21, 24, 25 and 2026-11-19, 20. The publisher
documents the absent 46-session interval 2026-08-26 through 2026-11-18. This is useful for
recent cross-checking and extended EOD history, but does not bridge the full older floorsheet
history. These file counts have since been verified against row-level Parquet schemas and actual DuckDB table loads; see the Ankit QA section above.

Therefore the currently verified public evidence does not support a single continuous
Kaggle floorsheet archive for 2014–2026. Build the canonical floorsheet database as
source-specific segments, then explicitly report uncovered dates rather than filling gaps
with fabricated or interpolated trades.

### Kaggle download note

The Kaggle dataset can be downloaded from its dataset page after accepting any applicable
Kaggle terms. The Kaggle CLI requires the user's Kaggle authentication configured locally;
do not upload the Kaggle token into this repository or paste it into chat. After download,
place the archive in a local staging folder, inspect its CSV schema, record the source version
and SHA-256, and import it through a dedicated validator. No Kaggle data archive has yet
been copied into this private repository.

## Known source caveats

- ShareSansarScraper explicitly describes itself as an unofficial archive sourced from ShareSansar.
- SamirWagle's project says its daily scraper stores flat files and runs after market close.
- Provider-specific endpoints and permissions for ShareHub, Chukul, Hamro Share, NEPSE Alpha
  and nepse.link still need direct confirmation before integration.
- Unofficial clients and scraped archives can break, lag, or change schema without notice.
- A broker represents many clients, so broker-level flow cannot identify the underlying investor.


## Shared validation registry integration

The main scanner's floorsheet normalizer accepts an optional `--validation-registry`
argument. The package is published from `jaljala044/nepse-smc-data` and is pinned in
CI to the tested source commit
`122acaae8665fd396d206ea40b66861b9cbd4d6b`.

Install it in the scanner environment:

```bash
python -m pip install "git+https://github.com/jaljala044/nepse-smc-data.git@122acaae8665fd396d206ea40b66861b9cbd4d6b"
```

Then run normalization with a shared, durable registry path:

```bash
python normalize_floorsheet_csv.py <input-file-or-directory> \
  --source <source-name> \
  --validation-registry /shared/nepse/validation/registry.sqlite3
```

The registry reuses deterministic parsing results only when the file SHA-256, source/schema
context and validator version match. The normalizer still performs the existing silver
upsert/conflict checks and preserves source metadata. A cache hit does not establish source
authorization, archive completeness, trading-session coverage, cross-source agreement or
canonical promotion.

A common SQLite path is required for actual cross-repository reuse. Separate hosted CI
runners do not share local files automatically. Do not treat per-runner databases or
evictable CI caches as a central evidence store. Production-wide reuse remains pending a
durable shared filesystem or registry service with backup, access control and concurrency
management.
