"""Uncalibrated research classifications; never executable recommendations."""
from decimal import Decimal

def classify_candidate(review,*,holding=False,market="UNKNOWN",liquidity="UNKNOWN"):
    direction=review.get("direction","UNKNOWN")
    plan=review.get("plan") or {}
    result=dict(action="NO_TRADE",timing="WAIT",confidence="LOW",production_eligible=False)
    if direction=="UNKNOWN": return dict(result,reason="direction_unavailable")
    if holding and direction=="BEARISH": return dict(result,action="SELL_REVIEW",reason="bearish_evidence_requires_exit_review")
    if holding: return dict(result,action="HOLD_REVIEW",reason="no_confirmed_exit")
    if direction!="BULLISH": return dict(result,reason="no_bullish_setup")
    if market!="FAVORABLE" or liquidity!="ADEQUATE": return dict(result,reason="market_or_liquidity_gate")
    try:
        entry,stop,target=(Decimal(str(plan[k])) for k in ("entry","stop","T1"))
        valid=all(v.is_finite() for v in (entry,stop,target)) and 0<stop<entry<target and (target-entry)/(entry-stop)>=2
    except (KeyError,ValueError,ArithmeticError): valid=False
    if not valid: return dict(result,reason="valid_two_to_one_plan_required")
    return dict(result,action="BUY_REVIEW",timing="WAIT_FOR_CONFIRMATION",reason="experimental_candidate_only")

def method_setup(review,method,as_of_session):
    evidence=review.get("evidence") or {}
    if method=="WYCKOFF":
        events={e["event"] for e in evidence.get("events",[]) if e["session_date"]==as_of_session}
        if events & {"upthrust","sow","lpsy"}: return "SUPPLY_REVIEW"
        if events & {"lps","backup_to_creek"}: return "RETEST_WATCH"
        if "spring" in events: return "EARLY_REVERSAL_WATCH"
        if events & {"sos","jump_across_creek"}: return "BREAKOUT_WATCH"
    if method=="SMC":
        events=[e for e in evidence.get("events",[]) if e.get("date")==as_of_session and e.get("direction","").lower()=="bullish"]
        if any(e.get("type")=="choch" for e in events): return "REVERSAL_WATCH"
        if any(e.get("type")=="bos" for e in events): return "BREAKOUT_WATCH"
    return "UNCLASSIFIED"
