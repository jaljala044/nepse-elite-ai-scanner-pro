from datetime import date, datetime, timezone, time
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
from .broker_intelligence_dashboard import build_broker_intelligence_dashboard
from .early_entry_exit_signals import generate_early_entry_exit_signals
from .signal_tracking import freeze_signal, HORIZONS as TRACKED_HORIZONS
from .signal_store import store_signal, store_outcome, get_signal, list_signals, list_signal_outcomes, list_all_outcomes
from .signal_outcome_validation import evaluate_signal_path

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

class BrokerDashboardRequest(BaseModel):
    as_of_date: date
    as_of_timestamp: str
    rolling_profiles: dict
    source_manifest: dict
    sector_rotation_by_window: dict = Field(default_factory=dict)
    candidates: list[dict] = Field(default_factory=list)

class EarlySignalRequest(BaseModel):
    as_of_date: date
    as_of_timestamp: str
    snapshot: dict

class FreezeSignalRequest(BaseModel):
    symbol: str
    decision_time: str
    horizon: str
    action: str
    methodology: str
    evidence: list[dict]
    details: dict

class EvaluateSignalOutcomeRequest(BaseModel):
    evaluation_date: date
    verified_sessions: list[date]
    calendar_evidence: dict

class StoreSignalOutcomeRequest(BaseModel):
    horizon: str
    observed_at: str
    outcome: dict


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "mode": "research_only"}

@app.post("/v1/research/broker-dashboard")
def broker_dashboard(request: BrokerDashboardRequest):
    """Compose supplied upstream broker evidence into a read-only dashboard.

    This endpoint does not ingest or verify source files. It propagates upstream
    provenance assertions and withholds incomplete/late evidence.
    """
    try:
        return build_broker_intelligence_dashboard(
            as_of_date=request.as_of_date.isoformat(),
            as_of_timestamp=request.as_of_timestamp,
            rolling_profiles=request.rolling_profiles,
            source_manifest=request.source_manifest,
            sector_rotation_by_window=request.sector_rotation_by_window,
            candidates=request.candidates,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.post("/v1/research/early-signals")
def early_signals(request: EarlySignalRequest):
    """Generate conservative horizon-separated signals from supplied evidence.

    Upstream evidence is caller-supplied and not independently re-attested here.
    The endpoint never places orders or claims confirmed fills.
    """
    try:
        return generate_early_entry_exit_signals(
            request.snapshot, as_of_date=request.as_of_date.isoformat(),
            as_of_timestamp=request.as_of_timestamp,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/v1/research/signals")
def create_research_signal(request: FreezeSignalRequest):
    """Freeze and persist a content-addressed research signal; never places an order."""
    try:
        envelope = freeze_signal(
            symbol=request.symbol, decision_time=request.decision_time,
            horizon=request.horizon, action=request.action,
            methodology=request.methodology, evidence=request.evidence,
            details=request.details,
        )
        stored = store_signal(envelope)
        return {**envelope, "storage": stored,
                "classification": "research_only_not_execution"}
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/research/signals")
def research_signals(symbol: str | None = None, horizon: str | None = None, limit: int = 500):
    try:
        return {"classification": "research_only_not_execution",
                "signals": list_signals(symbol=symbol, horizon=horizon, limit=limit)}
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/v1/research/signals/{signal_id}/evaluate")
def evaluate_research_signal(signal_id: str, request: EvaluateSignalOutcomeRequest):
    """Measure price references using server-reviewed OHLCV and a caller-attested calendar."""
    try:
        record = get_signal(signal_id)
        if record is None:
            raise HTTPException(404, "signal_not_found")
        if record.get("symbol") not in DATA:
            raise HTTPException(422, "ohlcv_history_unavailable")
        calendar = request.calendar_evidence
        cutoff = datetime.combine(request.evaluation_date, time.max, ZoneInfo("Asia/Kathmandu"))
        if (calendar.get("status") != "verified"
                or not calendar.get("source_id")
                or float(calendar.get("coverage", 0)) < 0.95):
            raise HTTPException(422, "verified_calendar_evidence_required")
        available = datetime.fromisoformat(str(calendar.get("available_at", "")).replace("Z", "+00:00"))
        if available.tzinfo is None or available > cutoff:
            raise HTTPException(422, "calendar_evidence_late_or_timezone_missing")
        rows = DATA[record["symbol"]]
        result = evaluate_signal_path(
            record, rows, [d.isoformat() for d in request.verified_sessions],
            evaluation_date=request.evaluation_date.isoformat(), reviewed=REVIEWED_ROWS,
        )
        if result.get("status") in {"observed", "partial"}:
            saved = store_outcome(
                signal_id=signal_id, horizon=record["horizon"],
                observed_at=cutoff.isoformat(), outcome=result,
            )
            result["storage"] = saved
        return result
    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/research/signals/{signal_id}/outcomes")
def research_signal_outcomes(signal_id: str):
    if get_signal(signal_id) is None:
        raise HTTPException(404, "signal_not_found")
    return {"classification": "research_reference_not_execution",
            "outcomes": list_signal_outcomes(signal_id)}


@app.get("/v1/research/performance")
def research_signal_performance(horizon: str | None = None, limit: int = 2000):
    """Descriptive gross reference outcomes only; no strategy edge is inferred."""
    try:
        outcomes = list_all_outcomes(horizon=horizon, limit=limit)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    grouped = {}
    for item in outcomes:
        h = item.get("horizon")
        payload = item.get("outcome", {})
        bucket = grouped.setdefault(h, {"sample_size": 0, "entry_touched": 0,
            "positive_reference": 0, "negative_reference": 0,
            "returns": [], "statuses": {}})
        bucket["sample_size"] += 1
        status = payload.get("status", "unknown")
        bucket["statuses"][status] = bucket["statuses"].get(status, 0) + 1
        if payload.get("entry_touched") is True and payload.get("reference_return_pct") is not None:
            value = float(payload["reference_return_pct"])
            bucket["entry_touched"] += 1
            bucket["returns"].append(value)
            if value > 0: bucket["positive_reference"] += 1
            elif value < 0: bucket["negative_reference"] += 1
    summaries = {}
    for h, bucket in grouped.items():
        vals = bucket.pop("returns")
        winners = [x for x in vals if x > 0]
        losers = [x for x in vals if x < 0]
        bucket["win_rate_pct"] = (100 * len(winners) / len(vals)) if vals else None
        bucket["average_reference_return_pct"] = (sum(vals) / len(vals)) if vals else None
        bucket["average_win_pct"] = (sum(winners) / len(winners)) if winners else None
        bucket["average_loss_pct"] = (sum(losers) / len(losers)) if losers else None
        bucket["profit_factor"] = (sum(winners) / abs(sum(losers))) if losers and sum(losers) else None
        bucket["data_quality"] = "LOW_CONFIDENCE" if len(vals) < 30 else "DESCRIPTIVE_ONLY"
        summaries[h] = bucket
    return {"classification": "gross_price_reference_statistics_not_backtest",
            "sample_count": len(outcomes), "by_horizon": summaries,
            "limitations": ["No execution/fill records, fees, slippage or market impact",
                            "Repeated evaluations of one signal are separate observations; deduplication is not a trade ledger",
                            "No calibrated probability or strategy-performance claim is produced"]}


@app.get("/v1/research/readiness")
def research_readiness():
    """Read-only UI contract. Never exposes uploaded data or authorizes recommendations."""
    return {
        "mode": "research_only",
        "candidate_equities": len(EQUITY_UNIVERSE["symbols"]) if EQUITY_UNIVERSE else None,
        "canonical_reviewed_rows": len(REVIEWED_ROWS),
        "universe_available": EQUITY_UNIVERSE is not None,
        "independent_strategy_validation": False,
        "production_recommendations_enabled": False,
        "ai_recommendations_enabled": False,
        "ranking_enabled": False,
        "modules": {
            "market_structure": "research_only",
            "ipda": "implemented_not_production_certified",
            "zone_lifecycle": "implemented_not_production_certified",
            "multitimeframe": "implemented_not_production_certified",
            "broker_confluence": "implemented_not_production_certified",
            "combined_strategy": "research_test_not_approved",
        },
        "missing_evidence_policy": "UNKNOWN",
    }

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

@app.get("/v1/data/{symbol}")
def history(symbol: str):
    rows = DATA.get(symbol.upper())
    if rows is None:
        raise HTTPException(404, "Symbol not found")
    return {"symbol": symbol.upper(), "rows": rows}
