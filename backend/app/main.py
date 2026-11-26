import csv
import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from .scanner import analyze
from .storage import CandleConflict, SQLiteStore

MAX_CSV_BYTES = 15 * 1024 * 1024
DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "instance" / "nepse.sqlite3"
store = SQLiteStore(Path(os.environ.get("NEPSE_DB_PATH") or DEFAULT_DATABASE))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(store.initialize)
    yield


app = FastAPI(
    title="NEPSE ELITE AI SCANNER PRO",
    version="0.1.0",
    description="Research-only NEPSE analytics API. No trade execution.",
    lifespan=lifespan,
)


class ScanRequest(BaseModel):
    symbols: list[str] | None = None
    as_of: date | None = None


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "mode": "research_only"}


@app.get("/ready")
def ready():
    if not store.is_ready():
        raise HTTPException(503, "Database is unavailable or requires migration")
    return {"status": "ready"}


@app.get("/v1/symbols")
def symbols():
    listed = store.symbols()
    return {"symbols": listed, "count": len(listed)}


@app.get("/v1/imports")
def imports():
    return {"imports": store.recent_imports()}


@app.post("/v1/ingest/csv")
async def ingest_csv(file: UploadFile = File(...), x_source_label: str = Header(default="user_upload")):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a .csv file")
    raw = await file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(413, "CSV exceeds 15 MiB limit")
    try:
        return await run_in_threadpool(store.store_rows, raw, x_source_label[:100])
    except CandleConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except (ValueError, csv.Error) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/v1/scan")
def scan(request: ScanRequest):
    results = [analyze(symbol, rows) for symbol, rows in store.histories(request.symbols, request.as_of)]
    return {
        "mode": "research_only",
        "results": results,
        "disclaimer": "Rule-based observations only; not investment advice or a guaranteed signal.",
    }


@app.get("/v1/data/{symbol}")
def history(symbol: str):
    normalized = symbol.upper()
    rows = store.history(normalized)
    if not rows:
        raise HTTPException(404, "Symbol not found")
    return {"symbol": normalized, "rows": rows}
