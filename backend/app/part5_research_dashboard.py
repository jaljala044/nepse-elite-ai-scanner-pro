"""Research-only comparative stress and paper outcome dashboard."""
from math import isfinite
from .performance_statistics import summarize
from .scanner_eligibility import REVIEWED_ROWS

def comparative_readiness(reviewed=None):
    reviewed=REVIEWED_ROWS if reviewed is None else reviewed
    return {"reviewed_row_count":len(reviewed),
            "symbol_count":len({k[0] for k in reviewed}),
            "status":"additional_gates_required" if reviewed else "blocked_no_canonical_rows",
            "backtest_executed":False,"production_eligible":False}

def stress_report(scenarios, *, initial_capital):
    """Compare precomputed scenario trades; does not itself simulate parameter changes."""
    if not scenarios or "baseline" not in scenarios:
        raise ValueError("baseline required")
    results={}
    for name,trades in scenarios.items():
        stats=summarize(trades,initial_capital=initial_capital)
        results[name]=stats
    baseline=results["baseline"]["net_return_pct"]
    for stats in results.values():
        value=stats["net_return_pct"]
        stats["return_delta_vs_baseline_pct_points"]=value-baseline if value is not None and baseline is not None else None
    return {"classification":"hypothetical_research_only","scenarios":results,
            "production_eligible":False,"robustness_proven":False}

def dashboard(trades, *, initial_capital):
    """Per-horizon hypothetical outcomes; never equate trade wins with signal accuracy."""
    horizons=("t_plus_2","swing","positional","investment")
    seen=set()
    for trade in trades:
        key=trade.get("paper_id")
        if not isinstance(key,str) or not key.strip() or key in seen or trade.get("horizon") not in horizons:
            raise ValueError("invalid or duplicate paper trade")
        seen.add(key)
        if trade.get("classification")!="hypothetical_paper_trade":
            raise ValueError("paper classification required")
    return {"classification":"hypothetical_research_only",
            "horizons":{h:summarize([t for t in trades if t["horizon"]==h],initial_capital=initial_capital) for h in horizons},
            "signal_accuracy":None,"production_eligible":False}


def journal_dashboard(envelopes, *, initial_capital):
    """One final outcome per signal; reject conflicting revisions instead of double counting."""
    from .part5_paper_journal import verify_paper_outcome
    from .point_in_time import _aware
    trades=[]
    seen=set()
    for envelope in envelopes:
        if not verify_paper_outcome(envelope):
            raise ValueError("invalid paper envelope")
        record=envelope["record"]
        key=record["signal_id"]
        if key in seen:
            raise ValueError("multiple outcomes for one signal require explicit resolution")
        seen.add(key)
        trades.append({**record["trade"],"paper_id":envelope["paper_id"],
                       "classification":record["classification"],"observed_at":record["observed_at"]})
    trades.sort(key=lambda t:(_aware(t["observed_at"]),t["paper_id"]))
    result=dashboard(trades,initial_capital=initial_capital)
    result["drawdown_basis"]="observation_order_not_mark_to_market"
    return result
