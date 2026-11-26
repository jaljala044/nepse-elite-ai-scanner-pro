"""Research-only long trade geometry. Not an execution or recommendation engine."""
from math import isfinite

def plan_long(entry, stop, objectives, *, eligible=False, horizon="swing"):
    result={"horizon":horizon,"action":"NO TRADE","entry":None,"stop":None,
            "targets":[],"risk_pct":None,"classification":"research_geometry"}
    if horizon not in ("t_plus_2","swing"):
        raise ValueError("unsupported horizon")
    if not eligible:
        return dict(result,status="eligibility_unverified")
    def valid(x):
        return isinstance(x,(float,int)) and not isinstance(x,bool) and isfinite(x) and x>0
    if not valid(entry) or not valid(stop) or stop>=entry:
        return dict(result,status="invalid_geometry")
    if not isinstance(objectives,(list,tuple)) or not all(valid(x) for x in objectives):
        return dict(result,status="invalid_objectives")
    risk=entry-stop
    targets=[{"price":p,"reward_risk":(p-entry)/risk} for p in sorted(set(objectives)) if p>entry][:3]
    return dict(result,entry=entry,stop=stop,targets=targets,risk_pct=100*risk/entry,
                status="geometry_only" if targets and targets[0]["reward_risk"]>=2 else "poor_or_missing_reward_risk",
                missing=["execution_depth","broker_flow","market_sector_confirmation","costs","validated_strategy"],
                invalidation={"condition":"close_below","price":stop})
