"""Experimental research only; no original IDPAT or executable recommendation."""
from decimal import Decimal
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available
from .idpat_behavior_research import review_behavior

def broker_persistence(records,sessions,symbol,assessment_time):
    now=_time(assessment_time)
    expected=list(sessions)[-5:]
    if len(expected)!=5 or expected!=sorted(set(expected)): raise ValueError("invalid_sessions")
    by_day={}
    cohort=None
    for r in records:
        _available(r,now,"broker")
        if r["symbol"]!=symbol or _time(r["observed_at"])>_time(r["available_at"]): raise ValueError("invalid_broker")
        day=r["session"]
        if day not in expected or day in by_day: raise ValueError("invalid_broker_session")
        ids=tuple(sorted(set(r["broker_ids"])))
        if not ids or not r.get("coverage_complete") or (cohort is not None and ids!=cohort): return "UNKNOWN"
        cohort=ids
        b,s=(Decimal(str(r[k])) for k in ("buy_turnover","sell_turnover"))
        if any(not v.is_finite() or v<0 for v in (b,s)): raise ValueError("invalid_turnover")
        by_day[day]=(b-s)/(b+s) if b+s else Decimal(0)
    if set(by_day)!=set(expected): return "UNKNOWN"
    values=[by_day[d] for d in expected]
    if all(v>=Decimal(".2") for v in values[-3:]): return "PERSISTENT_BUYING_PROXY"
    if all(v<=Decimal("-.2") for v in values[-3:]): return "PERSISTENT_SELLING_PROXY"
    return "MIXED"

def horizon_review(rows,assessment_time,flow="UNKNOWN"):
    review=review_behavior(rows,assessment_time)
    plans={}
    for name,n in (("T+2",20),("swing",60),("positional",126),("investment",252)):
        result=dict(action="NO_TRADE",entry=None,stop=None,T1=None,T2=None,T3=None,reward_risk=None)
        if review["status"]!="UNKNOWN" and len(rows)>n:
            prior=rows[-n-1:-1]
            entry=Decimal(str(rows[-1]["close"]))
            stop=min(Decimal(str(r["low"])) for r in prior)
            levels=sorted(set(Decimal(str(r["high"])) for r in prior if Decimal(str(r["high"]))>entry))
            result.update(inferred_support=str(stop),inferred_resistance=[str(v) for v in levels[:3]],window_bars=n)
            if name!="investment" and flow=="PERSISTENT_BUYING_PROXY" and levels and stop<entry and (levels[0]-entry)/(entry-stop)>=2:
                result.update(entry=str(entry),stop=str(stop),reward_risk=str((levels[0]-entry)/(entry-stop)),**{"T"+str(i+1):str(v) for i,v in enumerate(levels[:3])})
        plans[name]=result
    return dict(plans=plans,trend=review.get("session_window_returns"),production_eligible=False,limitations=["Bar-count windows and historical highs are uncalibrated proxies; no verified calendar, fundamental investment evidence or execution eligibility."])
