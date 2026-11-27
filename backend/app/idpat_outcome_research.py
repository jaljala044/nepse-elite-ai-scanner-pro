"""Descriptive forward returns only, not simulated fills or original IDPAT performance."""
from decimal import Decimal
from .idpat_behavior_research import review_behavior
from .idpat_experimental_research import research_events

def evaluate_events(rows,assessment_time,horizon=5):
    if type(horizon) is not int or horizon<1: raise ValueError("invalid_horizon")
    if len(rows)<21+horizon: return dict(sample_size=0,mean_returns={},production_eligible=False)
    research_events(rows,assessment_time)
    outcomes={}
    for i in range(20,len(rows)-horizon,horizon):
        decision=rows[i]["available_at"]
        if any(r["available_at"] is None for r in rows[:i+1]): raise ValueError("missing_timestamp")
        review=review_behavior(rows[:i+1],decision)
        ret=Decimal(str(rows[i+horizon]["close"]))/Decimal(str(rows[i]["close"]))-1
        for event in review["events"]: outcomes.setdefault(event,[]).append(ret)
    return dict(sample_size=sum(map(len,outcomes.values())),mean_returns={k:str(sum(v)/len(v)) for k,v in outcomes.items()},
        event_counts={k:len(v) for k,v in outcomes.items()},production_eligible=False,
        limitations=["Event observations may share dates; no verified calendar, costs, fills, benchmark or out-of-sample fitting."])
