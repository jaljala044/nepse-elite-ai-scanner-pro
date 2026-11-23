from datetime import date
import os
from pathlib import Path
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from .scanner import analyze
from .scanner_v3 import analyze_v3
from .duckdb_coverage_v3 import audit_duckdb_ohlcv
from .coverage_audit import audit_coverage
from .storage import DATA, IMPORTS, store_rows

app = FastAPI(title="NEPSE ELITE AI SCANNER PRO", version="0.1.0",
              description="Research-only NEPSE analytics API. No trade execution.")


class ScanRequest(BaseModel):
    symbols: list[str] | None = None
    as_of: date | None = None


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "mode": "research_only"}


@app.get("/v1/symbols")
def symbols():
    return {"symbols": sorted(DATA.keys()), "count": len(DATA)}


@app.get("/v1/imports")
def imports():
    return {"imports": IMPORTS[-100:]}


@app.post("/v1/ingest/csv")
async def ingest_csv(file: UploadFile = File(...), x_source_label: str = Header(default="user_upload")):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a .csv file")
    raw = await file.read()
    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(413, "CSV exceeds 15 MiB limit")
    try:
        result = store_rows(raw.decode("utf-8-sig"), x_source_label[:100])
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return result


@app.post("/v1/scan")
def scan(request: ScanRequest):
    selected = request.symbols or sorted(DATA.keys())
    results = []
    for symbol in selected:
        rows = DATA.get(symbol.upper(), [])
        if request.as_of:
            rows = [r for r in rows if r["date"] <= request.as_of]
        results.append(analyze(symbol.upper(), rows))
    return {"mode": "research_only", "results": results,
            "disclaimer": "Rule-based observations only; not investment advice or a guaranteed signal."}


@app.post("/v3/scan")
def scan_v3(request: ScanRequest):
    """Run the separate V3 descriptive feature engine on ingested daily bars."""
    selected = request.symbols or sorted(DATA.keys())
    results = []
    for symbol in selected:
        rows = DATA.get(symbol.upper(), [])
        if request.as_of:
            rows = [
                row for row in rows
                if (row["date"] if isinstance(row["date"], date) else date.fromisoformat(str(row["date"])[:10]))
                <= request.as_of
            ]
        results.append(analyze_v3(symbol.upper(), rows))
    return {
        "engine": "v3",
        "mode": "research_only",
        "results": results,
        "disclaimer": "Descriptive research observations only; not a buy/sell recommendation or guaranteed prediction.",
    }


@app.get("/v1/data/{symbol}")
def history(symbol: str):
    rows = DATA.get(symbol.upper())
    if rows is None:
        raise HTTPException(404, "Symbol not found")
    return {"symbol": symbol.upper(), "rows": rows}


@app.get("/v3/audit/coverage")
def audit_v3_coverage(as_of: date | None = None, target_universe_size: int = 309):
    """Audit daily OHLCV coverage directly from the read-only DuckDB warehouse."""
    if target_universe_size < 1 or target_universe_size > 1000:
        raise HTTPException(422, "target_universe_size must be between 1 and 1000")
    configured = os.getenv("NEPSE_DUCKDB_PATH")
    database_path = (
        Path(configured).expanduser()
        if configured
        else Path(__file__).resolve().parents[2] / "data" / "warehouse" / "nepse-analytics.duckdb"
    )
    try:
        return audit_duckdb_ohlcv(
            database_path,
            as_of=as_of,
            target_universe_size=target_universe_size,
        )
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"DuckDB coverage audit failed: {exc}") from exc



@app.get("/v3/audit/coverage/strict")
def audit_v3_coverage_strict():
    """Audit every configured master symbol against a verified session calendar."""
    database_path = os.getenv("NEPSE_DUCKDB_PATH")
    master_table = os.getenv("NEPSE_SYMBOL_MASTER_TABLE")
    calendar_table = os.getenv("NEPSE_SESSION_CALENDAR_TABLE")
    if not database_path:
        raise HTTPException(503, "NEPSE_DUCKDB_PATH is not configured")
    if not master_table or not calendar_table:
        raise HTTPException(
            503,
            "Strict audit requires NEPSE_SYMBOL_MASTER_TABLE and "
            "NEPSE_SESSION_CALENDAR_TABLE; no reference data will be guessed.",
        )
    try:
        return audit_coverage(
            database=database_path,
            ohlcv_table=os.getenv("NEPSE_OHLCV_TABLE", "ankit.eod_price"),
            symbol_master_table=master_table,
            calendar_table=calendar_table,
            symbol_col=os.getenv("NEPSE_OHLCV_SYMBOL_COL", "symbol"),
            date_col=os.getenv("NEPSE_OHLCV_DATE_COL", "business_date"),
            open_col=os.getenv("NEPSE_OHLCV_OPEN_COL", "open_price"),
            high_col=os.getenv("NEPSE_OHLCV_HIGH_COL", "high_price"),
            low_col=os.getenv("NEPSE_OHLCV_LOW_COL", "low_price"),
            close_col=os.getenv("NEPSE_OHLCV_CLOSE_COL", "close_price"),
            volume_col=os.getenv("NEPSE_OHLCV_VOLUME_COL", "total_traded_quantity"),
            master_symbol_col=os.getenv("NEPSE_MASTER_SYMBOL_COL", "symbol"),
            calendar_date_col=os.getenv("NEPSE_CALENDAR_DATE_COL", "session_date"),
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Strict DuckDB coverage audit failed: {exc}") from exc
