"""Project-authored proxies, NOT original IDPAT rules."""
from decimal import Decimal
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available
import hashlib,json

def register_plan(plan,assessment_time):
    values=[Decimal(str(plan[k])) for k in ("entry_low","entry_high","stop","target_low","target_high")]
    if any(not v.is_finite() or v<=0 for v in values): raise ValueError("invalid_price")
    lo,hi,stop,tl,th=values
    if not stop<lo<=hi<tl<=th: raise ValueError("invalid_long_plan")
    eligible=False
    try:
        _available(plan,_time(assessment_time),"plan")
        eligible=_time(plan["published_at"])<=_time(plan["available_at"])
    except (ValueError,KeyError,TypeError): pass
    return dict(plan_id=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest(),plan=plan,
        midpoint_rr=str(((tl+th)/2-(lo+hi)/2)/((lo+hi)/2-stop)),timestamp_gate_passed=eligible,
        backtest_eligible=False)

def research_events(rows,assessment_time):
    now=_time(assessment_time)
    if len(rows)<21: return dict(status="UNKNOWN",events=[],score=None)
    dates=[]; bars=[]
    for r in rows:
        _available(r,now,"bar")
        d=_time(r["observed_at"])
        if d>_time(r["available_at"]) or (dates and d<=dates[-1]): raise ValueError("invalid_bar_chronology")
        dates.append(d)
        o,h,l,c,v=[Decimal(str(r[k])) for k in ("open","high","low","close","volume")]
        if any(not x.is_finite() for x in (o,h,l,c,v)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<=0: raise ValueError("invalid_bar")
        bars.append((o,h,l,c,v))
    if len({r.get("price_basis") for r in rows})!=1 or not rows[0].get("price_basis"): raise ValueError("mixed_price_basis")
    prior=bars[-21:-1]; o,h,l,c,v=bars[-1]
    support=min(b[2] for b in prior); resistance=max(b[1] for b in prior)
    avg=sum(b[4] for b in prior)/20; ratio=v/avg
    events=[]
    if l<support<c: events.append("SHAKEOUT_PROXY")
    if h>resistance>c: events.append("FAILED_BREAKOUT_PROXY")
    if c>resistance and ratio>=Decimal("1.5"): events.append("BREAKOUT_PROXY")
    if ratio>=2 and h>l and abs(c-o)/(h-l)<=Decimal(".3"): events.append("HIGH_VOLUME_SMALL_BODY_PROXY")
    return dict(status="EXPERIMENTAL",events=events,levels=dict(support=str(support),resistance=str(resistance)),volume_ratio=str(ratio),
        original_idpat=dict(OPR=None,OPS=None,SOS=None,SOR=None,hidden_levels=None),score=None,production_eligible=False,
        limitations=["Caller-attested bars; calendar completeness and outcome calibration not established."])
