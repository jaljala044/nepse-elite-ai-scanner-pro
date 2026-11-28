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
from .broker_pattern_detector import detect_broker_patterns
from .index_intelligence import build_verified_index_intelligence
from .verified_sector_rotation import build_verified_sector_rotation
from .sector_intelligence_confluence import build_sector_intelligence_confluence

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

class BrokerPatternRequest(BaseModel):
    symbol: str
    broker_rows: list[dict]
    price_rows: list[dict]
    market_context: list[dict]
    expected_sessions: list[str]
    complete_broker_sessions: list[str]
    decision_at: str

class IndexIntelligenceRequest(BaseModel):
    rows: list[dict]
    verified_session_dates: list[str]
    decision_time: str
    index_code: str = "NEPSE"

class SectorRotationRequest(BaseModel):
    stock_rows: list[dict]
    benchmark_rows: list[dict]
    expected_sector_members: dict[str, list[str]]
    sector_membership: dict[str, dict]
    verified_session_dates: list[str]
    decision_time: str

class SectorConfluenceRequest(BaseModel):
    market_rotation: dict
    broker_rotation: dict
    decision_time: str
    minimum_broker_count: int = 1

@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "mode": "research_only"}

@app.get("/v1/market-health")
def market_health():
    """Expose readiness without fabricating a live market regime.

    The integrated calculator is not connected to a trusted persistent store
    for index, market-summary, mature-equity and sector evidence.
    """
    return {
        "status": "insufficient_evidence",
        "decision_session": None,
        "market_health_score": None,
        "regime": "unknown",
        "trading_posture": "preserve_capital",
        "confidence": "LOW",
        "coverage_pct": 0.0,
        "coverage_status": "insufficient",
        "component_scores": {
            "trend": None, "breadth": None, "turnover": None,
            "sector_participation": None, "volatility": None,
        },
        "missing_components": [
            "trend", "breadth", "turnover", "sector_participation", "volatility"
        ],
        "readiness": {
            "calculator_integrated": True,
            "production_source_store_connected": False,
            "canonical_session_calendar": "unavailable_to_market_health",
            "verified_nepse_index_ohlcv": "not_connected",
            "verified_market_summary_turnover": "not_connected",
            "verified_mature_equity_ohlcv": "not_connected",
            "verified_sector_membership": "not_authoritatively_verified",
            "verified_sector_price_evidence": "not_connected",
        },
        "probability": None,
        "action": "PRESERVE_CAPITAL",
        "note": (
            "No live market-health score is published. Existing CSV imports "
            "do not retain the complete record-level source, finality, "
            "availability and payload-hash evidence required by the market "
            "adapters. The secondary candidate universe is not authoritative "
            "sector membership evidence."
        ),
    }

@app.post("/v1/research/broker-dashboard")
def broker_dashboard(request: BrokerDashboardRequest):
    """Read-only broker dashboard; upstream provenance is not independently re-attested."""
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
    """Conservative research-only signals; no orders or confirmed fills."""
    try:
        return generate_early_entry_exit_signals(
            request.snapshot, as_of_date=request.as_of_date.isoformat(),
            as_of_timestamp=request.as_of_timestamp,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.post("/v1/research/broker-patterns")
def broker_patterns(request: BrokerPatternRequest):
    """Point-in-time accumulation/distribution candidates, never trading instructions."""
    try:
        return detect_broker_patterns(
            request.symbol, request.broker_rows, request.price_rows, request.market_context,
            expected_sessions=request.expected_sessions,
            complete_broker_sessions=request.complete_broker_sessions,
            decision_at=request.decision_at,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.post("/v1/research/index-intelligence")
def index_intelligence_research(request: IndexIntelligenceRequest):
    """Verified-input research calculator; caller-supplied rows are not independently sourced here."""
    try:
        return build_verified_index_intelligence(
            request.rows, verified_session_dates=request.verified_session_dates,
            index_code=request.index_code, decision_time=request.decision_time,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.post("/v1/research/sector-rotation")
def sector_rotation_research(request: SectorRotationRequest):
    """Verified-input sector rotation calculator; no BUY/SELL actions."""
    try:
        return build_verified_sector_rotation(
            request.stock_rows, request.benchmark_rows,
            expected_sector_members=request.expected_sector_members,
            sector_membership=request.sector_membership,
            verified_session_dates=request.verified_session_dates,
            decision_time=request.decision_time,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.post("/v1/research/sector-confluence")
def sector_confluence_research(request: SectorConfluenceRequest):
    """Join price and broker-sector outputs descriptively; never infer ownership or intent."""
    try:
        return build_sector_intelligence_confluence(
            request.market_rotation, request.broker_rotation,
            decision_time=request.decision_time,
            minimum_broker_count=request.minimum_broker_count,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc

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

@app.get("/v1/history/{symbol}")
def history_page(symbol: str, offset: int = 0, limit: int = 500, snapshot: str | None = None):
    import hashlib
    import json
    if offset < 0 or not 1 <= limit <= 1000:
        raise HTTPException(422, "Invalid pagination")
    rows = DATA.get(symbol.upper())
    if rows is None:
        raise HTTPException(404, "Symbol not found")
    ordered = sorted(rows, key=lambda r: str(r["date"]))
    digest = hashlib.sha256(json.dumps(ordered, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    if (offset > 0 and snapshot is None) or (snapshot is not None and snapshot != digest):
        raise HTTPException(409, "History changed or snapshot missing; restart pagination")
    if offset > len(ordered):
        raise HTTPException(422, "Offset outside history")
    end = min(offset + limit, len(ordered))
    return {"symbol": symbol.upper(), "rows": ordered[offset:end], "total": len(ordered),
            "snapshot": digest, "offset": offset, "next_offset": end if end < len(ordered) else None,
            "status": "observed_history_not_independently_certified"}

@app.get("/v1/volume-profile/{symbol}")
def volume_profile(symbol: str, start: date, end: date):
    from .volume_profile_store import load_profile
    symbol=symbol.upper()
    if EQUITY_UNIVERSE is None or symbol not in EQUITY_UNIVERSE["symbols"]:
        return {"status":"unavailable","symbol":symbol,"levels":[],"reason":"equity_universe_gate"}
    return load_profile(symbol,start,end)


@app.get("/v1/broker/summary/{symbol}")
def broker_summary(symbol: str, start: date, end: date):
    from decimal import Decimal
    from .volume_profile_store import load_profile
    symbol = symbol.upper()
    if EQUITY_UNIVERSE is None or symbol not in EQUITY_UNIVERSE["symbols"]:
        return {"status":"unavailable","reason":"equity_universe_gate"}
    profile = load_profile(symbol, start, end)
    if profile.get("status") != "research_only":
        return {"status":profile.get("status","unavailable"),"reason":profile.get("reason"),"symbol":symbol}
    brokers = {}
    for level in profile["levels"]:
        for side in ("buyer","seller"):
            for code, qty in level[side+"_broker_quantity"].items():
                b = brokers.setdefault(code, {"buy_qty":Decimal(0),"sell_qty":Decimal(0),"buy_amount":Decimal(0),"sell_amount":Decimal(0)})
                prefix = "buy" if side=="buyer" else "sell"
                b[prefix+"_qty"] += Decimal(qty)
                b[prefix+"_amount"] += Decimal(qty)*Decimal(level["price"])
    rows = []
    for code, b in brokers.items():
        rows.append({"broker_code":code, **{k:str(v) for k,v in b.items()},
                     "net_qty":str(b["buy_qty"]-b["sell_qty"]),
                     "net_amount":str(b["buy_amount"]-b["sell_amount"])})
    rows.sort(key=lambda x:(-Decimal(x["net_amount"]),x["broker_code"]))
    total = Decimal(profile["total_amount"])*2
    gross = sorted((b["buy_amount"]+b["sell_amount"] for b in brokers.values()),reverse=True)
    return {"status":"research_only","symbol":symbol,"start":str(start),"end":str(end),
            "brokers":rows,"top3_gross_share_pct":str(sum(gross[:3])/total*100) if total else None,
            "control_evidence_ids":profile["control_evidence_ids"],
            "limitations":["Broker codes are execution channels, not verified beneficial owners.",
                           "Net buying is not proof of accumulation or future return."]}

@app.get("/v1/research/strategy-modes")
def strategy_modes():
    return {"status":"research_only","production_recommendations_enabled":False,
            "modes":{"swing":{"holding_days":[3,15],"broker_confirmation_sessions":5},
                     "positional":{"holding_weeks":[2,8],"broker_confirmation_sessions":21}},
            "minimum_reward_risk":2,"short_selling_enabled":False,
            "parameters_status":"research_policy_not_validated"}


@app.get("/v1/research/reliability")
def reliability():
    return {"status":"research_only","independent_validation":False,
            "production_recommendations_enabled":False,
            "experiments":[{"id":"P7.10.9","classification":"exploratory_not_holdout",
              "period":"2026","cost_percentage_points":1,
              "strategy":"All four combined structural proxies",
              "outcomes":[{"sessions":5,"n":93,"mean_net_pct":-1.530,"win_pct":29.03,"profit_factor":0.392},
                          {"sessions":20,"n":76,"mean_net_pct":-0.835,"win_pct":32.89,"profit_factor":0.746},
                          {"sessions":40,"n":66,"mean_net_pct":-1.916,"win_pct":33.33,"profit_factor":0.574}],
              "decision":"not_approved","limitations":["Uncertified session calendar and historical data",
              "No independent holdout; incomplete broker, sector and corporate-action evidence",
              "Overlapping research observations, not portfolio performance"]}]}


from fastapi import Request, Depends
from .private_accounts import principal, proxy_principal, issue_mobile_session, revoke_mobile_session, watchlist, set_watchlist, list_alerts, add_alert, delete_alert

@app.post("/v1/account/mobile/session")
def mobile_session_issue(request: Request, owner: str = Depends(proxy_principal)):
    # Require a gateway-injected proof separate from its identity header.
    import hmac
    proof = os.getenv("NEPSE_MOBILE_GATEWAY_PROOF", "")
    provided = request.headers.get("x-nepse-mobile-gateway-proof", "")
    if len(proof)<32 or not hmac.compare_digest(proof.encode(),provided.encode()):
        raise HTTPException(403,"Trusted mobile exchange required")
    if os.getenv("NEPSE_MOBILE_EXCHANGE_ENABLED") != "1":
        raise HTTPException(503,"Mobile identity exchange unavailable")
    from fastapi.responses import JSONResponse
    return JSONResponse(issue_mobile_session(owner),headers={"Cache-Control":"no-store"})

@app.post("/v1/account/mobile/logout")
def mobile_session_logout(request: Request):
    revoke_mobile_session(request.headers.get("authorization",""))
    return {"revoked":True}

@app.get("/v1/account/session")
def account_session(owner: str = Depends(principal)):
    admins = {s.strip() for s in os.getenv("NEPSE_ADMIN_SUBJECTS", "").split(",") if s.strip()}
    return {"authenticated": True, "role": "administrator" if owner in admins else "researcher",
            "permissions": {"watchlist": True, "research": True,
                            "admin_ingestion": owner in admins, "ai_recommendations": False},
            "mode": "research_only"}

class WatchlistRequest(BaseModel):
    symbols: list[str] = Field(max_length=300)

@app.get("/v1/account/watchlist")
def account_watchlist(owner: str = Depends(principal)):
    return {"symbols":watchlist(owner)}

@app.put("/v1/account/watchlist")
def account_watchlist_update(payload: WatchlistRequest, owner: str = Depends(principal)):
    try:
        return {"symbols":set_watchlist(owner,payload.symbols)}
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc

class PriceAlertRequest(BaseModel):
    symbol: str = Field(max_length=20)
    direction: str = Field(max_length=5)
    threshold: str = Field(max_length=32)

@app.get("/v1/account/alerts")
def account_alerts(owner: str = Depends(principal)):
    return {"rules": list_alerts(owner), "delivery_enabled": False}

@app.post("/v1/account/alerts")
def account_alert_add(payload: PriceAlertRequest, owner: str = Depends(principal)):
    try:
        return {"rules": add_alert(owner,payload.symbol,payload.direction,payload.threshold), "delivery_enabled": False}
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc

@app.delete("/v1/account/alerts")
def account_alert_delete(payload: PriceAlertRequest, owner: str = Depends(principal)):
    try:
        return {"rules": delete_alert(owner,payload.symbol,payload.direction,payload.threshold), "delivery_enabled": False}
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc

@app.middleware("http")
async def private_deployment_gate(request: Request, call_next):
    # Opt-in development API only. A deployed service must authenticate all non-health routes.
    if os.getenv("NEPSE_DEPLOYMENT_MODE") == "private" and request.url.path != "/health":
        try:
            owner = principal(request)
            if request.url.path in {"/v1/ingest/csv","/v1/imports"}:
                if request.headers.get("authorization"):
                    raise HTTPException(401,"Proxy authentication required for ingestion")
                admins = {s.strip() for s in os.getenv("NEPSE_ADMIN_SUBJECTS","").split(",") if s.strip()}
                if owner not in admins:
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"detail":"Administrator required"},status_code=403)
        except HTTPException:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail":"Authentication required"},status_code=401,headers={"Cache-Control":"no-store"})
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Referrer-Policy"]="no-referrer"
    if request.url.path.startswith("/v1/account/"):
        response.headers["Cache-Control"]="no-store"
    return response


@app.get("/v1/research/unified-coverage")
def unified_coverage():
    import json
    import csv
    root = Path(os.getenv("NEPSE_UNIFIED_RESEARCH_DIR", "/srv/private/unified-research"))
    unavailable = {"status":"unavailable","production_eligible":False,"rows":[]}
    try:
        summary = json.loads((root/"summary.json").read_text())
        if summary.get("production_eligible") is not False or summary.get("symbols") != 281:
            return dict(unavailable,reason="invalid_research_summary")
        with (root/"stock_coverage.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        if len(rows)!=281 or len({r["symbol"] for r in rows})!=281 or any(r.get("production_score") or r.get("action")!="UNKNOWN" or r.get("as_of")!=summary.get("as_of") for r in rows):
            return dict(unavailable,reason="invalid_research_rows")
        fields=("symbol","as_of","historical_rows","contiguous_observed_rows","trend_status","wyckoff_status","volume_status","smc_status","broker_status","broker_net_buy_profiles","broker_net_sell_profiles","relative_strength_status","sector_status","liquidity_status")
        return {"status":"archive_research_only","production_eligible":False,
                "independent_validation":False,"summary":summary,
                "rows":[{k:r.get(k) for k in fields} for r in rows]}
    except (OSError,ValueError,TypeError,KeyError):
        return dict(unavailable,reason="research_artifact_missing_or_invalid")

# Mount only the built public frontend, never the repository or raw data.
from fastapi.staticfiles import StaticFiles
import os
_public_frontend = Path(os.environ.get("NEPSE_PUBLIC_FRONTEND", str(Path(__file__).resolve().parents[2] / "frontend" / "public-build")))
if (_public_frontend / "index.html").is_file():
    app.mount("/terminal", StaticFiles(directory=str(_public_frontend), html=True), name="terminal")
