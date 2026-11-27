"""Fail-closed bridge to the existing full NEPSE feature pipeline.

This module deliberately preserves missing component scores and hard blocks.
It exposes Wyckoff, Minervini, RS, broker, VSA, SMC, sector and liquidity
features from the established feature pipeline, plus optional IDPAT horizon
research. It does not turn research scores into BUY/SELL recommendations.
"""
from __future__ import annotations
from app.feature_pipeline import build_feature_snapshot
from app.idpat_horizon_validation import validate_idpat_horizons


def build_full_stack_research_validation(*, records, decision_time,
    expected_symbols=None, sector_membership=None, expected_sector_members=None,
    session_dates=None, evidence_pipeline=None, idpat_snapshots=None,
    as_of_date=None, as_of_timestamp=None, session_calendar=None):
    ready=(isinstance(evidence_pipeline,dict)
        and evidence_pipeline.get("research_review_allowed") is True
        and evidence_pipeline.get("production_promotion_allowed") is False)
    if not ready:
        return {"status":"blocked_missing_admitted_nepse_history",
            "action":"NO_TRADE","overall_score":None,"probability":None,
            "feature_snapshot":None,"idpat_horizons":{},
            "production_recommendations_enabled":False,
            "errors":["trusted_reference_raw_admission_reconciliation_and_120_session_gates_required"]}
    features=build_feature_snapshot(records=records,decision_time=decision_time,
        expected_symbols=expected_symbols,sector_membership=sector_membership,
        expected_sector_members=expected_sector_members,session_dates=session_dates)
    horizons={}
    for symbol,snapshot in (idpat_snapshots or {}).items():
        horizons[symbol]=validate_idpat_horizons(snapshot=snapshot,as_of_date=as_of_date,
            as_of_timestamp=as_of_timestamp,history_validation=evidence_pipeline,
            session_calendar=session_calendar,trusted_gate_evidence=None)
    return {"status":"research_features_evaluated",
        "decision_time":features.get("decision_time"),
        "input_contracts":features.get("input_contracts"),
        "market_breadth":features.get("market_breadth"),
        "security_features":features.get("security_features"),
        "wyckoff":features.get("wyckoff_features"),
        "minervini":features.get("trend_features"),
        "relative_strength":features.get("relative_strength"),
        "broker_footprint":features.get("broker_footprint"),
        "volume_vsa":features.get("volume_features"),
        "smc":features.get("smc_features"),
        "sector_strength":features.get("sector_strength"),
        "liquidity_tradability":features.get("liquidity_tradability"),
        "component_candidates":features.get("component_candidates"),
        "aggregate_scores":features.get("aggregate_scores"),
        "idpat_horizons":horizons,
        "action":"NO_TRADE","overall_score":None,"probability":None,
        "production_recommendations_enabled":False,"production_promotion_allowed":False,
        "limitations":["Existing feature pipeline retains explicit hard blocks for stage-1 quality, structure, liquidity, market and reward/risk.",
        "Broker, sector and other components remain descriptive where their independent source contracts are incomplete.",
        "No calibrated composite rating, BUY/SELL, probability or backtest result is generated."]}
