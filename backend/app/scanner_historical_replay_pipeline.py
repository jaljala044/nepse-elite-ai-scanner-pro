"""Evidence-gated bridge from historical feature snapshots to six-strategy replay."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from app.scanner_strategy_lab import STRATEGIES, evaluate_strategy
from app.scanner_replay_orchestrator import run_six_strategy_replay
from app.scanner_backtest import HOLDING_SESSIONS

_NEPA_TZ=ZoneInfo("Asia/Kathmandu")
_SHA256=re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_PARTITIONS={"train","validation","out_of_sample"}


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()


def _day(value):
    if not isinstance(value,str):
        return None
    try: parsed=date.fromisoformat(value)
    except ValueError: return None
    return parsed if parsed.isoformat()==value else None


def _timestamp(value):
    if not isinstance(value,str): return None
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)


def _positive(value):
    try: parsed=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): return None
    return parsed if parsed.is_finite() and parsed>0 else None


def _verified_level(value, cutoff):
    if not isinstance(value,dict) or value.get("evidence_status")!="verified":
        return False
    if not isinstance(value.get("source_id"),str) or not value["source_id"].strip():
        return False
    if not isinstance(value.get("evidence_id"),str) or not value["evidence_id"].strip():
        return False
    available=_timestamp(value.get("available_at"))
    price=_positive(value.get("price"))
    return available is not None and available<=cutoff and price is not None


def build_historical_research_candidates(*, snapshots, feature_evidence_by_key,
    trade_plans_by_key, partition_by_date, minimum_coverage="0.95"):
    """Evaluate every strategy/horizon; only source-bound, risk-valid plans become replay signals.

    Keys are '<security_id>|<session_date>'. A strategy score alone never creates a trade.
    """
    if (not isinstance(snapshots,list) or not isinstance(feature_evidence_by_key,dict)
            or not isinstance(trade_plans_by_key,dict) or not isinstance(partition_by_date,dict)):
        raise ValueError("snapshots_evidence_trade_plans_and_partitions_required")

    histories={}
    seen_snapshots=set()
    for snap in snapshots:
        if not isinstance(snap,dict):
            raise ValueError("snapshot_invalid")
        sid=snap.get("security_id")
        symbol=snap.get("symbol")
        day=_day(snap.get("session_date"))
        cutoff=_timestamp(snap.get("decision_cutoff"))
        digest=snap.get("feature_snapshot_sha256")
        if not isinstance(sid,str) or not sid.strip() or not isinstance(symbol,str) or not symbol.strip():
            raise ValueError("snapshot_identity_invalid")
        if day is None or cutoff is None or not isinstance(digest,str) or not _SHA256.fullmatch(digest):
            raise ValueError("snapshot_date_cutoff_or_fingerprint_invalid")
        if day>cutoff.astimezone(_NEPA_TZ).date():
            raise ValueError("future_snapshot_after_decision_cutoff:"+sid+":"+day.isoformat())
        key=(sid.strip(),day.isoformat())
        if key in seen_snapshots:
            raise ValueError("duplicate_security_session_snapshot:"+key[0]+":"+key[1])
        seen_snapshots.add(key)
        if snap.get("feature_status")!="complete":
            continue
        histories.setdefault(key[0],[]).append(snap)
    for rows in histories.values():
        rows.sort(key=lambda x:x["session_date"])

    evaluations=[]
    signals={s+":"+h:[] for s in STRATEGIES for h in HOLDING_SESSIONS}
    withheld=[]
    used_signal_ids=set()
    for sid,rows in sorted(histories.items()):
        for i,snap in enumerate(rows):
            day=snap["session_date"]
            key=sid+"|"+day
            snapshot_cutoff=_timestamp(snap["decision_cutoff"])
            snapshot_digest=snap["feature_snapshot_sha256"]
            supplied_evidence=feature_evidence_by_key.get(key,{})
            evidence_matches=(isinstance(supplied_evidence,dict)
                and supplied_evidence.get("feature_snapshot_sha256")==snapshot_digest)
            evidence=supplied_evidence if evidence_matches else {}
            for strategy_id in STRATEGIES:
                for horizon in HOLDING_SESSIONS:
                    result=evaluate_strategy(strategy_id=strategy_id,symbol=snap.get("symbol") or sid,
                        horizon=horizon,decision_time=snap["decision_cutoff"],
                        history_sessions=i+1,feature_evidence=evidence,minimum_coverage=minimum_coverage)
                    by_strategy=trade_plans_by_key.get(key,{})
                    by_horizon=by_strategy.get(strategy_id,{}) if isinstance(by_strategy,dict) else {}
                    plan=by_horizon.get(horizon,{}) if isinstance(by_horizon,dict) else {}
                    evaluation={"security_id":sid,"session_date":day,
                        "feature_snapshot_sha256":snapshot_digest,"evaluation":result,
                        "feature_evidence_gate":"matched" if evidence_matches else "missing_or_snapshot_mismatch",
                        "trade_plan_gate":"not_supplied"}

                    if result["status"]!="research_ranked":
                        evaluation["trade_plan_gate"]="blocked_by_strategy_evidence_or_history"
                    elif not isinstance(plan,dict):
                        evaluation["trade_plan_gate"]="missing_independent_trade_plan"
                    else:
                        entry=_positive(plan.get("entry_price"))
                        stop_level=plan.get("stop")
                        target_level=plan.get("target")
                        stop=_positive(stop_level.get("price")) if isinstance(stop_level,dict) else None
                        target=_positive(target_level.get("price")) if isinstance(target_level,dict) else None
                        net_rr=_positive(plan.get("net_reward_risk"))
                        cap=_positive(plan.get("liquidity_quantity_cap"))
                        plan_available=_timestamp(plan.get("available_at"))
                        plan_cutoff=_timestamp(plan.get("decision_time"))
                        signal_id=plan.get("signal_id")
                        sample_partition=plan.get("sample_partition")
                        required=("signal_id","source_id","evidence_id","available_at","entry_price","liquidity_quantity_cap")
                        cap_integer=(cap is not None and cap==cap.to_integral_value())
                        geometry=(entry is not None and stop is not None and target is not None
                            and stop<entry<target)
                        gross_rr=(target-entry)/(entry-stop) if geometry else None
                        valid=(evidence_matches
                            and all(plan.get(k) not in (None,"") for k in required)
                            and isinstance(signal_id,str) and bool(signal_id.strip())
                            and signal_id not in used_signal_ids
                            and plan.get("decision_date")==day
                            and plan_cutoff is not None and plan_cutoff==snapshot_cutoff
                            and sample_partition in _ALLOWED_PARTITIONS
                            and sample_partition==partition_by_date.get(day)
                            and plan.get("evidence_status")=="verified"
                            and plan_available is not None and plan_available<=snapshot_cutoff
                            and _verified_level(stop_level,snapshot_cutoff)
                            and _verified_level(target_level,snapshot_cutoff)
                            and geometry and cap_integer
                            and net_rr is not None and net_rr>=Decimal("2")
                            and gross_rr is not None and net_rr<=gross_rr)
                        if valid:
                            signal={**plan,"symbol":snap.get("symbol") or sid,"strategy_id":strategy_id,
                                "horizon":horizon,"feature_snapshot_sha256":snapshot_digest,
                                "source_evaluation_sha256":_fingerprint(result)}
                            signals[strategy_id+":"+horizon].append(signal)
                            used_signal_ids.add(signal_id)
                            evaluation["trade_plan_gate"]="passed"
                            evaluation["computed_gross_reward_risk"]=str(gross_rr)
                        else:
                            evaluation["trade_plan_gate"]="invalid_or_unverified_trade_plan"
                            evaluation["computed_gross_reward_risk"]=str(gross_rr) if gross_rr is not None else None
                    evaluations.append(evaluation)
                    if evaluation["trade_plan_gate"]!="passed":
                        withheld.append({"security_id":sid,"session_date":day,"strategy_id":strategy_id,
                            "horizon":horizon,"reason":evaluation["trade_plan_gate"]})
    return {"schema_version":"nepse-six-strategy-candidate-bridge-1.0.0",
        "status":"completed_with_gaps" if withheld else "completed",
        "evaluation_count":len(evaluations),"qualified_signal_count":sum(map(len,signals.values())),
        "evaluations":evaluations,"signals_by_strategy_horizon":signals,"withheld":withheld,
        "policy":"feature score is not a trade; require feature-hash-bound evidence, a source/time-bound plan, verified stop/target, net R:R >=2 not exceeding entry/stop/target geometry, positive whole-share liquidity cap, same decision cutoff, unique signal identity and explicit sample partition",
        "performance_claimed":False,"probabilities_calibrated":False,"production_enabled":False}


def run_feature_to_six_strategy_replay(*, historical_panel, candidate_bundle, bars_by_symbol,
    round_trip_cost_pct, round_trip_slippage_pct, sellable_after_sessions=2):
    if not isinstance(candidate_bundle,dict) or candidate_bundle.get("schema_version")!="nepse-six-strategy-candidate-bridge-1.0.0":
        raise ValueError("candidate_bundle_schema_invalid")
    signals=candidate_bundle.get("signals_by_strategy_horizon")
    if not isinstance(signals,dict) or set(signals)!={s+":"+h for s in STRATEGIES for h in HOLDING_SESSIONS}:
        raise ValueError("candidate_bundle_signal_batches_invalid")
    if any(not isinstance(batch,list) for batch in signals.values()):
        raise ValueError("candidate_bundle_signal_batches_invalid")
    actual_count=sum(len(batch) for batch in signals.values())
    if candidate_bundle.get("qualified_signal_count")!=actual_count:
        raise ValueError("candidate_bundle_signal_count_mismatch")
    replay=run_six_strategy_replay(historical_panel=historical_panel,
        signals_by_strategy_horizon=signals,bars_by_symbol=bars_by_symbol,
        round_trip_cost_pct=round_trip_cost_pct,
        round_trip_slippage_pct=round_trip_slippage_pct,
        sellable_after_sessions=sellable_after_sessions)
    return {"schema_version":"nepse-feature-to-replay-1.0.0","status":replay["status"],
        "candidate_count":actual_count,"replay":replay,
        "comparison_warning":"Only compare strategies on identical point-in-time universe, folds, costs, slippage and settlement assumptions. OOS selection must remain untouched.",
        "performance_claimed":False,"production_enabled":False}
