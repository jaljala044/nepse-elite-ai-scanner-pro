"""Matched research portfolio scenarios, not verified investment returns."""
from .scanner_common_cohort import METHODS
from .portfolio_backtest import run_portfolio_backtest

def compare_portfolios(*,candidates,common_inputs):
    if set(candidates)!=set(METHODS): raise ValueError("six_scanners_required")
    if "signals" in common_inputs or "scenario_runner" in common_inputs: raise ValueError("common_policy_required")
    universe=None
    for method in METHODS:
        keys=[(s["symbol"],s["horizon"],s["details"]["decision_date"]) for s in candidates[method]]
        if len(keys)!=len(set(keys)): raise ValueError("duplicate_decision")
        if universe is None: universe=set(keys)
        elif set(keys)!=universe: raise ValueError("unmatched_decision_universe")
    results={}
    for method in METHODS:
        signals=candidates[method]
        buys=sum(s.get("action")=="BUY" for s in signals)
        unknown=sum(s.get("action")=="UNKNOWN" for s in signals)
        result=run_portfolio_backtest(signals=signals,**common_inputs)
        results[method]=dict(portfolio=result,buy_count=buys,unknown_count=unknown,other_count=len(signals)-buys-unknown,
            performance_eligible=buys>0 and result["trade_count"]>0 and result["withheld_signal_count"]==0 and unknown==0)
    return dict(methods=results,matched_decisions=len(universe),ranking=None,production_eligible=False,
        limitations=["Shared caller-supplied historical inputs and risk policy.","No independent evidence verification or corporate-action-aware allocation.","Unavailable signals are not evidence of a profitable cash strategy."])
