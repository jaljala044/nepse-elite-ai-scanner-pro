"""Out-of-sample comparison of six strategies across four horizons."""
from decimal import Decimal, InvalidOperation
from app.scanner_strategy_lab import HORIZONS, STRATEGIES
DEFAULT_MINIMUM_SAMPLE = 30

def _d(value):
    try: x = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError): return None
    return x if x.is_finite() else None

def compare_strategy_results(*, replay_results, minimum_sample=DEFAULT_MINIMUM_SAMPLE,
                             maximum_drawdown_pct=Decimal("25")):
    if isinstance(minimum_sample, bool) or not isinstance(minimum_sample, int) or minimum_sample < 1:
        raise ValueError("minimum_sample_must_be_positive_integer")
    max_dd = _d(maximum_drawdown_pct)
    if max_dd is None or max_dd <= 0: raise ValueError("maximum_drawdown_pct_must_be_positive")
    rows, seen = [], set()
    for result in replay_results if isinstance(replay_results, list) else []:
        if not isinstance(result, dict) or result.get("partition") != "out_of_sample": continue
        strategy, horizon = result.get("strategy_id"), result.get("horizon")
        if strategy not in STRATEGIES or horizon not in HORIZONS: continue
        key = (strategy, horizon)
        if key in seen: raise ValueError("duplicate_strategy_horizon_result")
        seen.add(key)
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
        n = metrics.get("sample_size", 0)
        expectancy, pf, dd = (_d(metrics.get("expectancy_net_pct_per_trade")),
                              _d(metrics.get("profit_factor")), _d(metrics.get("max_drawdown_pct")))
        eligible = (isinstance(n,int) and not isinstance(n,bool) and n >= minimum_sample
            and expectancy is not None and expectancy > 0 and pf is not None and pf >= 1
            and dd is not None and dd <= max_dd)
        rows.append({"strategy_id":strategy,"strategy_label":STRATEGIES[strategy]["label"],
            "horizon":horizon,"sample_size":n,"win_rate_pct":metrics.get("win_rate_pct"),
            "profit_factor":metrics.get("profit_factor"),
            "expectancy_net_pct_per_trade":metrics.get("expectancy_net_pct_per_trade"),
            "max_drawdown_pct":metrics.get("max_drawdown_pct"),
            "eligible_for_selection":eligible,
            "selection_status":"eligible" if eligible else "insufficient_sample_or_performance_gate_failed"})
    winners = {}
    for horizon in HORIZONS:
        candidates = [r for r in rows if r["horizon"]==horizon and r["eligible_for_selection"]]
        candidates.sort(key=lambda r:(_d(r["expectancy_net_pct_per_trade"]),
            _d(r["profit_factor"]) if _d(r["profit_factor"]) is not None else Decimal("Infinity"),
            -_d(r["max_drawdown_pct"]),r["sample_size"]),reverse=True)
        winners[horizon] = ({"strategy_id":candidates[0]["strategy_id"],
            "strategy_label":candidates[0]["strategy_label"],
            "basis":"out_of_sample_expectancy_then_profit_factor_then_lower_drawdown_then_sample"}
            if candidates else None)
    return {"schema_version":"six-strategy-comparison-1.0.0","partition_used":"out_of_sample",
        "minimum_sample":minimum_sample,"maximum_drawdown_pct":str(max_dd),"results":rows,
        "best_strategy_by_horizon":winners,
        "unscored_strategy_horizons":[{"strategy_id":s,"horizon":h} for s in STRATEGIES for h in HORIZONS if (s,h) not in seen],
        "policy":"no_winner_without_untouched_oos_positive_expectancy_pf_at_least_1_and_drawdown_gate",
        "performance_claimed":False,"production_enabled":False}
