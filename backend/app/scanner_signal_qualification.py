"""Evidence-weighted, fail-closed scanner signal qualification.

This is a research decision layer, not an order router or calibrated predictor.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

WEIGHTS={"wyckoff":25,"minervini":25,"relative_strength":15,"broker_footprint":10,"vsa":10,"liquidity":5,"sector":5,"smc":5}
HORIZONS={"t_plus_2":21,"swing":40,"positional":60,"investment":120}

def _time(value):
    if not isinstance(value,str): return None
    try: d=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if d.tzinfo is None or d.utcoffset() is None: return None
    return d.astimezone(timezone.utc)

def _num(value):
    try:
        x=Decimal(str(value))
        return x if x.is_finite() else None
    except (InvalidOperation,TypeError,ValueError): return None

def qualify_scanner_signal(*, symbol, decision_time, horizon, component_evidence,
    gates, trade_plan, minimum_coverage=Decimal("0.80"), minimum_score=Decimal("80")):
    if horizon not in HORIZONS: raise ValueError("unsupported_horizon")
    cutoff=_time(decision_time)
    if cutoff is None: raise ValueError("decision_time_must_be_timezone_aware")
    if not isinstance(symbol,str) or not symbol.strip(): raise ValueError("symbol_required")
    components=component_evidence if isinstance(component_evidence,dict) else {}
    accepted={}; covered=Decimal("0"); weighted=Decimal("0"); errors=[]
    for name,weight in WEIGHTS.items():
        item=components.get(name)
        if not isinstance(item,dict): continue
        score=_num(item.get("score")); available=_time(item.get("available_at"))
        if score is None or not 0<=score<=100 or not item.get("source_id") or not item.get("evidence_id") or available is None or available>cutoff or item.get("status")!="verified":
            errors.append(name+":score_or_evidence_invalid")
            continue
        accepted[name]={"score":str(score),"weight":weight,"source_id":item["source_id"],"evidence_id":item["evidence_id"]}
        covered+=Decimal(weight); weighted+=score*weight
    coverage=covered/Decimal(100)
    score=(weighted/covered) if covered else None
    gate_names=("market","sector","broker","liquidity","execution","corporate_actions","source_quality")
    gate_failures=[]
    for name in gate_names:
        g=(gates or {}).get(name) if isinstance(gates,dict) else None
        if not isinstance(g,dict) or g.get("status")!="verified" or not g.get("source_id") or not g.get("evidence_id") or not _time(g.get("available_at")) or _time(g.get("available_at"))>cutoff:
            gate_failures.append(name)
    plan=trade_plan if isinstance(trade_plan,dict) else {}
    entry,stop,t1=(_num(plan.get(k)) for k in ("entry","stop","T1"))
    plan_errors=[]
    if entry is None or stop is None or t1 is None or not (0<stop<entry<t1): plan_errors.append("valid_entry_stop_T1_required")
    costs=_num(plan.get("round_trip_cost_pct")); slip=_num(plan.get("slippage_pct"))
    if costs is None or slip is None or costs<0 or slip<0 or costs+slip>=100: plan_errors.append("explicit_cost_and_slippage_required")
    rr=None
    if not plan_errors:
        rate=(costs+slip)/100
        loss=entry-stop+(entry+stop)*rate/2
        reward=t1-entry-(t1+entry)*rate/2
        rr=reward/loss if loss>0 else None
        if rr is None or rr<2: plan_errors.append("net_T1_reward_risk_below_2")
    coverage_ok=coverage>=Decimal(str(minimum_coverage))
    score_ok=score is not None and score>=Decimal(str(minimum_score))
    ready=not gate_failures and not plan_errors and not errors and coverage_ok and score_ok
    action="BUY" if ready else "NO_TRADE"
    return {"symbol":symbol,"horizon":horizon,"decision_time":cutoff.isoformat(),
      "status":"qualified_for_human_review" if ready else "not_qualified",
      "action":action,"overall_score":str(score) if score is not None else None,
      "score_coverage_pct":str(coverage*100),"component_scores":accepted,
      "missing_or_rejected_component_evidence":errors,"gate_failures":gate_failures,
      "trade_plan":{"entry":str(entry) if entry is not None else None,"stop":str(stop) if stop is not None else None,
        "T1":str(t1) if t1 is not None else None,"net_reward_risk":str(rr) if rr is not None else None,
        "T2":plan.get("T2"),"T3":plan.get("T3"),"invalidation":plan.get("invalidation")},
      "trade_plan_errors":plan_errors,"coverage_passed":coverage_ok,"score_threshold_passed":score_ok,
      "production_recommendations_enabled":False,"production_promotion_allowed":False,
      "limitations":["BUY means research qualification for human review only, not an order or guaranteed executable trade.",
       "Weights are inherited research weights and are not empirically calibrated.",
       "Probabilities, live fills, settlement availability and portfolio-level exposure are not inferred.",
       "Horizon bar counts are minimum evidence requirements, not predictive calibration."]}
