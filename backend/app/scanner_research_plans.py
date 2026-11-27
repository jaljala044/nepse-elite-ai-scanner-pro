"""Experimental shared level rule; not method-specific execution advice."""
from decimal import Decimal
from .six_scanner_pipeline import run_six_scanners

def attach_reference_plans(result,rows):
    if result["status"]!="RESEARCH": return result
    n={"T+2":20,"swing":60,"positional":126,"investment":252}[result["horizon"]]
    if len(rows)<=n or result["horizon"]=="investment": return result
    bars=sorted(rows,key=lambda r:r["date"])
    entry=Decimal(str(bars[-1]["close"]))
    prior=bars[-n-1:-1]
    stop=min(Decimal(str(r["low"])) for r in prior)
    targets=sorted({Decimal(str(r["high"])) for r in prior if Decimal(str(r["high"]))>entry})[:3]
    if not targets or not 0<stop<entry or (targets[0]-entry)/(entry-stop)<2: return result
    for name,review in result["reviews"].items():
        if review["direction"]=="BULLISH":
            review["plan"]=dict(entry=str(entry),stop=str(stop),T1=str(targets[0]),T2=str(targets[1]) if len(targets)>1 else None,T3=str(targets[2]) if len(targets)>2 else None,reward_risk=str((targets[0]-entry)/(entry-stop)),execution_eligible=False,classification="shared_historical_level_proxy")
    return result

def replay_research(decision_inputs):
    seen=set(); results=[]
    for inputs in decision_inputs:
        key=(inputs["symbol"],inputs["horizon"],inputs["decision_time"])
        if key in seen: raise ValueError("duplicate_decision")
        seen.add(key)
        results.append(attach_reference_plans(run_six_scanners(**inputs),inputs["rows"]))
    return dict(reviews=results,decision_count=len(results),accuracy=None,production_eligible=False)
