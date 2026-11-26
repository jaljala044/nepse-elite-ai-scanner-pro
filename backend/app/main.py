from datetime import date, datetime, timezone, time
from zoneinfo import ZoneInfo
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from .market_structure import add_event_evidence, detect_structure
from .scanner import analyze
from .decision_engine import evaluate_all_horizons
from .structure_timeframes import evaluate_timeframes
from .smc_confluence import evaluate_confluence
from .idpat_v3 import evaluate_idpat_v3, evaluate_provisional
from .scanner_eligibility import assess, REVIEWED_ROWS
from .storage import DATA, IMPORTS, store_rows, snapshot

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
        result = analyze(symbol.upper(), rows)
        cutoff = datetime.now(timezone.utc)
        if request.as_of:
            cutoff = min(cutoff, datetime.combine(request.as_of, time.max, ZoneInfo("Asia/Kathmandu")))
        errors = assess(symbol.upper(), rows, cutoff.isoformat(), REVIEWED_ROWS)
        result["eligibility"] = {"eligible": not errors, "reasons": errors}
        if errors:
            structure_status = (
                result["status"] if result["status"] == "data_quality_failed" else "eligibility_unverified"
            )
            result["market_structure"] = {"status": structure_status, "bias": "neutral", "events": []}
            result["signals"] = []
            result["metrics"] = {}
            if result["status"] == "screened":
                result["status"] = "eligibility_unverified"
        else:
            structure = detect_structure(rows)
            reviewed_rows = [REVIEWED_ROWS[(symbol.upper(), str(row["date"]))] for row in rows]
            add_event_evidence(structure, reviewed_rows)
            result["market_structure"] = structure
        result["idpat_v3"] = evaluate_idpat_v3(rows, eligible=not errors)
        result["provisional_research"] = evaluate_provisional(rows, eligible=not errors)
        timeframes = evaluate_timeframes(rows, eligible=not errors)
        if not errors:
            # Return the reviewed event objects, rather than unlinked duplicates.
            recent = {str(row["date"]) for row in sorted(rows,key=lambda row:str(row["date"]))[-5:]}
            timeframes["t_plus_2"]["recent_events"] = [
                event for event in result["market_structure"]["events"] if event["date"] in recent
            ]
        result["structure_timeframes"] = timeframes
        result["smc_confluence"] = evaluate_confluence(result["market_structure"], timeframes, eligible=not errors)

        # Preview only: current Stage 1/2 modules do not certify all Stage 3
        # gates or provide the eight-component score and horizon trade plans.
        reviewed_for_stage3 = [
            REVIEWED_ROWS[(symbol.upper(), str(row["date"]))]
            for row in rows if not errors
        ]
        stage3_evidence_refs = [
            f'{item["source_id"]}:{item["evidence_id"]}'
            for item in reviewed_for_stage3
            if item.get("source_id") and item.get("evidence_id")
        ]
        stage1_stage3 = {
            "eligible": not errors,
            "data_quality": "LOW",  # no calibrated HIGH/MEDIUM grade is exposed
            "identity_valid": not errors,
            "session_valid": not errors,
            "source_valid": not errors,
            "corporate_actions_clear": False,  # no complete action-clearance contract
            "point_in_time_valid": not errors,
            "liquidity_pass": False,  # execution depth/spread gate not connected
            "market_tradeable": False,  # market-regime approval not connected
        }
        stage2_stage3 = {
            "components": {},  # experimental SMC/IDPAT outputs are not Stage 2 weighted scores
            "structure": {},
        }
        result["stage3_decisions"] = evaluate_all_horizons(
            symbol.upper(), stage1_stage3, stage2_stage3, {},
            evidence_refs=stage3_evidence_refs,
        )
        result["stage3_status"] = "fail_closed_preview"
        result["stage3_limitations"] = [
            "No BUY/HOLD/SELL action is activated by this preview.",
            "The eight weighted Stage 2 components are not yet integrated.",
            "Corporate-action, execution-liquidity and market-regime gates remain unapproved.",
            "No evidence-backed horizon entry, stop or target plans are supplied.",
        ]
        results.append(result)
    return {"mode": "research_only", "results": results,
            "disclaimer": "Rule-based observations only; not investment advice or a guaranteed signal."}

@app.get("/v1/data/{symbol}")
def history(symbol: str):
    rows = DATA.get(symbol.upper())
    if rows is None:
        raise HTTPException(404, "Symbol not found")
    return {"symbol": symbol.upper(), "rows": rows}
