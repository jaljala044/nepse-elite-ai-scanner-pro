# NEPSE ELITE AI SCANNER PRO

Private, research-oriented NEPSE market analysis platform. This repository starts with a deliberately conservative backend foundation; it does not place trades or promise predictive accuracy.

## Status
- Foundation scaffold: initial implementation
- Data ingestion: CSV OHLCV with validation and audit metadata
- Public datasets: Hugging Face inventory, bounded/resumable downloader, daily floorsheet and sector-index normalizers, and independent audit reports
- Kaggle: safe local download/staging helper (requires your locally configured Kaggle CLI)
- Scanner: transparent, rule-based technical feature extraction (not an institutional-flow detector)
- Live API feeds, paid broker integrations, web UI, Android app, authentication, deployment and scheduled automation: not yet connected or verified

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

## CSV format
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

See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md), [docs/ANALYSIS_METHOD.md](docs/ANALYSIS_METHOD.md) and [docs/ROADMAP.md](docs/ROADMAP.md).
