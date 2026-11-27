"""Connect portfolio-level OOS outcomes with fold stability before selecting a strategy."""
from decimal import Decimal, InvalidOperation
from app.scanner_walk_forward_diagnostics import diagnose_walk_forward_folds
from app.scanner_strategy_lab import HORIZONS, STRATEGIES

def _d(value):
    try: n=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): return None
    return n if n.is_finite() else None

def _portfolio_metrics(portfolio):
    closed=portfolio.get("closed_positions")
    if not isinstance(closed,list): return None
    returns=[]
    wins=losses=Decimal("0")
    for trade in closed:
        if not isinstance(trade,dict): return None
        ret=_d(trade.get("net_return_pct")); pnl=_d(trade.get("net_pnl"))
        if ret is None or pnl is None: return None
        returns.append(ret)
        if pnl>0: wins+=pnl
        elif pnl<0: losses+=abs(pnl)
    expectancy=sum(returns,Decimal("0"))/len(returns) if returns else None
    pf=(wins/losses if losses else (Decimal("Infinity") if wins else None))
    dd=_d(portfolio.get("max_realized_equity_drawdown_pct"))
    return {"closed_trade_count":len(returns),"expectancy_net_pct_per_trade":expectancy,
            "profit_factor":pf,"max_drawdown_pct":dd}

def select_six_strategies(*, portfolio_comparison, fold_results,
                          minimum_total_trades=30, minimum_folds=3,
                          maximum_drawdown_pct="25"):
    if not isinstance(portfolio_comparison,dict) or not isinstance(portfolio_comparison.get("portfolios"),list):
        raise ValueError("portfolio_comparison_required")
    if portfolio_comparison.get("partition")!="out_of_sample":
        raise ValueError("selection_requires_out_of_sample_portfolio_comparison")
    portfolio_rows=[]; seen=set(); rejected=[]
    for item in portfolio_comparison["portfolios"]:
        if not isinstance(item,dict): continue
        strategy,horizon=item.get("strategy_id"),item.get("horizon")
        key=(strategy,horizon)
        if strategy not in STRATEGIES or horizon not in HORIZONS or key in seen:
            rejected.append({"strategy_id":strategy,"horizon":horizon,"reason":"invalid_or_duplicate_portfolio"})
            continue
        seen.add(key)
        p=item.get("portfolio")
        if not isinstance(p,dict): rejected.append({"strategy_id":strategy,"horizon":horizon,"reason":"portfolio_missing"}); continue
        metrics=_portfolio_metrics(p)
        if metrics is None: rejected.append({"strategy_id":strategy,"horizon":horizon,"reason":"closed_trade_metrics_incomplete"}); continue
        pf=metrics["profit_factor"]
        portfolio_rows.append({"strategy_id":strategy,"horizon":horizon,
            "closed_trade_count":metrics["closed_trade_count"],
            "expectancy_net_pct_per_trade":str(metrics["expectancy_net_pct_per_trade"]) if metrics["expectancy_net_pct_per_trade"] is not None else None,
            "profit_factor":"infinity" if pf is not None and pf.is_infinite() else (str(pf) if pf is not None else None),
            "max_drawdown_pct":str(metrics["max_drawdown_pct"]) if metrics["max_drawdown_pct"] is not None else None})
    fold=diagnose_walk_forward_folds(fold_results=fold_results,
        minimum_total_trades=minimum_total_trades,minimum_folds=minimum_folds,
        maximum_fold_drawdown_pct=maximum_drawdown_pct)
    fold_by_key={(x["strategy_id"],x["horizon"]):x for x in fold["results"]}
    portfolio_by_key={(x["strategy_id"],x["horizon"]):x for x in portfolio_rows}
    candidates=[]
    for key,p in portfolio_by_key.items():
        f=fold_by_key.get(key)
        expectancy=_d(p["expectancy_net_pct_per_trade"])
        pf=p["profit_factor"]
        pf_ok=(pf=="infinity" or (_d(pf) is not None and _d(pf)>=1))
        dd=_d(p["max_drawdown_pct"])
        portfolio_ok=(p["closed_trade_count"]>=minimum_total_trades and expectancy is not None
            and expectancy>0 and pf_ok and dd is not None and _d(maximum_drawdown_pct) is not None
            and dd<=_d(maximum_drawdown_pct))
        stable=bool(f and f["eligible_for_selection"])
        candidates.append({"strategy_id":key[0],"horizon":key[1],
            "portfolio_gate_passed":portfolio_ok,"fold_stability_passed":stable,
            "eligible_for_selection":portfolio_ok and stable,
            "portfolio_metrics":p,
            "fold_median_expectancy_net_pct_per_trade":f["median_fold_expectancy_net_pct_per_trade"] if f else None,
            "fold_count":f["fold_count"] if f else 0,
            "selection_status":"eligible" if portfolio_ok and stable else "blocked_by_portfolio_or_fold_gate"})
    winners={}
    for horizon in HORIZONS:
        options=[x for x in candidates if x["horizon"]==horizon and x["eligible_for_selection"]]
        options.sort(key=lambda x:(_d(x["fold_median_expectancy_net_pct_per_trade"]),
            x["fold_count"],x["portfolio_metrics"]["closed_trade_count"]),reverse=True)
        winners[horizon]=({"strategy_id":options[0]["strategy_id"],
            "basis":"median OOS fold expectancy after portfolio-level sample, expectancy, PF and drawdown gates"}
            if options else None)
    expected={(s,h) for s in STRATEGIES for h in HORIZONS}
    return {"schema_version":"nepse-six-strategy-selection-1.0.0",
        "partition":"out_of_sample","strategy_count":len(STRATEGIES),"horizon_count":len(HORIZONS),
        "portfolio_pairs_observed":len(portfolio_by_key),"portfolio_pairs_missing":len(expected-set(portfolio_by_key)),
        "candidates":candidates,"best_strategy_by_horizon":winners,
        "fold_diagnostics":fold,"rejected_portfolios":rejected,
        "policy":"a strategy is eligible only when both portfolio-level OOS metrics and all-fold walk-forward stability pass; absent data is never neutral",
        "performance_claimed":False,"probabilities_calibrated":False,"production_enabled":False}
