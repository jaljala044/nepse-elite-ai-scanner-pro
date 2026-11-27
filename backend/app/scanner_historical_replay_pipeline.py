"""Evidence-gated bridge from historical feature snapshots to six-strategy replay."""
from __future__ import annotations
import hashlib, json
from app.scanner_strategy_lab import STRATEGIES, evaluate_strategy
from app.scanner_replay_orchestrator import run_six_strategy_replay
from app.scanner_backtest import HOLDING_SESSIONS

def _fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def build_historical_research_candidates(*, snapshots, feature_evidence_by_key,
    trade_plans_by_key, partition_by_date, minimum_coverage="0.95"):
    """Evaluate every strategy/horizon; only independently qualified plans become replay signals.

    Keys are '<security_id>|<session_date>'. A strategy score alone never creates a trade.
    """
    if not isinstance(snapshots,list) or not isinstance(feature_evidence_by_key,dict) or not isinstance(trade_plans_by_key,dict):
        raise ValueError("snapshots_evidence_and_trade_plans_required")
    histories={}
    for snap in snapshots:
        if not isinstance(snap,dict) or snap.get("feature_status")!="complete": continue
        histories.setdefault(snap.get("security_id"),[]).append(snap)
    for rows in histories.values(): rows.sort(key=lambda x:x["session_date"])
    evaluations=[]; signals={s+":"+h:[] for s in STRATEGIES for h in HOLDING_SESSIONS}
    withheld=[]
    for sid,rows in sorted(histories.items()):
        for i,snap in enumerate(rows):
            day=snap["session_date"]; key=sid+"|"+day
            evidence=feature_evidence_by_key.get(key,{})
            for strategy_id in STRATEGIES:
                for horizon in HOLDING_SESSIONS:
                    result=evaluate_strategy(strategy_id=strategy_id,symbol=snap.get("symbol") or sid,
                        horizon=horizon,decision_time=snap["decision_cutoff"],
                        history_sessions=i+1,feature_evidence=evidence,minimum_coverage=minimum_coverage)
                    plan=trade_plans_by_key.get(key,{}).get(strategy_id,{}).get(horizon,{})
                    evaluation={"security_id":sid,"session_date":day,"feature_snapshot_sha256":snap["feature_snapshot_sha256"],
                        "evaluation":result,"trade_plan_gate":"not_supplied"}
                    if result["status"]!="research_ranked":
                        evaluation["trade_plan_gate"]="blocked_by_strategy_evidence_or_history"
                    elif not isinstance(plan,dict):
                        evaluation["trade_plan_gate"]="missing_independent_trade_plan"
                    else:
                        stop=plan.get("stop"); target=plan.get("target")
                        rr=plan.get("net_reward_risk")
                        try: rr_value=float(rr)
                        except (TypeError,ValueError): rr_value=0
                        required=("signal_id","decision_date","decision_time","sample_partition","entry_price","liquidity_quantity_cap")
                        valid=(all(plan.get(k) not in (None,"") for k in required)
                            and plan.get("decision_date")==day
                            and plan.get("decision_time")==snap["decision_cutoff"]
                            and plan.get("sample_partition")==partition_by_date.get(day)
                            and plan.get("evidence_status")=="verified"
                            and isinstance(stop,dict) and stop.get("evidence_status")=="verified"
                            and isinstance(target,dict) and target.get("evidence_status")=="verified"
                            and rr_value>=2 and plan.get("feature_snapshot_sha256")==snap["feature_snapshot_sha256"])
                        if valid:
                            signal={**plan,"symbol":snap.get("symbol") or sid,"strategy_id":strategy_id,
                                "horizon":horizon,"feature_snapshot_sha256":snap["feature_snapshot_sha256"],
                                "source_evaluation_sha256":_fingerprint(result)}
                            signals[strategy_id+":"+horizon].append(signal)
                            evaluation["trade_plan_gate"]="passed"
                        else:
                            evaluation["trade_plan_gate"]="invalid_or_unverified_trade_plan"
                    evaluations.append(evaluation)
                    if evaluation["trade_plan_gate"]!="passed":
                        withheld.append({"security_id":sid,"session_date":day,"strategy_id":strategy_id,
                            "horizon":horizon,"reason":evaluation["trade_plan_gate"]})
    return {"schema_version":"nepse-six-strategy-candidate-bridge-1.0.0",
        "status":"completed_with_gaps" if withheld else "completed",
        "evaluation_count":len(evaluations),"qualified_signal_count":sum(map(len,signals.values())),
        "evaluations":evaluations,"signals_by_strategy_horizon":signals,"withheld":withheld,
        "policy":"feature score is not a trade; require separately verified entry/stop/target, net R:R >=2, liquidity cap, same decision cutoff, same snapshot fingerprint and explicit sample partition",
        "performance_claimed":False,"probabilities_calibrated":False,"production_enabled":False}

def run_feature_to_six_strategy_replay(*, historical_panel, candidate_bundle, bars_by_symbol,
    round_trip_cost_pct, round_trip_slippage_pct, sellable_after_sessions=2):
    if not isinstance(candidate_bundle,dict) or candidate_bundle.get("schema_version")!="nepse-six-strategy-candidate-bridge-1.0.0":
        raise ValueError("candidate_bundle_schema_invalid")
    replay=run_six_strategy_replay(historical_panel=historical_panel,
        signals_by_strategy_horizon=candidate_bundle["signals_by_strategy_horizon"],
        bars_by_symbol=bars_by_symbol,round_trip_cost_pct=round_trip_cost_pct,
        round_trip_slippage_pct=round_trip_slippage_pct,
        sellable_after_sessions=sellable_after_sessions)
    return {"schema_version":"nepse-feature-to-replay-1.0.0","status":replay["status"],
        "candidate_count":candidate_bundle["qualified_signal_count"],"replay":replay,
        "comparison_warning":"Only compare strategies on identical point-in-time universe, folds, costs, slippage and settlement assumptions. OOS selection must remain untouched.",
        "performance_claimed":False,"production_enabled":False}
