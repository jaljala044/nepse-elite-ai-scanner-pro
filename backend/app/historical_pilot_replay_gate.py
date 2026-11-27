"""Build a provenance-hashed pilot panel and fail-closed replay preflight."""
from __future__ import annotations
import hashlib
import json
from typing import Iterable, Mapping

from app.historical_pilot_admission import build_pilot_admission_bundle
from app.historical_pilot_assembler import assemble_lifecycle_pilot_panel


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
    """Assemble the panel, join evidence gates, and hash a reproducible manifest.

    This intentionally stops before backtest admission. A human-reviewed, separately
    authorized dataset promotion is required before historical replay can run.
    """
    symbols, master, sessions, ingestions = list(cohort_symbols), list(security_master), list(expected_sessions), list(ingestion_reports)
    panel = assemble_lifecycle_pilot_panel(
        cohort_symbols=symbols, security_master=master, expected_sessions=sessions,
        ingestion_reports=ingestions, corporate_action_status=corporate_action_status,
        decision_cutoff=decision_cutoff, minimum_independent_sources=minimum_independent_sources,
    )
    capture_reports = source_reconciliation_report.get("capture_reports", {})
    first_trade = source_reconciliation_report.get("first_trade_report", {})
    admission = build_pilot_admission_bundle(
        capture_reports=capture_reports if isinstance(capture_reports, Mapping) else {},
        first_trade_report=first_trade if isinstance(first_trade, Mapping) else {},
        panel_readiness_report=panel.get("readiness_report", {}),
        required_capture_ids=list(required_capture_keys),
    )
    # Canonical JSON makes the panel manifest reproducible and audit-friendly.
    canonical_rows = sorted(panel.get("panel_rows", []), key=lambda x: (x["symbol"], x["session_date"]))
    manifest_payload = {
        "decision_cutoff": decision_cutoff,
        "cohort_symbols": sorted(symbols),
        "panel_rows": canonical_rows,
        "source_reconciliation_status": source_reconciliation_report.get("status"),
        "admission_status": admission.get("status"),
        "minimum_independent_sources": minimum_independent_sources,
    }
    manifest_bytes = json.dumps(manifest_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    gates_pass = panel.get("status") == "PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH" and admission.get("status") == "BOUNDED_PILOT_EVIDENCE_READY"
    return {
        "status": "BOUNDED_PILOT_REPLAY_PREFLIGHT_READY" if gates_pass else "BLOCKED",
        "panel": panel,
        "admission": admission,
        "dataset_manifest": {"sha256": manifest_hash, "row_count": len(canonical_rows), "decision_cutoff": decision_cutoff, "cohort_count": len(symbols)},
        "replay_preflight_passed": gates_pass,
        "historical_replay_executed": False,
        "backtest_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "production_enabled": False,
        "next_required_action": "independent_human_review_and_explicit_research_dataset_admission" if gates_pass else "resolve_all_blocking_source_identity_calendar_ohlcv_or_corporate_action_evidence",
        "limitations": [
            "Preflight readiness is not permission to run a backtest; explicit dataset admission is a separate control.",
            "The dataset hash covers normalized panel rows and gate statuses, not the full raw archive.",
            "No performance, accuracy or probability claim is produced.",
        ],
    }
