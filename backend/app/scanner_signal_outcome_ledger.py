"""Append-only signal/outcome event ledger and horizon-level diagnostics."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal,InvalidOperation

def _d(v):
    try: x=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError): return None
    return x if x.is_finite() else None

def build_signal_outcome_ledger(*,signals,replay_results):
    if not isinstance(signals,list) or not isinstance(replay_results,list):
        raise ValueError("signals_and_replay_results_must_be_lists")
    trades={}; pending=set(); seen=set(); orphaned_trades=[]
    for result in replay_results:
        if not isinstance(result,dict): continue
        for trade in result.get("trades",[]):
            sid=trade.get("source_signal_id")
            if not isinstance(sid,str) or not sid: continue
            if sid in trades: raise ValueError("duplicate_replay_outcome_for_signal")
            trades[sid]=trade
        for item in result.get("pending_exits",[]):
            sid=item.get("source_signal_id")
            if isinstance(sid,str) and sid: pending.add(sid)
    events=[]; outcomes=[]; grouped=defaultdict(list); rejected=[]
    for s in signals:
        if not isinstance(s,dict): rejected.append({"reason":"signal_record_invalid"}); continue
        sid=s.get("signal_id")
        if not isinstance(sid,str) or not sid or sid in seen:
            rejected.append({"signal_id":sid,"reason":"missing_or_duplicate_signal_id"}); continue
        seen.add(sid)
        base={"signal_id":sid,"symbol":s.get("symbol"),"strategy_id":s.get("strategy_id"),
            "horizon":s.get("horizon"),"decision_time":s.get("decision_time"),
            "action":s.get("action"),"strategy_score":s.get("strategy_score"),
            "feature_coverage_pct":s.get("feature_coverage_pct")}
        events.append({"event_type":"SIGNAL_RECORDED","event_id":sid,"payload":base})
        trade=trades.get(sid)
        if trade:
            expected = {
                "symbol": s.get("symbol"), "strategy_id": s.get("strategy_id"),
                "horizon": s.get("horizon"), "decision_time": s.get("decision_time"),
                "feature_snapshot_sha256": s.get("feature_snapshot_sha256"),
            }
            policy_digest = trade.get("replay_policy_sha256")
            if (
                any(not expected[key] or trade.get(key) != expected[key] for key in expected)
                or not isinstance(expected["feature_snapshot_sha256"], str) or len(expected["feature_snapshot_sha256"]) != 64\n                or any(char not in "0123456789abcdef" for char in expected["feature_snapshot_sha256"].lower())\n                or not isinstance(policy_digest, str) or len(policy_digest) != 64
                or any(char not in "0123456789abcdef" for char in policy_digest.lower())
            ):
                rejected.append({"signal_id": sid, "reason": "replay_trade_signal_metadata_mismatch"})
                trades.pop(sid, None)
                trade = None
        if trade:
            reason=trade.get("exit_reason","unknown")
            if reason=="target": label="target_hit"
            elif str(reason).startswith("stop"): label="stop_hit"
            elif reason=="time_exit_close": label="time_exit"
            else: label="other_exit"
            outcome={"signal_id":sid,"outcome":label,"exit_reason":reason,
                "entry_date":trade.get("entry_date"),"exit_date":trade.get("exit_date"),
                "net_return_pct":trade.get("net_return_pct"),
                "max_favorable_excursion_pct":trade.get("max_favorable_excursion_pct"),
                "max_adverse_excursion_pct":trade.get("max_adverse_excursion_pct"),
                "holding_sessions":trade.get("holding_sessions"),
                "feature_snapshot_sha256":trade.get("feature_snapshot_sha256"),
                "replay_policy_sha256":trade.get("replay_policy_sha256")}
        elif s.get("action")=="NO_TRADE":
            outcome={"signal_id":sid,"outcome":"not_executed","reason":"scanner_action_no_trade"}
        elif sid in pending:
            outcome={"signal_id":sid,"outcome":"settlement_or_horizon_pending"}
        else:
            outcome={"signal_id":sid,"outcome":"unmatched_or_rejected","reason":"no_replay_trade_found"}
        outcomes.append(outcome)
        events.append({"event_type":"OUTCOME_ATTACHED","event_id":sid+"|OUTCOME","payload":outcome})
        if outcome["outcome"] in {"target_hit","stop_hit","time_exit","other_exit"}:
            grouped[(s.get("strategy_id"),s.get("horizon"))].append(outcome)
    matched_ids = {item.get("signal_id") for item in outcomes}
    orphaned_trades = [
        {"source_signal_id": sid, "reason": "replay_trade_without_matching_signal"}
        for sid in trades if sid not in matched_ids
    ]
    summaries=[]
    for (strategy,horizon),items in sorted(grouped.items()):
        returns=[_d(x.get("net_return_pct")) for x in items]
        returns=[x for x in returns if x is not None]
        wins=[x for x in returns if x>0]; losses=[x for x in returns if x<0]
        avg=lambda xs: sum(xs,Decimal("0"))/len(xs) if xs else None
        summaries.append({"strategy_id":strategy,"horizon":horizon,"resolved_trade_count":len(items),
            "target_hit_count":sum(x["outcome"]=="target_hit" for x in items),
            "stop_hit_count":sum(x["outcome"]=="stop_hit" for x in items),
            "time_exit_count":sum(x["outcome"]=="time_exit" for x in items),
            "win_rate_pct":str(Decimal(len(wins))/len(returns)*100) if returns else None,
            "average_net_return_pct":str(avg(returns)) if returns else None,
            "average_gain_pct":str(avg(wins)) if wins else None,
            "average_loss_pct":str(avg(losses)) if losses else None,
            "profit_factor":str(sum(wins,Decimal("0"))/abs(sum(losses,Decimal("0")))) if losses else ("infinity" if wins else None),
            "average_mfe_pct":str(avg([x for x in (_d(i.get("max_favorable_excursion_pct")) for i in items) if x is not None])) if any(_d(i.get("max_favorable_excursion_pct")) is not None for i in items) else None,
            "average_mae_pct":str(avg([x for x in (_d(i.get("max_adverse_excursion_pct")) for i in items) if x is not None])) if any(_d(i.get("max_adverse_excursion_pct")) is not None for i in items) else None})
    return {"schema_version":"nepse-signal-outcome-ledger-1.0.0","status":"appended",
        "signal_event_count":sum(event["event_type"] == "SIGNAL_RECORDED" for event in events),"outcome_event_count":len(outcomes),
        "resolved_trade_count":sum(x["outcome"] in {"target_hit","stop_hit","time_exit","other_exit"} for x in outcomes),
        "unresolved_count":sum(x["outcome"] in {"settlement_or_horizon_pending","unmatched_or_rejected"} for x in outcomes),
        "not_executed_count":sum(x["outcome"]=="not_executed" for x in outcomes),
        "events":events,"outcomes":outcomes,"strategy_horizon_summaries":summaries,
        "rejected_signal_records":rejected,"orphaned_replay_trades":orphaned_trades,
        "ledger_policy":"append-only event records; never overwrite original signal payload; outcome attachment is a separate event",
        "limitations":["NO_TRADE outcomes are not labelled as false negatives without a defined counterfactual policy.",
            "Unmatched research signals remain unresolved rather than being silently counted as losses.",
            "MFE/MAE are based on observed replay bars and do not include intraday path beyond OHLC extremes.",
            "No probabilities or accuracy claims are calibrated by this ledger."],
        "performance_claimed":False,"production_enabled":False}
