from datetime import date, datetime, timezone, time
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from .market_structure import add_event_evidence, detect_structure
from .scanner import analyze
from .structure_timeframes import evaluate_timeframes
from .smc_confluence import evaluate_confluence
from .idpat_v3 import evaluate_idpat_v3, evaluate_provisional
from .scanner_eligibility import assess, REVIEWED_ROWS
from .equity_universe_manifest import load_equity_universe_manifest
from .storage import DATA, IMPORTS, store_rows, snapshot
from .canonical_feature_pipeline import build_canonical_feature_snapshot

app = FastAPI(title="NEPSE ELITE AI SCANNER PRO", version="0.1.0",
              description="Research-only NEPSE analytics API. No trade execution.")

_UNIVERSE_PATH = Path(__file__).resolve().parents[2] / "data/reference/nepse_active_equity_manifest_2026-11-26.csv"
try:
    EQUITY_UNIVERSE = load_equity_universe_manifest(_UNIVERSE_PATH)
    UNIVERSE_LOAD_ERROR = None
except (OSError, ValueError) as exc:
    # Fail closed: no scan is permitted when the candidate universe is absent or invalid.
    EQUITY_UNIVERSE = None
    UNIVERSE_LOAD_ERROR = str(exc)
class ScanRequest(BaseModel):
    symbols: list[str] | None = None
    as_of: date | None = None

class CanonicalFeatureRequest(BaseModel):
    decision_time: datetime
    symbols: list[str] | None = None

@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "mode": "research_only"}

@app.get("/v1/symbols")
def symbols():
    candidate_symbols = set(EQUITY_UNIVERSE["symbols"]) if EQUITY_UNIVERSE else set()
    loaded = sorted(set(DATA.keys()) & candidate_symbols)
    return {
        "symbols": loaded,
        "count": len(loaded),
        "candidate_universe_count": len(candidate_symbols),
        "universe_status": "secondary_candidate_manifest_validated" if EQUITY_UNIVERSE else "unavailable",
    }

@app.get("/v1/universe")
def universe():
    if EQUITY_UNIVERSE is None:
        raise HTTPException(503, "Equity candidate universe unavailable; scanner is fail-closed")
    return {
        key: value for key, value in EQUITY_UNIVERSE.items()
        if key not in {"security_ids_by_symbol", "manifest_path"}
    } | {
        "membership_authoritatively_verified": False,
        "promotion_allowed": False,
    }

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
    selected = request.symbols
    results = []
    if EQUITY_UNIVERSE is None:
        unavailable = [{
            "symbol": symbol.upper(),
            "status": "universe_unavailable",
            "result_bucket": "universe_unavailable",
            "ranking_eligible": False,
            "buy_list_eligible": False,
            "eligibility": {"eligible": False, "reasons": ["candidate_universe_unavailable"]},
            "signals": [],
            "metrics": {},
        } for symbol in (selected or sorted(DATA.keys()))]
        return {
            "mode": "research_only",
            "results": unavailable,
            "unknown_results": [],
            "ranked_results": [],
            "buy_candidates": [],
            "out_of_scope_results": [],
            "research_only_results": [],
            "universe_unavailable_results": unavailable,
            "disclaimer": "Fail-closed: no equity universe manifest is available.",
        }
    candidate_symbols = set(EQUITY_UNIVERSE["symbols"])
    selected = selected or sorted(candidate_symbols)
    for symbol in selected:
        normalized_symbol = symbol.upper()
        if normalized_symbol not in candidate_symbols:
            results.append({
                "symbol": normalized_symbol,
                "status": "out_of_scope",
                "result_bucket": "out_of_scope",
                "ranking_eligible": False,
                "buy_list_eligible": False,
                "eligibility": {"eligible": False, "reasons": ["not_in_active_equity_candidate_universe"]},
                "signals": [],
                "metrics": {},
            })
            continue
        symbol = normalized_symbol
        if symbol == "UNL":
            results.append({
                "symbol": "UNL",
                "status": "unknown_result",
                "result_bucket": "unknown_results",
                "ranking_eligible": False,
                "buy_list_eligible": False,
                "ranking_exclusion_reason": "insufficient_validated_evidence",
                "eligibility": {
                    "eligible": False,
                    "reasons": [
                        "unl_historical_ohlcv_quarantined",
                        "session_level_trade_vs_no_trade_not_reconciled",
                        "complete_primary_floorsheet_coverage_not_verified",
                        "historical_source_lineage_and_ohlcv_integrity_unresolved",
                    ],
                },
                "signals": [],
                "metrics": {},
                "data_quality": "LOW_CONFIDENCE",
                "data_status": "UNKNOWN",
                "overall_rating": "NOT_RATED",
                "horizon_actions": {
                    "t_plus_2": "UNKNOWN",
                    "swing": "UNKNOWN",
                    "positional": "UNKNOWN",
                    "investment": "UNKNOWN",
                },
                "scan_note": (
                    "UNL is retained in scan output as UNKNOWN, not excluded and not "
                    "treated as a no-trade security. A session is a verified no-trade "
                    "only when the exchange session is confirmed open and complete "
                    "floorsheet coverage contains zero UNL contracts. Do not carry "
                    "forward OHLCV or score missing evidence as neutral."
                ),
            })
            continue
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

        # Unknown is a first-class scan outcome for every equity whose evidence
        # is incomplete, not a special case for UNL. A structurally plausible
        # chart is not enough to authorize scoring when provenance/session/
        # point-in-time review is absent, and short history is not a no-trade.
        if errors or result.get("status") != "screened":
            unknown_reasons = list(errors)
            if result.get("status") == "data_quality_failed":
                unknown_reasons.extend(result.get("limitations", []))
            elif result.get("status") == "insufficient_data":
                unknown_reasons.append("insufficient_validated_observation_history")
            if not unknown_reasons:
                unknown_reasons.append("validated_scan_evidence_unavailable")
            result["status"] = "unknown_result"
            result["result_bucket"] = "unknown_results"
            result["ranking_eligible"] = False
            result["buy_list_eligible"] = False
            result["ranking_exclusion_reason"] = "insufficient_validated_evidence"
            result["data_status"] = "UNKNOWN"
            result["data_quality"] = "LOW_CONFIDENCE"
            result["overall_rating"] = "NOT_RATED"
            result["horizon_actions"] = {
                "t_plus_2": "UNKNOWN",
                "swing": "UNKNOWN",
                "positional": "UNKNOWN",
                "investment": "UNKNOWN",
            }
            result["eligibility"] = {"eligible": not errors, "reasons": unknown_reasons}
            result["signals"] = []
            result["metrics"] = {}
            if errors:
                result["market_structure"] = {
                    "status": "unknown", "bias": "unavailable", "events": []
                }
            result["idpat_v3"] = {"status": "unavailable", "score": None}
            result["provisional_research"] = {"status": "unavailable", "score": None}
            result["structure_timeframes"] = {
                "status": "unavailable",
                "t_plus_2": {"action": "UNKNOWN"},
                "swing": {"action": "UNKNOWN"},
                "positional": {"action": "UNKNOWN"},
                "investment": {"action": "UNKNOWN"},
            }
            result["smc_confluence"] = {"status": "unavailable", "score": None}
            result["scan_note"] = (
                "Insufficient validated evidence: result is UNKNOWN, not BUY, SELL, "
                "HOLD or NO_TRADE. No rating or horizon action is assigned. "
                "NO_TRADE requires verified open-session status and complete "
                "date-matched floorsheet coverage with zero contracts."
            )
        else:
            result["data_status"] = "VALIDATED_FOR_RESEARCH_SCREEN"
            result["data_quality"] = "MEDIUM_CONFIDENCE"
            result["overall_rating"] = "NOT_RATED"
            result["horizon_actions"] = {
                "t_plus_2": "NOT_ASSESSED",
                "swing": "NOT_ASSESSED",
                "positional": "NOT_ASSESSED",
                "investment": "NOT_ASSESSED",
            }
            result["result_bucket"] = "research_only"
            result["ranking_eligible"] = False
            result["buy_list_eligible"] = False
            result["ranking_exclusion_reason"] = "scoring_and_recommendation_engine_not_authorized"
        results.append(result)
    unknown_results = [item for item in results if item.get("status") == "unknown_result"]
    ranked_results = [
        item for item in results
        if item.get("ranking_eligible") is True and item.get("overall_rating") != "NOT_RATED"
    ]
    buy_candidates = [
        item for item in ranked_results
        if item.get("buy_list_eligible") is True
        and any(str(action).upper() == "BUY" for action in item.get("horizon_actions", {}).values())
    ]
    return {
        "mode": "research_only",
        "results": results,
        "unknown_results": unknown_results,
        "ranked_results": ranked_results,
        "buy_candidates": buy_candidates,
        "out_of_scope_results": [item for item in results if item.get("status") == "out_of_scope"],
        "research_only_results": [item for item in results if item.get("result_bucket") == "research_only"],
        "disclaimer": "Rule-based observations only; not investment advice or a guaranteed signal.",
    }


@app.post("/v1/canonical-feature-snapshot")
def canonical_feature_snapshot(request: CanonicalFeatureRequest):
    """Research-only scanner features from server-configured canonical evidence."""
    root = Path(__file__).resolve().parents[2]
    registry_path = Path(os.getenv(
        "NEPSE_SOURCE_TRUST_REGISTRY_PATH",
        str(root / "data" / "reference" / "source-trust-registry.v1.json"),
    ))
    calendar_value = os.getenv("NEPSE_SESSION_CALENDAR_PATH")
    calendar_digest = os.getenv("NEPSE_SESSION_CALENDAR_SHA256", "")
    ledger_path = Path(os.getenv(
        "NEPSE_PROMOTION_LEDGER_PATH",
        str(root / "backend" / "data" / "promotion-ledger.jsonl"),
    ))
    trusted_digest = os.getenv("NEPSE_SOURCE_REGISTRY_SHA256", "")
    reviewer_keys_raw = os.getenv("NEPSE_REVIEWER_KEYS_JSON", "")
    if not calendar_value or not calendar_digest or not trusted_digest or not reviewer_keys_raw:
        return {
            "status": "insufficient_evidence", "decision_status": "UNKNOWN",
            "action": "PRESERVE_CAPITAL", "feature_snapshot": None,
            "missing": ["server_side_calendar_registry_digest_or_reviewer_keys"],
            "production_source_claim": False,
        }
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        raw_keys = json.loads(reviewer_keys_raw)
        if not isinstance(raw_keys, dict) or any(
            not isinstance(name, str) or not isinstance(value, str) or not value
            for name, value in raw_keys.items()
        ):
            raise ValueError("reviewer key configuration must be a non-empty string mapping")
        reviewer_keys = {name: value.encode("utf-8") for name, value in raw_keys.items()}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {
            "status": "insufficient_evidence", "decision_status": "UNKNOWN",
            "action": "PRESERVE_CAPITAL", "feature_snapshot": None,
            "missing": ["valid_server_side_registry_or_reviewer_key_configuration"],
            "production_source_claim": False,
        }
    return build_canonical_feature_snapshot(
        database_path=None, ledger_path=ledger_path, registry=registry,
        trusted_registry_sha256=trusted_digest, reviewer_keys=reviewer_keys,
        calendar_path=calendar_value, trusted_calendar_sha256=calendar_digest,
        decision_time=request.decision_time.isoformat(),
        expected_symbols=request.symbols or sorted(set(DATA.keys()) & set(EQUITY_UNIVERSE["symbols"] if EQUITY_UNIVERSE else [])),
    )

@app.get("/v1/data/{symbol}")
def history(symbol: str):
    rows = DATA.get(symbol.upper())
    if rows is None:
        raise HTTPException(404, "Symbol not found")
    return {"symbol": symbol.upper(), "rows": rows}
