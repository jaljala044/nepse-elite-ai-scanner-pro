"""Research comparison; no ranking from unequal or missing evidence."""
from .scanner_common_cohort import METHODS
from .execution_backtest import aggregate_execution_scenarios
from .corporate_action_trade_plan import _time

def performance_review(cohort,scenarios,*,test_start,assessment_time):
    boundary,cutoff=_time(test_start),_time(assessment_time)
    if boundary>=cutoff: raise ValueError("invalid_boundary")
    seen=set(); buckets={m:{"train":[],"test":[]} for m in METHODS}
    counts={m:{"abstained":0,"unknown":0,"purged":0,"missing":0} for m in METHODS}
    for row in cohort["rows"]:
        key=tuple(row["key"]); decision=_time(key[2])
        if key in seen or decision>cutoff or set(row["reviews"])!=set(METHODS): raise ValueError("invalid_cohort")
        seen.add(key)
        for m in METHODS:
            review=row["reviews"][m]
            if review["direction"]=="UNKNOWN":
                counts[m]["unknown"]+=1; continue
            if review.get("candidate_decision",{}).get("action")!="BUY_REVIEW":
                counts[m]["abstained"]+=1; continue
            scenario=scenarios.get((m,key))
            if not scenario or scenario.get("status")!="scenario_completed":
                counts[m]["missing"]+=1; continue
            end=_time(scenario["outcome_available_at"])
            if end<=decision or end>cutoff or scenario.get("symbol")!=key[0] or scenario.get("horizon")!=key[1]: raise ValueError("invalid_scenario_alignment")
            if decision<boundary<=end:
                counts[m]["purged"]+=1; continue
            buckets[m]["train" if decision<boundary else "test"].append(scenario)
    return dict(decision_count=len(seen),methods={m:dict(counts[m],**{p:aggregate_execution_scenarios(v) for p,v in buckets[m].items()}) for m in METHODS},ranking=None,production_eligible=False,limitations=["Caller supplied scenarios; no independent fill or provenance verification.","Chronological split is not fitted walk-forward validation.","Abstentions and missing outcomes are separate; no portfolio equity curve."])
