"""Evidence-gated bridge from historical feature snapshots to six-strategy replay."""
from __future__ import annotations
import hashlib, json, re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from app.scanner_strategy_lab import STRATEGIES, evaluate_strategy
from app.scanner_replay_orchestrator import run_six_strategy_replay
from app.scanner_backtest import HOLDING_SESSIONS

_SHA256=re.compile(r"^[0-9a-f]{64}$")

def _fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def _decimal(value):
    if isinstance(value,bool): return None
    try:
        parsed=Decimal(str(value))
        return parsed if parsed.is_finite() else None
    except (InvalidOperation,TypeError,ValueError):
        return None

def _timestamp(value):
    if not isinstance(value,str): return None
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def _verified_evidence(item, cutoff):
    if not isinstance(item,dict) or item.get("evidence_status")!="verified": return False
    if not isinstance(item.get("source_id"),str) or not item["source_id"].strip(): return False
    if not isinstance(item.get("evidence_id"),str) or not item["evidence_id"].strip(): return False
    available=_timestamp(item.get("available_at"))
    return available is not None and available<=cutoff

def _valid_trade_plan(plan, snapshot, day, expected_partition):
    """Validate the same evidence/time contract used by the downstream replay."""
    if not isinstance(plan,dict) or not isinstance(snapshot,dict): return False
    cutoff=_timestamp(snapshot.get("decision_cutoff"))
    plan_cutoff=_timestamp(plan.get("decision_time"))
    digest=str(snapshot.get("feature_snapshot_sha256",""))
    if cutoff is None or plan_cutoff is None or plan_cutoff!=cutoff: return False
    if cutoff.date().isoformat()!=day or plan.get("decision_date")!=day: return False
    if not _SHA256.fullmatch(digest) or plan.get("feature_snapshot_sha256")!=digest: return False
    if expected_partition not in {"train","validation","out_of_sample"}: return False
    if plan.get("sample_partition")!=expected_partition: return False
    if not isinstance(plan.get("signal_id"),str) or not plan["signal_id"].strip(): return False
    if not _verified_evidence(plan,cutoff): return False
    stop=plan.get("stop"); target=plan.get("target")
    if not _verified_evidence(stop,cutoff) or not _verified_evidence(target,cutoff): return False
    entry_price=_decimal(plan.get("entry_price"))
    stop_price=_decimal(stop.get("price"))
    target_price=_decimal(target.get("price"))
    quantity_cap=_decimal(plan.get("liquidity_quantity_cap"))
    net_reward_risk=_decimal(plan.get("net_reward_risk"))
    if any(value is None or value<=0 for value in (entry_price,stop_price,target_price,quantity_cap)): return False
    if quantity_cap != quantity_cap.to_integral_value(): return False
    if stop_price>=entry_price or target_price<=entry_price: return False
    if net_reward_risk is None or net_reward_risk<Decimal("2"): return False
    gross_reward_risk=(target_price-entry_price)/(entry_price-stop_price)
    if not gross_reward_risk.is_finite() or gross_reward_risk<Decimal("2") or net_reward_risk>gross_reward_risk: return False
    return True

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
    for sid,rows in histories.items():
        rows.sort(key=lambda x:x["session_date"])
        days=[x.get("session_date") for x in rows]
        if len(days)!=len(set(days)): raise ValueError("duplicate_security_session_snapshot:"+str(sid))
    evaluations=[]; signals={s+":"+h:[] for s in STRATEGIES for h in HOLDING_SESSIONS}
    withheld=[]; seen_signal_ids=set()
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
                        valid=_valid_trade_plan(plan,snap,day,partition_by_date.get(day))
                        if valid and plan["signal_id"] in seen_signal_ids:
                            valid=False
                        if valid:
                            seen_signal_ids.add(plan["signal_id"])
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
        "policy":"feature score is not a trade; require independently verified plan/stop/target provenance, finite positive long-side prices, whole-share liquidity cap, net and gross R:R >=2, same decision cutoff, same snapshot fingerprint, unique signal ID and explicit sample partition",
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
