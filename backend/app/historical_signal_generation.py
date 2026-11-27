"""Historical strategy-to-trade-plan signal generation with fail-closed risk gates.

Consumes point-in-time feature-series output and independently supplied,
trusted per-decision gate/level/execution evidence. It does not invent levels.
"""
from __future__ import annotations
from datetime import datetime,timezone\nimport hashlib
from decimal import Decimal,InvalidOperation
from app.scanner_trade_plan import build_evidence_backed_trade_plan
from app.scanner_risk_engine import calculate_risk_limited_position,evaluate_execution_constraints
from app.scanner_strategy_lab import STRATEGIES

REQUIRED_GATES=("market","sector","broker","liquidity","execution","corporate_actions","source_quality")

def _time(v):
    if not isinstance(v,str): return None
    try: d=datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError: return None
    if d.tzinfo is None or d.utcoffset() is None: return None
    return d.astimezone(timezone.utc)

def _d(v):
    try: x=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError): return None
    return x if x.is_finite() else None

def generate_historical_research_signals(*,feature_series,signal_contexts,minimum_score=Decimal("80"),minimum_coverage_pct=Decimal("95")):
    if not isinstance(feature_series,dict) or not isinstance(feature_series.get("snapshots"),list): raise ValueError("historical_feature_series_required")
    if not isinstance(signal_contexts,dict): raise ValueError("signal_contexts_must_be_mapping")
    min_score=_d(minimum_score); min_cov=_d(minimum_coverage_pct)
    if min_score is None or min_cov is None or not 0<=min_score<=100 or not 0<=min_cov<=100: raise ValueError("invalid_thresholds")
    signals=[]; withheld=[]
    for snap in feature_series["snapshots"]:
        cutoff=_time(snap.get("decision_time"))
        if cutoff is None: withheld.append({"reason":"snapshot_decision_time_invalid"}); continue
        for symbol,strategy_map in snap.get("feature_series",{}).items():
            for strategy_id,strategy_data in strategy_map.items():
                if strategy_id not in STRATEGIES: continue
                for horizon,q in strategy_data.get("qualification_by_horizon",{}).items():
                    key="|".join((cutoff.isoformat(),symbol,strategy_id,horizon))
                    ctx=signal_contexts.get(key)
                    if not isinstance(ctx,dict):
                        withheld.append({"key":key,"reason":"trade_context_missing"}); continue
                    score=_d(q.get("score")); coverage=_d(q.get("evidence_coverage_pct"))
                    failures=[]
                    if q.get("status")!="research_ranked": failures.append("strategy_not_research_ranked")
                    if score is None or score<min_score: failures.append("strategy_score_below_threshold")
                    if coverage is None or coverage<min_cov: failures.append("feature_coverage_below_threshold")
                    gates=ctx.get("gates") if isinstance(ctx.get("gates"),dict) else {}
                    for name in REQUIRED_GATES:
                        g=gates.get(name)
                        if not isinstance(g,dict) or g.get("status")!="verified" or not g.get("source_id") or not g.get("evidence_id") or _time(g.get("available_at")) is None or _time(g.get("available_at"))>cutoff:
                            failures.append("gate_unverified:"+name)
                    costs=ctx.get("round_trip_cost_pct"); slip=ctx.get("slippage_pct")
                    plan=build_evidence_backed_trade_plan(symbol=symbol,horizon=horizon,decision_time=cutoff.isoformat(),levels=ctx.get("levels",{}),round_trip_cost_pct=costs,slippage_pct=slip)
                    if plan.get("status")!="research_plan_ready_for_human_review": failures.extend(["trade_plan_unavailable"]+plan.get("errors",[]))
                    ex=ctx.get("execution_snapshot")
                    if isinstance(ex,dict):
                        execution=evaluate_execution_constraints(**ex)
                    else: execution={"status":"blocked","failures":["execution_snapshot_missing"]}
                    if execution.get("status")!="execution_checks_passed_for_human_review": failures.extend(["execution_blocked"]+execution.get("failures",[]))
                    sizing={"status":"blocked","quantity":0,"reason":"risk_inputs_missing"}
                    if not failures:
                        ri=ctx.get("risk_inputs")
                        if isinstance(ri,dict):
                            params=dict(ri); params.setdefault("entry_price",plan["entry"]["high"]); params.setdefault("structural_stop",plan["stop"]["price"])
                            params.setdefault("round_trip_cost_pct",costs); params.setdefault("slippage_pct",slip)
                            sizing=calculate_risk_limited_position(**params)
                        if sizing.get("status")!="sized_for_human_review": failures.append("position_sizing_blocked")
                    signal_id=hashlib.sha256("|".join((symbol,strategy_id,horizon,cutoff.isoformat())).encode("utf-8")).hexdigest()\n                    signal={"signal_id":signal_id,"symbol":symbol,"strategy_id":strategy_id,"horizon":horizon,"decision_time":cutoff.isoformat(),"as_of_session":snap.get("as_of_session"),"strategy_score":str(score) if score is not None else None,"feature_coverage_pct":str(coverage) if coverage is not None else None,"plan":plan,"execution":execution,"position_sizing":sizing,"liquidity_quantity_cap":sizing.get("quantity_caps",{}).get("liquidity_adv"),"action":"RESEARCH_BUY_FOR_HUMAN_REVIEW" if not failures else "NO_TRADE","qualification_failures":failures,"evidence_clusters":q.get("accepted_evidence_clusters",{}),"production_enabled":False}
                    signals.append(signal)
    return {"schema_version":"nepse-historical-research-signals-1.0.0","status":"generated_with_withheld" if withheld else "generated","signal_count":len(signals),"research_buy_count":sum(s["action"]=="RESEARCH_BUY_FOR_HUMAN_REVIEW" for s in signals),"no_trade_count":sum(s["action"]=="NO_TRADE" for s in signals),"signals":signals,"withheld":withheld,"signal_tracking_log":[{"symbol":s["symbol"],"strategy_id":s["strategy_id"],"horizon":s["horizon"],"decision_time":s["decision_time"],"action":s["action"],"entry":s["plan"].get("entry"),"stop":s["plan"].get("stop"),"targets":s["plan"].get("targets"),"score":s["strategy_score"],"coverage_pct":s["feature_coverage_pct"],"invalidation":"verified structural stop; re-evaluate on each new as-of snapshot"} for s in signals],"performance_claimed":False,"production_enabled":False,"limitations":["Research BUY is not a live order or guaranteed fill.","Every context key must be built from trusted server-side point-in-time sources.","A passing execution snapshot is not a fill guarantee and must be refreshed at order time.","No portfolio overlap, position netting, circuit queue, partial-fill or exchange order simulation is included.","No live NEPSE history is bundled; performance metrics require licensed validated historical inputs."]}
