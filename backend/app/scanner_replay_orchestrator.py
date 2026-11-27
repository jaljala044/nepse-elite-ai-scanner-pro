"""Common-input replay coordinator for six strategies and four horizons.

The coordinator evaluates supplied, already-generated point-in-time signals. It
does not generate features/signals or fetch history; missing evidence is blocked.
"""
from __future__ import annotations
from app.scanner_strategy_lab import STRATEGIES
from app.scanner_backtest import replay_strategy_horizon, HOLDING_SESSIONS

def run_six_strategy_replay(*, historical_panel, signals_by_strategy_horizon,
    bars_by_symbol, round_trip_cost_pct, round_trip_slippage_pct,
    sellable_after_sessions=2, partitions=("train", "validation", "out_of_sample")):
    if not isinstance(historical_panel, dict): raise ValueError("historical_panel_required")
    eligible = set(historical_panel.get("eligible_symbols", []))
    panel_status = historical_panel.get("status")
    if panel_status != "validated_for_research" or not eligible:
        return {"schema_version":"nepse-six-strategy-replay-1.0.0","status":"blocked",
            "reason":"historical_panel_not_validated_or_no_eligible_symbols",
            "eligible_symbol_count":len(eligible),"runs":[],"performance_claimed":False,"production_enabled":False}
    if not isinstance(signals_by_strategy_horizon, dict) or not isinstance(bars_by_symbol, dict):
        raise ValueError("signals_and_bars_required")
    if not isinstance(partitions, (tuple, list)) or not partitions or any(p not in {"train","validation","out_of_sample"} for p in partitions):
        raise ValueError("invalid_partitions")
    runs, blocked = [], []
    for strategy_id in STRATEGIES:
        for horizon in HOLDING_SESSIONS:
            key = strategy_id + ":" + horizon
            supplied = signals_by_strategy_horizon.get(key, [])
            if not isinstance(supplied, list):
                blocked.append({"strategy_id":strategy_id,"horizon":horizon,"reason":"signal_batch_invalid"}); continue
            scoped = [s for s in supplied if isinstance(s, dict) and str(s.get("symbol","")).upper() in eligible]
            excluded = len(supplied) - len(scoped)
            for partition in partitions:
                try:
                    result = replay_strategy_horizon(strategy_id=strategy_id,horizon=horizon,
                        signals=[s for s in scoped if s.get("sample_partition")==partition],
                        bars_by_symbol=bars_by_symbol,partition=partition,
                        round_trip_cost_pct=round_trip_cost_pct,
                        round_trip_slippage_pct=round_trip_slippage_pct,
                        sellable_after_sessions=sellable_after_sessions)
                    runs.append({"strategy_id":strategy_id,"horizon":horizon,"partition":partition,
                        "metrics":result["metrics"],"trade_count":len(result["trades"]),
                        "rejected_signals":result["rejected_signals"],"pending_exits":result["pending_exits"],
                        "assumptions":result["assumptions"],"excluded_non_universe_signals":excluded,
                        "status":"replayed" if result["trades"] else "no_eligible_trades"})
                except (ValueError, TypeError) as exc:
                    blocked.append({"strategy_id":strategy_id,"horizon":horizon,
                        "partition":partition,"reason":str(exc)})
    expected = len(STRATEGIES) * len(HOLDING_SESSIONS) * len(partitions)
    return {
        "schema_version":"nepse-six-strategy-replay-1.0.0",
        "status":"completed_with_gaps" if blocked or len(runs) != expected else "completed",
        "strategy_count":len(STRATEGIES),"horizon_count":len(HOLDING_SESSIONS),
        "partition_count":len(partitions),"expected_run_count":expected,
        "completed_run_count":len(runs),"blocked_run_count":len(blocked),
        "runs":runs,"blocked_runs":blocked,
        "comparison_policy":"compare only identical panel, universe, folds, costs, slippage and settlement assumptions; use untouched out_of_sample for selection",
        "performance_claimed":False,"production_enabled":False,
        "limitations":[
            "This orchestrates replay of externally generated signals; it does not calculate scanner features or create signals.",
            "The historical panel must already have passed point-in-time, universe and corporate-action controls.",
            "Empty samples are reported as no_eligible_trades, not as zero-risk or successful strategies.",
            "Replay limitations include simplified fills, no circuit queues, market impact, portfolio overlap or partial fills."
        ]
    }
