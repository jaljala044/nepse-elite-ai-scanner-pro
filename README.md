# NEPSE ELITE AI SCANNER PRO

Private, research-oriented NEPSE market analysis platform. This repository starts with a deliberately conservative backend foundation; it does not place trades or promise predictive accuracy.

## Status
- Foundation scaffold: initial implementation
- Data ingestion: CSV OHLCV with validation and audit metadata; API uploads and history now persist in a local DuckDB database (`backend/data/nepse-api.duckdb` by default)
- Public datasets: Hugging Face inventory, bounded/resumable downloader, daily floorsheet and sector-index normalizers, and independent audit reports
- Kaggle: safe local download/staging helper (requires your locally configured Kaggle CLI)
- Scanner: transparent, rule-based technical feature extraction (not an institutional-flow detector)
- Broker behaviour memory: first backend persistence/API foundation and responsive web explorer are implemented on PR #87; it stores only rows admitted by the verified evidence contract and is not connected to live floorsheet ingestion or a daily scheduler
- Early entry/exit: an uncalibrated, fail-closed research-rule evaluator exists, but it is not yet wired to a verified market-context producer or production scanner/watchlist
- Mobile app: no mobile client source tree is currently present in this repository; mobile implementation remains outstanding
- Live API feeds, paid broker integrations, authentication, production deployment and scheduled automation: not yet connected or verified

## Quick start
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

## NEPSE data collection

All commands below run from `backend/` after installing requirements:

```bash
# Inventory public Hugging Face dataset files (no data download)
python collect_hf_datasets.py

# Download a small test sample into data/raw/huggingface
python collect_hf_datasets.py --dataset floorsheet_indices_2024 --download --max-total-mb 50

# For a full pull, the measured compressed archive is about 728 MiB.
# Re-running safely skips already-present files only when the published SHA-256 matches.
python collect_hf_datasets.py --dataset floorsheet_indices_2024 --download \
  --max-total-mb 800 --max-file-mb 20 --max-files 10000

# Normalize floorsheet and sector-index CSV.GZ files into separate silver tables
python normalize_floorsheet_csv.py ../data/raw/huggingface/urekmazino69__Nepse-floorsheet-and-indices/main/floorsheet \
  --source urekmazino69/Nepse-floorsheet-and-indices

python normalize_indices_csv.py ../data/raw/huggingface/urekmazino69__Nepse-floorsheet-and-indices/main/indices \
  --source urekmazino69/Nepse-floorsheet-and-indices

# Audit each normalized dataset independently
python audit_silver_floorsheet.py
python audit_silver_indices.py

# Optional: after setting up Kaggle CLI locally, stage the historic Kaggle archive
python ingest_kaggle_floorsheet.py --confirm-download
```

The one-session smoke test on 2024-01-02 accepted 85,435 floorsheet rows and 16 index rows with no configured quality-gate failures; this is a parser check, not a full-history validation. Large source files are stored locally, excluded by `.gitignore`, and are not committed to GitHub. Review [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for dataset coverage, licensing notes, gaps and validation rules.

### Build the separate Ankit Parquet warehouse

After fetching the Ankit public Parquet files into `data/raw/huggingface/`:

```bash
python inspect_parquet_datasets.py \
  --input ../data/raw/huggingface/AnkitSanjyal__nepse-market-data/main

python load_ankit_warehouse.py \
  --input ../data/raw/huggingface/AnkitSanjyal__nepse-market-data/main \
  --database ../data/warehouse/nepse-analytics.duckdb \
  --report ../data/reports/ankit-warehouse-load.json
```

The loader preserves the six source tables separately in DuckDB and emits row-level QA
including floorsheet arithmetic, broker-flow reconciliation, OHLC anomalies and EOD
source-overlap differences. It does not auto-correct prices or generate buy/sell instructions.


## Historical coverage matrix (new)

The first coverage utility is deliberately conservative. It compares dated source
files against an evidence-backed calendar and keeps unverified dates visible.
It does not infer exchange sessions from weekdays, and it does not claim that a
file's presence proves row completeness.

Prepare an evidence-backed calendar CSV with these columns:

```csv
session_date,calendar_status,evidence_source,evidence_ref,decision_reason
```

Allowed statuses: `confirmed_session`, `confirmed_non_session`,
`candidate_unverified`, and `conflict`. Do not populate confirmed statuses
without recorded evidence.

Generate a source-separated file-level report from one or more inventory manifests:

```bash
python build_coverage_matrix.py --calendar ../data/reference/nepse-session-calendar.csv \
  --manifest ../data/reports/github-source-inventory.json \
  --manifest ../data/raw/huggingface/manifests/hf_inventory_YYYYMMDDTHHMMSSZ.json \
  --output ../data/reports/historical-coverage-matrix.json
```

The report flags dated files on confirmed sessions, files on confirmed
non-sessions, calendar conflicts, unverified dates and undated files. It does
not infer missing sessions. Symbol-level coverage and row-level acceptance
remain separate follow-on gates.

## API persistence\n\nThe FastAPI upload/history store uses DuckDB and initializes its schema automatically. Set `NEPSE_API_DATABASE` to choose a persistent database path. The API database is separate from the source-separated historical research warehouse; an upload is not promoted to canonical market data and does not imply source rights or completeness.\n\n## CSV format
Required columns: `symbol,date,open,high,low,close,volume`. Dates should be ISO `YYYY-MM-DD`; prices and volume must be positive (volume may be zero). One file may contain multiple symbols.

Example:
```csv
symbol,date,open,high,low,close,volume
NABIL,2026-11-20,500,515,495,510,120000
```

## Tests

From `backend/`:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions workflow: [backend-tests.yml](.github/workflows/backend-tests.yml).

## Safety and data integrity
- Never treat missing or stale prices as live.
- Every import carries a source label and session date.
- Conflicting duplicate symbol/date rows are rejected.
- Scanner output is educational research, not a buy/sell instruction.
- No automated order execution is included.
- Do not enable scheduled scans until each data feed is tested, licensed/authorized where required, and reconciled against an authoritative exchange source.

See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md), [docs/ANALYSIS_METHOD.md](docs/ANALYSIS_METHOD.md), [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/BROKER_BEHAVIOUR_MEMORY_EARLY_ENTRY_EXIT.md](docs/BROKER_BEHAVIOUR_MEMORY_EARLY_ENTRY_EXIT.md).
