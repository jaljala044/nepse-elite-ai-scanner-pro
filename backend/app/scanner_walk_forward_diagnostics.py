"""Fold-stability diagnostics for six-strategy walk-forward research.

Selection is withheld unless every sample, expectancy, drawdown and stability gate passes.
"""
from decimal import Decimal, InvalidOperation
from app.scanner_strategy_lab import HORIZONS, STRATEGIES

def _d(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() else None

def diagnose_walk_forward_folds(*, fold_results, minimum_total_trades=30,
                                minimum_folds=3, minimum_profitable_fold_ratio="0.67",
                                maximum_fold_drawdown_pct="25"):
    if not isinstance(fold_results, list):
        raise ValueError("fold_results_must_be_list")
    if isinstance(minimum_total_trades, bool) or not isinstance(minimum_total_trades, int) or minimum_total_trades < 1:
        raise ValueError("minimum_total_trades_invalid")
    if isinstance(minimum_folds, bool) or not isinstance(minimum_folds, int) or minimum_folds < 2:
        raise ValueError("minimum_folds_must_be_at_least_two")
    ratio, max_dd = _d(minimum_profitable_fold_ratio), _d(maximum_fold_drawdown_pct)
    if ratio is None or not (0 < ratio <= 1) or max_dd is None or max_dd <= 0:
        raise ValueError("fold_gate_parameters_invalid")
    grouped, seen = {}, set()
    rejected = []
    for row in fold_results:
        if not isinstance(row, dict) or row.get("partition") != "out_of_sample":
            continue
        strategy, horizon, fold = row.get("strategy_id"), row.get("horizon"), row.get("fold_id")
        if strategy not in STRATEGIES or horizon not in HORIZONS or not isinstance(fold, str) or not fold.strip():
            rejected.append({"reason": "invalid_strategy_horizon_or_fold_id"})
            continue
        key = (strategy, horizon, fold)
        if key in seen:
            raise ValueError("duplicate_strategy_horizon_fold")
        seen.add(key)
        metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        n = metrics.get("closed_trade_count")
        expectancy, pf, dd = (_d(metrics.get("expectancy_net_pct_per_trade")),
                              _d(metrics.get("profit_factor")),
                              _d(metrics.get("max_drawdown_pct")))
        valid_n = isinstance(n, int) and not isinstance(n, bool) and n >= 0
        valid = valid_n and expectancy is not None and pf is not None and dd is not None
        profitable = bool(valid and n > 0 and expectancy > 0 and pf >= 1 and dd <= max_dd)
        grouped.setdefault((strategy, horizon), []).append({
            "fold_id": fold, "closed_trade_count": n if valid_n else None,
            "expectancy_net_pct_per_trade": str(expectancy) if expectancy is not None else None,
            "profit_factor": str(pf) if pf is not None else None,
            "max_drawdown_pct": str(dd) if dd is not None else None,
            "metrics_complete": valid, "profitable_fold": profitable})
    results = []
    for (strategy, horizon), folds in sorted(grouped.items()):
        folds.sort(key=lambda x: x["fold_id"])
        complete = [x for x in folds if x["metrics_complete"]]
        total = sum(x["closed_trade_count"] for x in complete)
        positive = sum(x["profitable_fold"] for x in complete)
        observed_ratio = Decimal(positive) / len(complete) if complete else Decimal("0")
        expectancy_values = sorted(_d(x["expectancy_net_pct_per_trade"]) for x in complete)
        median = (expectancy_values[(len(expectancy_values)-1)//2] + expectancy_values[len(expectancy_values)//2]) / 2 if expectancy_values else None
        stable = (len(complete) >= minimum_folds and total >= minimum_total_trades
                  and observed_ratio >= ratio and all(x["profitable_fold"] for x in complete))
        # Strict all-fold gate is intentional: one weak/failed OOS fold blocks selection.
        results.append({"strategy_id": strategy, "horizon": horizon,
            "fold_count": len(folds), "complete_fold_count": len(complete),
            "total_closed_trade_count": total, "profitable_fold_count": positive,
            "profitable_fold_ratio": str(observed_ratio),
            "median_fold_expectancy_net_pct_per_trade": str(median) if median is not None else None,
            "folds": folds, "eligible_for_selection": stable,
            "selection_status": "stable_candidate" if stable else "insufficient_sample_or_fold_instability"})
    winners = {}
    for horizon in HORIZONS:
        candidates = [x for x in results if x["horizon"] == horizon and x["eligible_for_selection"]]
        candidates.sort(key=lambda x: (_d(x["median_fold_expectancy_net_pct_per_trade"]),
            x["profitable_fold_ratio"], x["total_closed_trade_count"]), reverse=True)
        winners[horizon] = ({"strategy_id": candidates[0]["strategy_id"],
            "basis": "median OOS fold expectancy, fold consistency, then sample size"}
            if candidates else None)
    return {"schema_version": "nepse-walk-forward-fold-diagnostics-1.0.0",
        "partition_used": "out_of_sample", "minimum_total_trades": minimum_total_trades,
        "minimum_folds": minimum_folds, "minimum_profitable_fold_ratio": str(ratio),
        "maximum_fold_drawdown_pct": str(max_dd), "results": results,
        "best_strategy_by_horizon": winners, "rejected_records": rejected,
        "policy": "no winner without untouched OOS folds, adequate sample, positive expectancy, PF >= 1, drawdown within limit and stable profitable folds",
        "limitations": ["Fold metrics must be generated with chronological, embargoed, untouched OOS windows.",
            "Fold trade samples should not overlap; this module validates identifiers, not source chronology.",
            "Profitability and drawdown are historical estimates, not future probabilities."],
        "performance_claimed": False, "production_enabled": False}
