"""Trade-level audit of replayed signals, fills, exits and unresolved cases."""
from __future__ import annotations
from collections import defaultdict

def build_trade_audit_report(*, replay_bundle, signals, partition="out_of_sample"):
    if not isinstance(replay_bundle, dict) or not isinstance(replay_bundle.get("runs"), list):
        raise ValueError("replay_bundle_runs_required")
    if not isinstance(signals, list): raise ValueError("signals_must_be_list")
    if partition not in {"train", "validation", "out_of_sample"}:
        raise ValueError("explicit_partition_required")
    scoped = {}
    for signal in signals:
        if not isinstance(signal, dict) or signal.get("sample_partition") != partition: continue
        sid = signal.get("signal_id")
        if not isinstance(sid, str) or not sid.strip(): continue
        if sid in scoped: raise ValueError("duplicate_signal_id")
        scoped[sid] = signal

    run_reports, matched, pending_ids, rejected_ids = [], set(), set(), set()
    global_trades = []
    for run in replay_bundle["runs"]:
        if not isinstance(run, dict) or run.get("partition") != partition: continue
        strategy, horizon = run.get("strategy_id"), run.get("horizon")
        trades = run.get("trades", [])
        pending = run.get("pending_exits", [])
        rejected = run.get("rejected_signals", [])
        if not all(isinstance(x, list) for x in (trades, pending, rejected)):
            raise ValueError("replay_run_trade_collections_invalid")
        run_ids = set()
        for trade in trades:
            sid = trade.get("source_signal_id")
            if not isinstance(sid, str) or sid not in scoped: continue
            if sid in run_ids: raise ValueError("duplicate_replay_outcome_for_signal")
            run_ids.add(sid); matched.add(sid); global_trades.append(trade)
        for item in pending:
            sid = item.get("source_signal_id")
            if isinstance(sid, str) and sid in scoped: pending_ids.add(sid)
        for item in rejected:
            sid = item.get("source_signal_id") or item.get("signal_id")
            if isinstance(sid, str) and sid in scoped: rejected_ids.add(sid)
        reasons = [t.get("exit_reason") for t in trades if t.get("source_signal_id") in run_ids]
        closed = len(reasons)
        target = sum(reason == "target" for reason in reasons)
        stop = sum(isinstance(reason, str) and reason.startswith("stop") for reason in reasons)
        run_reports.append({
            "strategy_id": strategy, "horizon": horizon, "partition": partition,
            "closed_trade_count": closed, "target_exit_count": target,
            "stop_exit_count": stop,
            "time_or_other_exit_count": closed - target - stop,
            "target_hit_rate_pct": str(target * 100 / closed) if closed else None,
            "stop_hit_rate_pct": str(stop * 100 / closed) if closed else None,
            "net_positive_trade_count": sum(_positive(t.get("net_return_pct")) for t in trades if t.get("source_signal_id") in run_ids),
            "net_negative_trade_count": sum(_negative(t.get("net_return_pct")) for t in trades if t.get("source_signal_id") in run_ids),
            "pending_exit_count": sum(isinstance(p.get("source_signal_id"), str) and p["source_signal_id"] in scoped for p in pending),
            "rejected_count": len(rejected),
        })
    unresolved = set(scoped) - matched - pending_ids - rejected_ids
    audit_rows = []
    trade_by_id = {t.get("source_signal_id"): t for t in global_trades}
    for sid, signal in sorted(scoped.items()):
        trade = trade_by_id.get(sid)
        if trade:
            status = "closed_trade"
        elif sid in pending_ids:
            status = "settlement_or_data_pending"
        elif sid in rejected_ids:
            status = "rejected_by_replay"
        else:
            status = "no_replay_outcome_unmatched"
        audit_rows.append({"signal_id": sid, "symbol": signal.get("symbol"),
            "strategy_id": signal.get("strategy_id"), "horizon": signal.get("horizon"),
            "decision_time": signal.get("decision_time"), "status": status,
            "entry_date": trade.get("entry_date") if trade else None,
            "entry_price": trade.get("entry_price") if trade else None,
            "exit_date": trade.get("exit_date") if trade else None,
            "exit_price": trade.get("exit_price") if trade else None,
            "exit_reason": trade.get("exit_reason") if trade else None,
            "net_return_pct": trade.get("net_return_pct") if trade else None,
            "stop_triggered_during_lock": trade.get("stop_triggered_during_lock") if trade else None})
    return {
        "schema_version": "nepse-trade-audit-1.0.0", "partition": partition,
        "signal_count": len(scoped), "closed_trade_count": len(matched),
        "pending_signal_count": len(pending_ids), "rejected_signal_count": len(rejected_ids),
        "unmatched_signal_count": len(unresolved), "runs": run_reports, "signals": audit_rows,
        "limitations": ["Entry/target/stop hit rates reflect replay assumptions, not guaranteed live fills.",
            "Unmatched signals are unresolved, not automatically false negatives.",
            "Rejected, pending and closed outcomes must remain separately reported.",
            "Use only the untouched out_of_sample partition for final strategy assessment."],
        "performance_claimed": False, "production_enabled": False,
    }

def _positive(value):
    try: return float(value) > 0
    except (TypeError, ValueError): return False

def _negative(value):
    try: return float(value) < 0
    except (TypeError, ValueError): return False
