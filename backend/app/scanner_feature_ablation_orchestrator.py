"""Matched OOS feature ablation runner for all six strategies and four horizons.

The injected runner must regenerate the scanner variant at each historical fold cutoff.
This module does not fetch data, train models or infer missing evidence.
"""
from __future__ import annotations
import hashlib
import json
from app.scanner_feature_ablation import compare_feature_ablations
from app.scanner_strategy_lab import HORIZONS, STRATEGIES
from app.scanner_experiment_registry import append_experiment_events

REQUIRED_ASSUMPTIONS = ("universe_fingerprint", "panel_fingerprint",
    "cost_model_id", "execution_model_id", "methodology_version")

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)

def _sha(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

def _variant_record(result, *, strategy_id, horizon, fold_id, feature_group, excluded):
    if not isinstance(result, dict):
        raise ValueError("variant_runner_must_return_dict")
    missing = [k for k in REQUIRED_ASSUMPTIONS if not isinstance(result.get(k), str) or not result[k]]
    if missing:
        raise ValueError("variant_assumptions_missing:" + ",".join(missing))
    trades = result.get("closed_trades")
    if not isinstance(trades, list):
        raise ValueError("variant_closed_trades_missing")
    return {"strategy_id": strategy_id, "horizon": horizon, "fold_id": fold_id,
        "feature_group": feature_group, "partition": "out_of_sample",
        "excluded_feature_groups": list(excluded),
        "baseline": None, "ablated": None,
        "variant": {**{k: result[k] for k in REQUIRED_ASSUMPTIONS},
            "closed_trades": trades, "run_output_sha256": _sha(result)}}

def run_feature_ablation_matrix(*, run_variant, folds, registry_events=None,
    minimum_total_trades=30, minimum_folds=3, run_timestamp=None):
    """Run baseline plus one-cluster-removed variant for each strategy/horizon/fold."""
    if not callable(run_variant):
        raise ValueError("run_variant_callable_required")
    if not isinstance(folds, list) or len(folds) < minimum_folds:
        raise ValueError("insufficient_oos_folds")
    if not isinstance(run_timestamp, str) or not run_timestamp:
        raise ValueError("run_timestamp_required")
    if registry_events is None:
        registry_events = []
    if not isinstance(registry_events, list):
        raise ValueError("registry_events_must_be_list")
    fold_ids = []
    for fold in folds:
        if not isinstance(fold, dict) or fold.get("partition") != "out_of_sample":
            raise ValueError("every_fold_must_be_out_of_sample")
        fold_id = fold.get("fold_id")
        if not isinstance(fold_id, str) or not fold_id.strip() or fold_id in fold_ids:
            raise ValueError("fold_id_missing_or_duplicate")
        # Explicit fingerprints bind each run to the same point-in-time fold.
        if any(not isinstance(fold.get(k), str) or not fold[k] for k in REQUIRED_ASSUMPTIONS):
            raise ValueError("fold_assumptions_missing")
        fold_ids.append(fold_id)

    rows, rejected, new_events = [], [], []
    variant_count = 0
    for strategy_id, spec in STRATEGIES.items():
        groups = sorted(set(spec["clusters"].values()))
        for horizon in HORIZONS:
            for fold in sorted(folds, key=lambda x: x["fold_id"]):
                fold_id = fold["fold_id"]
                baseline = run_variant(strategy_id=strategy_id, horizon=horizon,
                    fold=fold, excluded_feature_groups=(), partition="out_of_sample")
                base_record = _variant_record(baseline, strategy_id=strategy_id,
                    horizon=horizon, fold_id=fold_id, feature_group="__baseline__", excluded=())
                for field in REQUIRED_ASSUMPTIONS:
                    if base_record["variant"][field] != fold[field]:
                        raise ValueError("baseline_fold_assumption_mismatch:" + field)
                base_id = _sha({"strategy":strategy_id,"horizon":horizon,"fold":fold_id,
                    "excluded":[],"output":base_record["variant"]["run_output_sha256"]})
                new_events.append({"event_id":base_id[:32],"event_type":"EXPERIMENT_REGISTERED",
                    "run_id":base_id,"occurred_at":run_timestamp,
                    "payload":{"strategy_id":strategy_id,"horizon":horizon,"fold_id":fold_id,
                        "partition":"out_of_sample","variant":"baseline",
                        "excluded_feature_groups":[],"assumptions":{k:base_record["variant"][k] for k in REQUIRED_ASSUMPTIONS},
                        "output_sha256":base_record["variant"]["run_output_sha256"]}})
                new_events.append({"event_id":_sha({"run":base_id,"status":"completed"})[:32],
                    "event_type":"EXPERIMENT_COMPLETED","run_id":base_id,"occurred_at":run_timestamp,
                    "payload":{"status":"completed","closed_trade_count":len(base_record["variant"]["closed_trades"])}})
                variant_count += 1
                for group in groups:
                    try:
                        result = run_variant(strategy_id=strategy_id, horizon=horizon,
                            fold=fold, excluded_feature_groups=(group,), partition="out_of_sample")
                        record = _variant_record(result, strategy_id=strategy_id,
                            horizon=horizon, fold_id=fold_id, feature_group=group, excluded=(group,))
                        for field in REQUIRED_ASSUMPTIONS:
                            if record["variant"][field] != base_record["variant"][field]:
                                raise ValueError("ablation_fold_assumption_mismatch:" + field)
                        rows.append({"strategy_id":strategy_id,"horizon":horizon,"fold_id":fold_id,
                            "feature_group":group,"partition":"out_of_sample",
                            "baseline":{k:base_record["variant"][k] for k in REQUIRED_ASSUMPTIONS} |
                                {"closed_trades":base_record["variant"]["closed_trades"]},
                            "ablated":{k:record["variant"][k] for k in REQUIRED_ASSUMPTIONS} |
                                {"closed_trades":record["variant"]["closed_trades"]}})
                        run_id = _sha({"strategy":strategy_id,"horizon":horizon,"fold":fold_id,
                            "excluded":[group],"output":record["variant"]["run_output_sha256"]})
                        new_events.extend([
                            {"event_id":run_id[:32],"event_type":"EXPERIMENT_REGISTERED","run_id":run_id,
                                "occurred_at":run_timestamp,"payload":{"strategy_id":strategy_id,
                                "horizon":horizon,"fold_id":fold_id,"partition":"out_of_sample",
                                "variant":"ablation","excluded_feature_groups":[group],
                                "assumptions":{k:record["variant"][k] for k in REQUIRED_ASSUMPTIONS},
                                "output_sha256":record["variant"]["run_output_sha256"]}},
                            {"event_id":_sha({"run":run_id,"status":"completed"})[:32],
                                "event_type":"EXPERIMENT_COMPLETED","run_id":run_id,
                                "occurred_at":run_timestamp,"payload":{"status":"completed",
                                "closed_trade_count":len(record["variant"]["closed_trades"])}}])
                        variant_count += 1
                    except (ValueError, TypeError, KeyError) as exc:
                        rejected.append({"strategy_id":strategy_id,"horizon":horizon,
                            "fold_id":fold_id,"feature_group":group,"reason":str(exc)})
            # one baseline run is reused only within its exact strategy/horizon/fold and never across folds
    diagnostics = compare_feature_ablations(ablation_runs=rows,
        minimum_total_trades=minimum_total_trades, minimum_folds=minimum_folds)
    registry = append_experiment_events(existing_events=registry_events,new_events=new_events)
    return {"schema_version":"nepse-feature-ablation-matrix-1.0.0",
        "status":"completed_with_gaps" if rejected else "completed",
        "strategy_count":len(STRATEGIES),"horizon_count":len(HORIZONS),
        "fold_count":len(folds),"feature_variant_group_count":sum(len(set(s["clusters"].values())) for s in STRATEGIES.values()),
        "variant_run_count":variant_count,"comparison_count":len(rows),
        "diagnostics":diagnostics,"rejected_runs":rejected,
        "experiment_registry":registry,"run_timestamp":run_timestamp,
        "policy":"all six strategies and four horizons; baseline and one feature-cluster removal per chronological OOS fold; matched universe, panel, cost, execution and methodology IDs",
        "limitations":["The caller-provided runner must enforce point-in-time feature generation and chronological embargoes.",
            "No live NEPSE data is acquired; no performance improvement or future probability is claimed.",
            "Feature removal can change the selected trades; the comparison is portfolio-variant impact, not isolated causal importance.",
            "Registry hash chaining is not a substitute for durable, access-controlled external storage."],
        "performance_claimed":False,"production_enabled":False}
