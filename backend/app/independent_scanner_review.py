"""Research review orchestration; never promotes experimental outputs to BUY."""
import hashlib,json
from .idpat_horizon_research import horizon_review,broker_persistence
from .scanner_execution_comparison import compare_scanners

def generate_idpat_review(*,symbol,rows,assessment_time,broker_records,sessions):
    if any(r.get("symbol")!=symbol for r in rows): raise ValueError("mixed_symbols")
    flow=broker_persistence(broker_records,sessions,symbol,assessment_time)
    result=horizon_review(rows,assessment_time,flow)
    payload=dict(symbol=symbol,assessment_time=assessment_time,method="IDPAT_PROXY_V1",broker_flow=flow,result=result)
    return dict(payload,review_id=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())

def resolve_reviews(reviews):
    allowed={"BULLISH","BEARISH","NEUTRAL","UNKNOWN"}
    if any(v not in allowed for v in reviews.values()): raise ValueError("invalid_direction")
    values=set(reviews.values())
    state="CONFLICTING" if {"BULLISH","BEARISH"}<=values else "INCOMPLETE" if not reviews or "UNKNOWN" in values else "ALIGNED" if len(values)==1 else "MIXED"
    return dict(state=state,independent_reviews=reviews,score=None,action="NO_TRADE",production_eligible=False)

def comparison_dashboard(candidates,scenario_inputs):
    result=compare_scanners(candidates,scenario_inputs)
    return dict(result,coverage={k:v["summary"]["completed_scenarios"] for k,v in result["scanners"].items()},ranking=None)
