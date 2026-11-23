from datetime import date
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from .scanner import analyze
from .scanner_v3 import analyze_v3
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
