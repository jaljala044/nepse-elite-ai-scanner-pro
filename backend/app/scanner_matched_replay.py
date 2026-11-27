"""Matched research cohort; unknown reviews remain in denominator."""
import hashlib,json
from .scanner_research_plans import replay_research
from .scanner_common_cohort import METHODS
from .scanner_direction_outcomes import evaluate_directions
from .independent_scanner_review import resolve_reviews
from .corporate_action_trade_plan import _time

def matched_replay(decisions,paths,assessment_time):
    cutoff=_time(assessment_time)
    ordered=sorted(decisions,key=lambda x:(_time(x["decision_time"]),x["symbol"],x["horizon"]))
    if any(_time(x["decision_time"])>cutoff for x in ordered): raise ValueError("future_decision")
    replay=replay_research(ordered)
    rows=[]
    for inputs,result in zip(ordered,replay["reviews"]):
        key=(inputs["symbol"],inputs["horizon"],inputs["decision_time"])
        if set(result["reviews"])!=set(METHODS): raise ValueError("incomplete_method_set")
        reviews={}
        for name,item in result["reviews"].items():
            payload=dict(item,symbol=key[0],horizon=key[1],available_at=key[2],method=name)
            reviews[name]=dict(payload,review_digest=hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest())
        rows.append(dict(key=key,reviews=reviews,confluence=resolve_reviews({m:reviews[m]["direction"] for m in METHODS if m!="MASTER"})))
    cohort=dict(rows=rows,decision_count=len(rows),production_eligible=False)
    return dict(cohort=cohort,outcomes=evaluate_directions(cohort,paths,assessment_time),production_eligible=False)
