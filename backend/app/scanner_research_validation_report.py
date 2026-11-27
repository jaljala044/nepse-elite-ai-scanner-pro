"""Integrated OOS comparison, signal audit and execution-quality diagnostics."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from app.scanner_portfolio_outcome_orchestrator import run_portfolio_outcome_comparison
from app.scanner_trade_audit import build_trade_audit_report
from app.scanner_strategy_selection import select_six_strategies

def _d(value):
    try: number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError): return None
    return number if number.is_finite() else None

def _execution_diagnostics(audit):
    groups = {}
    for row in audit.get("signals", []):
        key = (row.get("strategy_id"), row.get("horizon"))
        group = groups.setdefault(key, {"closed": [], "pending": 0, "rejected": 0, "unmatched": 0})
        if row.get("status") == "closed_trade":
            group["closed"].append(row)
        elif row.get("status") == "settlement_or_data_pending":
            group["pending"] += 1
        elif row.get("status") == "rejected_by_replay":
            group["rejected"] += 1
        else:
            group["unmatched"] += 1
    reports = []
    for (strategy, horizon), group in sorted(groups.items()):
        trades = group["closed"]
        mfe = [_d(t.get("max_favorable_excursion_pct")) for t in trades]
        mae = [_d(t.get("max_adverse_excursion_pct")) for t in trades]
        mfe = [x for x in mfe if x is not None]
        mae = [x for x in mae if x is not None]
        locked = sum(t.get("stop_triggered_during_lock") is True for t in trades)
        reports.append({
            "strategy_id": strategy, "horizon": horizon,
            "closed_trade_count": len(trades),
            "pending_count": group["pending"], "rejected_count": group["rejected"],
            "unmatched_count": group["unmatched"],
            "stop_triggered_during_settlement_lock_count": locked,
            "average_max_favorable_excursion_pct": str(sum(mfe, Decimal("0")) / len(mfe)) if mfe else None,
            "average_max_adverse_excursion_pct": str(sum(mae, Decimal("0")) / len(mae)) if mae else None,
            "excursion_coverage_count": min(len(mfe), len(mae)),
        })
    return reports

def build_research_validation_report(*, replay_bundle, signals, fold_results,
    portfolio_config=None, minimum_total_trades=30, minimum_folds=3,
    maximum_drawdown_pct="25"):
    """One auditable OOS report; never converts incomplete evidence into a winner."""
    if not isinstance(replay_bundle, dict) or not isinstance(replay_bundle.get("runs"), list):
        raise ValueError("replay_bundle_with_runs_required")
    if not isinstance(signals, list): raise ValueError("signals_must_be_list")
    if not isinstance(fold_results, list): raise ValueError("fold_results_must_be_list")
    # This report is the final holdout assessment; training/validation are not accepted.
    if any(not isinstance(s, dict) or s.get("sample_partition") != "out_of_sample" for s in signals):
        raise ValueError("all_signals_must_be_explicit_out_of_sample")
    if any(not isinstance(r, dict) or r.get("partition") != "out_of_sample" for r in replay_bundle["runs"]):
        raise ValueError("all_replay_runs_must_be_out_of_sample")
    if any(not isinstance(f, dict) or f.get("partition") != "out_of_sample" for f in fold_results):
        raise ValueError("all_fold_results_must_be_out_of_sample")
    comparison = run_portfolio_outcome_comparison(
        replay_bundle=replay_bundle, signals=signals, partition="out_of_sample",
        portfolio_config=portfolio_config)
    audit = build_trade_audit_report(replay_bundle=replay_bundle, signals=signals,
        partition="out_of_sample")
    selection = select_six_strategies(portfolio_comparison=comparison,
        fold_results=fold_results, minimum_total_trades=minimum_total_trades,
        minimum_folds=minimum_folds, maximum_drawdown_pct=maximum_drawdown_pct)
    return {
        "schema_version": "nepse-integrated-research-validation-1.0.0",
        "partition": "out_of_sample",
        "portfolio_comparison": comparison,
        "trade_audit": audit,
        "execution_diagnostics": _execution_diagnostics(audit),
        "strategy_selection": selection,
        "selection_summary": {
            "horizon_winners": selection["best_strategy_by_horizon"],
            "eligible_strategy_horizon_count": sum(x["eligible_for_selection"] for x in selection["candidates"]),
            "missing_portfolio_pairs": selection["portfolio_pairs_missing"],
        },
        "policy": "OOS-only; identical replay assumptions; missing and unmatched outcomes remain explicit; selection requires portfolio metrics and stable walk-forward folds",
        "performance_claimed": False, "probabilities_calibrated": False,
        "production_enabled": False,
        "limitations": [
            "The report is only as reliable as supplied point-in-time signals, bars, fills and fold construction.",
            "Excursion metrics are observed replay MFE/MAE, not achievable exit prices.",
            "Settlement lock, circuits, partial fills, market impact and full portfolio mark-to-market require separate execution models.",
            "No live NEPSE dataset is bundled; this module does not establish real-world accuracy or live recommendations.",
        ],
    }
