"""Build a provenance-hashed pilot panel and fail-closed replay preflight."""
from __future__ import annotations

import hashlib
import json
from typing import Iterable, Mapping

from app.historical_pilot_admission import build_pilot_admission_bundle
from app.historical_pilot_assembler import assemble_lifecycle_pilot_panel


def _canonical_sha256(value: Mapping[str, object]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_pilot_replay_preflight(
    *,
    cohort_symbols: Iterable[str],
    security_master: Iterable[Mapping[str, object]],
    expected_sessions: Iterable[Mapping[str, object]],
    ingestion_reports: Iterable[Mapping[str, object]],
    corporate_action_status: Mapping[str, object],
    source_reconciliation_report: Mapping[str, object],
    decision_cutoff: str,
    required_capture_keys: Iterable[str],
    minimum_independent_sources: int = 1,
) -> dict:
    """Assemble the panel and bind every supplied decision input into its manifest.

    Raw payload bytes remain outside this function; their exact page SHA-256 values
    must be present in the validated capture reports and ingestion provenance.
    """
    symbols = list(cohort_symbols)
    master = list(security_master)
    sessions = list(expected_sessions)
    ingestions = list(ingestion_reports)
    capture_reports = source_reconciliation_report.get("capture_reports", {})
    first_trade = source_reconciliation_report.get("first_trade_report", {})
    panel = assemble_lifecycle_pilot_panel(
        cohort_symbols=symbols, security_master=master, expected_sessions=sessions,
        ingestion_reports=ingestions, corporate_action_status=corporate_action_status,
        decision_cutoff=decision_cutoff, minimum_independent_sources=minimum_independent_sources,
    )
    admission = build_pilot_admission_bundle(
        capture_reports=capture_reports if isinstance(capture_reports, Mapping) else {},
        first_trade_report=first_trade if isinstance(first_trade, Mapping) else {},
        panel_readiness_report=panel.get("readiness_report", {}),
        required_capture_ids=list(required_capture_keys),
    )
    canonical_rows = sorted(panel.get("panel_rows", []), key=lambda x: (x["symbol"], x["session_date"]))
    panel_output_payload = {"panel_rows": canonical_rows}
    panel_output_hash = _canonical_sha256(panel_output_payload)
    manifest_payload = {
        "schema_version": 2,
        "decision_cutoff": decision_cutoff,
        "cohort_symbols": sorted(symbols),
        "security_master": master,
        "expected_sessions": sessions,
        "ingestion_reports": ingestions,
        "corporate_action_status": corporate_action_status,
        "source_reconciliation_report": source_reconciliation_report,
        "panel_output_sha256": panel_output_hash,
        "panel_report": panel,
        "admission_report": admission,
        "minimum_independent_sources": minimum_independent_sources,
    }
    manifest_error = None
    try:
        manifest_hash = _canonical_sha256(manifest_payload)
    except (TypeError, ValueError):
        manifest_hash = None
        manifest_error = "decision_inputs_not_canonical_json_serializable"

    gates_pass = (
        panel.get("status") == "PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH"
        and admission.get("status") == "BOUNDED_PILOT_EVIDENCE_READY"
        and manifest_hash is not None
    )
    gate_diagnostics = {
        "panel_status": panel.get("status"),
        "panel_readiness_status": panel.get("readiness_report", {}).get("status"),
        "panel_identity_errors": panel.get("readiness_report", {}).get("identity_errors", []),
        "panel_session_errors": panel.get("readiness_report", {}).get("session_errors", []),
        "panel_bar_errors": panel.get("readiness_report", {}).get("bar_errors", []),
        "panel_missing_symbol_sessions": panel.get("readiness_report", {}).get("missing_symbol_sessions", []),
        "panel_corporate_actions": panel.get("readiness_report", {}).get("corporate_actions"),
        "panel_assembly_errors": panel.get("ingestion_errors", []),
        "panel_source_conflicts": panel.get("conflicts", []),
        "panel_insufficient_source_coverage": panel.get("insufficient_source_coverage", []),
        "admission_status": admission.get("status"),
        "admission_blocking_reasons": admission.get("blocking_reasons", []),
        "manifest_error": manifest_error,
    }
    return {
        "status": "BOUNDED_PILOT_REPLAY_PREFLIGHT_READY" if gates_pass else "BLOCKED",
        "panel": panel,
        "admission": admission,
        "dataset_manifest": {
            "sha256": manifest_hash,
            "input_manifest_sha256": manifest_hash,
            "panel_output_sha256": panel_output_hash,
            "row_count": len(canonical_rows),
            "decision_cutoff": decision_cutoff,
            "cohort_count": len(symbols),
            "schema_version": 2,
        },
        "replay_preflight_passed": gates_pass,
        "gate_diagnostics": gate_diagnostics,
        "historical_replay_executed": False,
        "backtest_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "production_enabled": False,
        "next_required_action": "independent_human_review_and_explicit_research_dataset_admission" if gates_pass else "resolve_all_blocking_source_identity_calendar_ohlcv_or_corporate_action_evidence",
        "limitations": [
            "The input manifest binds supplied security-master, expected-session, ingestion, corporate-action, reconciliation and panel reports.",
            "Raw payload bytes are not embedded; their exact SHA-256 values must be retained in validated capture-page and ingestion provenance.",
            "Preflight readiness is not permission to run a backtest; explicit dataset admission is a separate control.",
            "No performance, accuracy or probability claim is produced.",
        ],
    }
