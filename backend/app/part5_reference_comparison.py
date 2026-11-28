"""Retrospective price-reference comparison, not executable or point-in-time certified."""
from math import isfinite
from .scanner import quality_errors

def compare_reference_paths(rows, sessions, *, start, end, holding_sessions=5, cost_pct=1.0):
    if type(holding_sessions) is not int or holding_sessions<1 or not isfinite(cost_pct) or cost_pct<0:
        raise ValueError("invalid assumptions")
    if quality_errors(rows) or list(sessions)!=sorted(set(sessions)):
        raise ValueError("invalid bars or calendar")
    indexed={str(r["date"]):r for r in rows}
    days=list(sessions)
    # Quarantine identical adjacent accepted-session signatures, not all same-price bars.
    fields=("open","high","low","close","volume")
    repeated=set()
    for a,b in zip(days,days[1:]):
        if a in indexed and b in indexed and tuple(float(indexed[a][k]) for k in fields)==tuple(float(indexed[b][k]) for k in fields):
            repeated.add(b)
    results={}
    for mode in ("unconditional","momentum20","breakout20"):
        values=[]
        busy=-1
        for i in range(20,len(days)-holding_sessions):
            if not start<=days[i]<=end or days[i+holding_sessions]>end or i<=busy:
                continue
            span=days[i-20:i+holding_sessions+1]
            if any(d not in indexed or d in repeated for d in span):
                continue
            close=float(indexed[days[i]]["close"])
            if mode=="momentum20" and close<=float(indexed[days[i-20]]["close"]):
                continue
            if mode=="breakout20" and close<=max(float(indexed[d]["high"]) for d in days[i-20:i]):
                continue
            entry=float(indexed[days[i+1]]["open"])
            exit=float(indexed[days[i+holding_sessions]]["close"])
            if float(indexed[days[i+1]]["volume"])<=0 or float(indexed[days[i+holding_sessions]]["volume"])<=0:
                continue
            values.append(100*(exit/entry-1)-cost_pct)
            busy=i+holding_sessions
        results[mode]={"n":len(values),"mean_reference_net_pct":sum(values)/len(values) if values else None,
            "positive_pct":100*sum(v>0 for v in values)/len(values) if values else None}
    return {"classification":"retrospective_price_reference_only","production_eligible":False,
            "point_in_time_verified":False,"results":results,"repeated_session_candidates":len(repeated),
            "limitations":["No confirmed fills, settlement, official costs, corporate-action basis or holdout certification.",
                           "Fixed cost deduction is a scenario, not actual charges."]}
