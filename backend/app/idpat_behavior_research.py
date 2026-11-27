"""Independent project-authored proxies, not original IDPAT definitions."""
from decimal import Decimal
from .idpat_experimental_research import research_events

def review_behavior(rows,assessment_time):
    result=research_events(rows,assessment_time)
    if result["status"]=="UNKNOWN": return result
    b=[{k:Decimal(str(r[k])) for k in ("open","high","low","close","volume")} for r in rows]
    x=b[-1]; span=x["high"]-x["low"]; ratio=Decimal(result["volume_ratio"])
    events=list(result["events"])
    if span>0 and ratio>=2:
        upper=(x["high"]-max(x["open"],x["close"]))/span
        lower=(min(x["open"],x["close"])-x["low"])/span
        if upper>=Decimal(".5"): events.append("UPPER_REJECTION_HIGH_VOLUME_PROXY")
        if lower>=Decimal(".5"): events.append("LOWER_REJECTION_HIGH_VOLUME_PROXY")
    trends={}
    for n in (5,20,60):
        if len(b)<=n: trends[str(n)]=None; continue
        ret=x["close"]/b[-n-1]["close"]-1
        trends[str(n)]=str(ret)
    result.update(events=events,session_window_returns=trends,accumulation_phase=None,distribution_phase=None,
        climax_confirmed=None,limitations=result["limitations"]+["Rejection is not proof of climax or accumulation; windows are bar counts, not verified timeframes."])
    return result
