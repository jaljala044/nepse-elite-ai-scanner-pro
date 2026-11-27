"""Matched candidate universe; no portfolio ranking."""
from .scanner_common_cohort import METHODS
from .scanner_execution_comparison import compare_scanners

def matched_execution(candidates,scenario_inputs):
    if set(candidates)!=set(METHODS): raise ValueError("six_scanners_required")
    def keys(signals):
        result=[(s["symbol"],s["horizon"],s["details"]["decision_date"]) for s in signals]
        if len(result)!=len(set(result)): raise ValueError("duplicate_decision")
        return set(result)
    universe=keys(candidates[METHODS[0]])
    if any(keys(candidates[m])!=universe for m in METHODS): raise ValueError("unmatched_decision_universe")
    result=compare_scanners(candidates,scenario_inputs)
    return dict(result,matched_decisions=len(universe),coverage={m:result["scanners"][m]["summary"]["completed_scenarios"] for m in METHODS},portfolio_metrics=None)
