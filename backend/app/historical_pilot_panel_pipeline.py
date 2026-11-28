"""Assemble validated OHLCV into a reviewable pilot panel with fail-closed gates."""
from __future__ import annotations
from typing import Iterable, Mapping
from app.historical_pilot_replay_gate import build_pilot_replay_preflight
from app.historical_pilot_quality_dashboard import build_historical_pilot_quality_dashboard


def build_historical_pilot_panel_review(*, cohort_symbols: Iterable[str], security_master: Iterable[Mapping[str, object]], expected_sessions: Iterable[Mapping[str, object]], ohlcv_ingestion_reports: Iterable[Mapping[str, object]], corporate_action_status: Mapping[str, object], source_reconciliation_report: Mapping[str, object], decision_cutoff: str, required_capture_keys: Iterable[str], minimum_independent_sources: int = 1) -> dict:
    """Build deterministic panel, preflight and dashboard; never auto-admit a backtest."""
    symbols, master, sessions, ingestions = list(cohort_symbols), list(security_master), list(expected_sessions), list(ohlcv_ingestion_reports)
    if source_reconciliation_report.get("status") != "SOURCE_EVIDENCE_RECONCILED":
        return {"status":"BLOCKED","reason":"source_reconciliation_not_passed","replay_preflight":None,"quality_dashboard":None,"backtest_admission_allowed":False,"production_enabled":False}
    if not ingestions or any(not isinstance(r,Mapping) or r.get("status") != "INGESTED" or r.get("all_rows_accepted") is not True for r in ingestions):
        return {"status":"BLOCKED","reason":"one_or_more_ohlcv_ingestion_reports_not_fully_accepted","replay_preflight":None,"quality_dashboard":None,"backtest_admission_allowed":False,"production_enabled":False}
    preflight = build_pilot_replay_preflight(
        cohort_symbols=symbols,security_master=master,expected_sessions=sessions,
        ingestion_reports=ingestions,corporate_action_status=corporate_action_status,
        source_reconciliation_report=source_reconciliation_report,decision_cutoff=decision_cutoff,
        required_capture_keys=list(required_capture_keys),minimum_independent_sources=minimum_independent_sources,
    )
    panel = preflight.get("panel",{})
    dashboard = build_historical_pilot_quality_dashboard(
        cohort_symbols=symbols,security_master=master,expected_sessions=sessions,
        panel_report=panel,reconciliation_report=source_reconciliation_report,
        replay_preflight=preflight,corporate_action_status=corporate_action_status,
    )
    ready = preflight.get("status") == "BOUNDED_PILOT_REPLAY_PREFLIGHT_READY" and dashboard.get("status") == "QUALITY_REVIEW_READY"
    return {
        "status":"PANEL_QUALITY_REVIEW_READY" if ready else "BLOCKED",
        "panel":panel,"replay_preflight":preflight,"quality_dashboard":dashboard,
        "dataset_manifest":preflight.get("dataset_manifest"),
        "human_review_required":True,"research_replay_admission_required":True,
        "backtest_admission_allowed":False,"canonical_promotion_allowed":False,"production_enabled":False,
        "next_required_action":"independent_human_review_then_explicit_research_replay_admission" if ready else "resolve_panel_quality_or_evidence_blockers",
        "limitations":[
            "The panel contains only the explicitly supplied OHLCV ingestion reports, identity records, sessions and corporate-action status.",
            "A passing dashboard is review readiness, not proof of publisher authenticity or full exchange-wide completeness.",
            "No historical replay, performance calculation or probability calibration is performed.",
        ],
    }
