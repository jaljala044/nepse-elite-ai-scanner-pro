"""Research-only sector rotation from normalized cohort observations."""
from decimal import Decimal
import hashlib,json
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available
from .scanner_broker_memory_bridge import review_cohort

def sector_rotation(*,records,memberships,previous_sessions,current_sessions,cohort,decision_time):
    cutoff=_time(decision_time)
    old,new=list(previous_sessions),list(current_sessions)
    if not old or len(old)!=len(new) or old+new!=sorted(set(old+new)) or new[-1]>cutoff.date().isoformat(): raise ValueError("invalid_windows")
    if not cohort or len(set(cohort))!=len(cohort): raise ValueError("invalid_cohort")
    mapping={}
    for m in memberships:
        _available(m,cutoff,"membership")
        if _time(m["available_at"]).date().isoformat()>=old[0] or m["symbol"] in mapping: raise ValueError("membership_not_frozen")
        mapping[m["symbol"]]=m["sector"]
    if not mapping: raise ValueError("empty_universe")
    seen=set(); totals={}
    for r in records:
        _available(r,cutoff,"flow")
        key=(r["symbol"],r["session"])
        if key in seen or key[0] not in mapping or key[1] not in old+new or set(r["broker_ids"])!=set(cohort): raise ValueError("flow_identity")
        if r.get("coverage_complete") is not True: continue
        b,s=(Decimal(str(r[k])) for k in ("buy_turnover","sell_turnover"))
        if any(not x.is_finite() or x<0 for x in (b,s)): raise ValueError("invalid_flow")
        seen.add(key)
        pair=totals.setdefault((mapping[key[0]],int(key[1] in new)),[Decimal(0),Decimal(0)])
        pair[0]+=b;pair[1]+=s
    expected={(s,d) for s in mapping for d in old+new}
    if seen!=expected: return dict(status="UNKNOWN",missing=sorted(expected-seen),sectors=[],production_eligible=False)
    sectors=[]
    for sector in sorted(set(mapping.values())):
        a,b=totals[sector,0],totals[sector,1]
        sectors.append(dict(sector=sector,previous_net=str(a[0]-a[1]),current_net=str(b[0]-b[1]),imbalance_change=str((b[0]-b[1])/sum(b)-(a[0]-a[1])/sum(a)) if sum(a) and sum(b) else None))
    return dict(status="RESEARCH",sectors=sectors,production_eligible=False)

def freeze_pattern(*,cohort_inputs):
    review=review_cohort(**cohort_inputs)
    if review["missing_sessions"]: return []
    result=[]
    for h in review["histories"]:
        if not h["observations"]: continue
        last=h["observations"][-1]
        for flag in last["flags"]:
            if flag not in ("ACCUMULATION_PATTERN","DISTRIBUTION_PATTERN"): continue
            payload=dict(symbol=h["symbol"],pattern=flag,decision_time=cohort_inputs["decision_time"],available_at=cohort_inputs["decision_time"],status="verified",source_id=review["selection_source"],broker_numbers=h["broker_numbers"],observation_sources=[x["source_id"] for x in h["observations"]])
            result.append(dict(payload,signal_id=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()))
    return result
