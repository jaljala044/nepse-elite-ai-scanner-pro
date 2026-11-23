# NEPSE ELITE AI SCANNER PRO

Private, research-oriented NEPSE market analysis platform. This repository starts with a deliberately conservative backend foundation; it does not place trades or promise predictive accuracy.

## Status
- Foundation scaffold: initial implementation
- Data ingestion: CSV OHLCV with validation and audit metadata
- Scanner: transparent, rule-based technical feature extraction (not an institutional-flow detector)
- Live feeds, broker/floorsheet integrations, web UI, Android app, authentication, deployment and scheduled automation: not yet connected or verified

## Quick start
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

## CSV format
Required columns: `symbol,date,open,high,low,close,volume`. Dates should be ISO `YYYY-MM-DD`; prices and volume must be positive (volume may be zero). One file may contain multiple symbols.

Example:
```csv
symbol,date,open,high,low,close,volume
NABIL,2026-11-20,500,515,495,510,120000
```

## Safety and data integrity
- Never treat missing or stale prices as live.
- Every import carries a source label and session date.
- Conflicting duplicate symbol/date rows are rejected.
- Scanner output is educational research, not a buy/sell instruction.
- No automated order execution is included.
- Do not enable scheduled scans until each data feed is tested, licensed/authorized where required, and reconciled against an authoritative exchange source.

See [docs/ANALYSIS_METHOD.md](docs/ANALYSIS_METHOD.md) and [docs/ROADMAP.md](docs/ROADMAP.md).
