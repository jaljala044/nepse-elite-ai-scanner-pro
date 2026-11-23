# NEPSE data-source register and collection plan

Updated: 2026-11-23. This register separates observed public interfaces from feeds that
need a provider account, a licence, or an exact endpoint supplied by the provider.

## Collection tiers

| Source | Data/use | Access status | Collector status |
|---|---|---|---|
| OmitNomis ShareSansarScraper | Historical daily OHLCV archive, latest session, symbols | Public JSON archive; unofficial ShareSansar-derived data | Verified JSON snapshot endpoints implemented |
| Kaggle: qramkrishna/nepal-stock-exchange-data | Historical trade-level floorsheet, per-company CSVs | Public Kaggle dataset; description says data through 2019-10-10 and 218 companies | Identified; manual/Kaggle-authenticated download and schema validation still required |
| Hugging Face: urekmazino69/Nepse-floorsheet-and-indices | Daily trade-level floorsheet and sector indices | Public dataset; stated coverage 2024-01-02 to 2026-08-26; MIT; 11 published columns | Bounded downloader and CSV-to-silver normalizer implemented |
| Hugging Face: AnkitSanjyal/nepse-market-data | Long daily OHLCV history plus newer floorsheet and derived data | Public Parquet dataset, 1.14M rows / 29.3 MB at inspection; EOD history stated 1995-07-20 to present; floorsheet from 2026-08-19 with gap 2026-08-26 to 2026-11-18 | Bounded Parquet file inventory/download implemented; per-table schema validation still required |
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

# Download up to 50 MiB of the older daily CSV floorsheet and indices
python collect_hf_datasets.py --dataset floorsheet_indices_2024 --download --max-total-mb 50

# Download selected daily sessions only (path-based date filter)
python collect_hf_datasets.py --dataset floorsheet_indices_2024 --download \
  --from-date 2026-08-01 --to-date 2026-08-26 --max-total-mb 50

# Inventory Ankit's Parquet data without downloading the full archive
python collect_hf_datasets.py --dataset market_data_2026
```

Downloads are byte-limited and stored under `data/raw/huggingface/`; they are not committed
to GitHub. Date filtering applies to date-stamped file paths, not rows inside an unpartitioned
Parquet file. Parquet schema validation is still a separate step.

### Normalize downloaded daily floorsheet CSVs

```bash
python normalize_floorsheet_csv.py ../data/raw/huggingface/urekmazino69__Nepse-floorsheet-and-indices/main/floorsheet \
  --source urekmazino69/Nepse-floorsheet-and-indices
```

The normalizer writes deduplicated daily CSV partitions under `data/silver/floorsheet/date=YYYY-MM-DD/`.
Rows with invalid dates, missing trade keys or inconsistent arithmetic are quarantined under
`data/quarantine/`. A file is rejected if more than 10% of its rows fail validation.

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

## Historical coverage finding (2026-11-23)

The Kaggle dataset currently identified is
[`qramkrishna/nepal-stock-exchange-data`](https://www.kaggle.com/datasets/qramkrishna/nepal-stock-exchange-data).
Its dataset description states that it contains historical NEPSE floorsheet transactions up to
2019-10-10, split into one CSV per each of 218 companies. It does **not** establish coverage
through 2026, and the listing does not establish a reliable 2014 start date. It is a legacy
historical segment, not a complete continuous 2014–2026 archive.

A newer public non-Kaggle alternative is
[`urekmazino69/Nepse-floorsheet-and-indices`](https://huggingface.co/datasets/urekmazino69/Nepse-floorsheet-and-indices).
Its published data card says daily floorsheet and indices cover 2024-01-02 through 2026-08-26.
The dataset exposes trade-level contract number, date, symbol, buyer/seller broker codes,
quantity, rate and amount. Its visible schema has 11 fields: contract_no, calculation_date,
time, stock_symbol, sector, buyer, seller, quantity, rate, amount and id. The publisher notes
that corporate actions are not adjusted. The repository collector and normalizer support
this schema while preserving broker codes as execution-channel IDs.

Another public dataset,
[`AnkitSanjyal/nepse-market-data`](https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data),
shows 1.14M rows and 29.3 MB across its Parquet tables. Its card states that extended daily
price history begins 1995-07-20, while its trade-level floorsheet begins 2026-08-19 and has
a gap from 2026-08-26 through 2026-11-18. The tables include `eod_history_ext`,
`eod_price`, `floorsheet`, `index_intraday`, `bars_1m`, `broker_flow_daily` and
`daily_stats`. This is useful for deeper price history and more recent trade-level data,
but it does not bridge the full older floorsheet history.

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
