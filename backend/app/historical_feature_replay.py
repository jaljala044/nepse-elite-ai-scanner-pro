"""Generate as-of feature snapshots and six-strategy research qualifications.

Uses the existing point-in-time feature pipeline. No features, provenance or
trade levels are synthesized; every decision point is independently rebuilt.
"""
from __future__ import annotations
from datetime import datetime, timezone
from app.feature_pipeline import build_feature_snapshot
from app.scanner_strategy_integration import adapt_feature_snapshot_to_strategy_evidence
from app.scanner_strategy_lab import STRATEGIES, evaluate_strategy

def _time(value):
    if not isinstance(value, str): return None
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def build_historical_feature_series(*, records, decision_points, expected_symbols,
    evidence_manifests, sector_membership=None, expected_sector_members=None):
    """Build immutable-by-value as-of snapshots; decision_points are chronological.

    Each decision point: {decision_time, session_dates}. A distinct trusted
    evidence manifest is required per decision timestamp and symbol.
    """
    if not isinstance(records,list) or not records: raise ValueError("historical_records_required")
    if not isinstance(decision_points,list) or not decision_points: raise ValueError("decision_points_required")
    if not isinstance(expected_symbols,list) or not expected_symbols: raise ValueError("expected_symbols_required")
    if not isinstance(evidence_manifests,dict): raise ValueError("evidence_manifests_required")
    parsed=[]; previous=None
    for point in decision_points:
        if not isinstance(point,dict): raise ValueError("decision_point_invalid")
        cutoff=_time(point.get("decision_time"))
        sessions=point.get("session_dates")
        if cutoff is None: raise ValueError("decision_time_must_be_timezone_aware")
        if not isinstance(sessions,list) or not sessions: raise ValueError("canonical_session_dates_required")
        if previous is not None and cutoff<=previous: raise ValueError("decision_points_must_be_strictly_chronological")
        if sessions != sorted(set(sessions)): raise ValueError("session_dates_must_be_unique_and_chronological")
        parsed.append((cutoff,sessions)); previous=cutoff
    snapshots=[]; withheld=[]
    for cutoff,sessions in parsed:
        key=cutoff.isoformat()
        manifest=evidence_manifests.get(key)
        if not isinstance(manifest,dict):
            withheld.append({"decision_time":key,"reason":"trusted_evidence_manifest_missing"})
            manifest={}
        snapshot=build_feature_snapshot(records,cutoff.isoformat(),expected_symbols,
            sector_membership=sector_membership,
            expected_sector_members=expected_sector_members,session_dates=sessions)
        adapted=adapt_feature_snapshot_to_strategy_evidence(
            feature_snapshot=snapshot,evidence_manifest=manifest,decision_time=cutoff.isoformat())
        session_count=len(sessions)
        symbols={}
        for symbol,strategy_map in adapted["symbols"].items():
            symbols[symbol]={}
            for strategy_id in STRATEGIES:
                item=strategy_map[strategy_id]
                symbols[symbol][strategy_id]={
                    "feature_evidence":item["feature_evidence"],
                    "missing_features":item["missing_features"],
                    "admitted_feature_count":item["admitted_feature_count"],
                    "required_feature_count":item["required_feature_count"],
                    "qualification_by_horizon":{}
                }
                for horizon in ("t_plus_2","swing","positional","investment"):
                    result=evaluate_strategy(strategy_id=strategy_id,symbol=symbol,
                        horizon=horizon,decision_time=cutoff.isoformat(),
                        history_sessions=session_count,
                        feature_evidence=item["feature_evidence"])
                    symbols[symbol][strategy_id]["qualification_by_horizon"][horizon]={
                        "status":result["status"],"action":result["action"],
                        "score":result["score"],"evidence_coverage_pct":result["evidence_coverage_pct"],
                        "history_passed":result["history_passed"],
                        "coverage_passed":result["coverage_passed"],
                        "missing_features":result["missing_features"],
                        "rejected_features":result["rejected_features"],
                        "accepted_evidence_clusters":result["accepted_evidence_clusters"]
                    }
        snapshots.append({
            "decision_time":key,"as_of_session":sessions[-1],
            "session_count":session_count,"input_contracts":snapshot.get("input_contracts",{}),
            "included_input_count":snapshot.get("included_input_count"),
            "excluded_input_count":snapshot.get("excluded_input_count"),
            "feature_series":symbols,
            "feature_adapter_policy":adapted["policy"],
            "status":"research_snapshot_built",
            "production_enabled":False
        })
    return {
        "schema_version":"nepse-historical-feature-series-1.0.0",
        "status":"built_with_gaps" if withheld else "built",
        "snapshot_count":len(snapshots),"snapshots":snapshots,"withheld_decision_points":withheld,
        "strategy_count":len(STRATEGIES),"horizons":["t_plus_2","swing","positional","investment"],
        "signals_generated":False,"trade_plans_generated":False,
        "performance_claimed":False,"production_enabled":False,
        "limitations":[
            "Feature snapshots are descriptive and inherit the upstream source/session/price-basis gates.",
            "A trusted per-decision evidence manifest must be supplied by a server-side evidence ledger.",
            "The current feature pipeline does not implement complete IDPAT hidden-level, accumulation/distribution, broker-persistence or fundamental scores.",
            "SMC remains experimental-only and is not promoted to weighted strategy evidence.",
            "Research qualification is not a trade signal; evidence-backed plans, execution and replay remain separate gates."
        ]
    }
