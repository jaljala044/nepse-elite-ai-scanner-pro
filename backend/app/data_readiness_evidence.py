"""Assemble explicit project evidence for the fail-closed training gate."""
from __future__ import annotations

import math
import re
from app.training_readiness import REQUIRED_GATES, evaluate_training_readiness


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _coverage_passes(value, threshold: float = 0.98) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(number) and threshold <= number <= 1.0


def assemble_training_evidence(*, universe_report: dict | None,
                               session_reports: list[dict] | None,
                               provenance_reports: list[dict] | None,
                               ohlcv_report: dict | None,
                               broker_report: dict | None,
                               point_in_time_report: dict | None,
                               corporate_action_reviewed: bool = False,
                               holdout_protocol_id: str | None = None,
                               historical_coverage: float | None = None,
                               evidence_snapshot_id: str | None = None) -> dict:
    """Translate upstream reports into gate evidence; absent reports fail closed."""
    universe_ok = bool(universe_report and universe_report.get("manifest_verified") is True)
    sessions = session_reports or []
    sessions_ok = bool(sessions) and all(
        item.get("status") == "verified"
        and item.get("session_state") in {"confirmed_trading_session",
                                          "confirmed_exchange_closure",
                                          "exceptional_session"}
        for item in sessions
    )
    provenance = provenance_reports or []
    rights_ok = bool(provenance) and all(
        item.get("training_eligibility", {}).get("rights_clearance") is True
        for item in provenance
    )
    lineage_ok = bool(provenance) and all(
        _SHA256.fullmatch(str(item.get("capture", {}).get("payload_sha256", ""))) is not None
        and bool(item.get("capture", {}).get("source_record_id"))
        and _SHA256.fullmatch(str(item.get("provenance_sha256", ""))) is not None
        for item in provenance
    )
    ohlcv_ok = bool(ohlcv_report) and (
        ohlcv_report.get("integrity_status") == "passed"
        and ohlcv_report.get("unresolved_exception_count") == 0
    )
    broker_ok = bool(broker_report) and (
        broker_report.get("identity_policy_status") == "passed"
        and broker_report.get("unresolved_identity_policy_violations") == 0
    )
    pit_ok = bool(point_in_time_report) and (
        point_in_time_report.get("leakage_status") == "passed"
        and point_in_time_report.get("future_input_count") == 0
        and point_in_time_report.get("premature_label_count") == 0
    )
    coverage_ok = _coverage_passes(historical_coverage)
    values = {
        "universe_verified": universe_ok,
        "session_calendar_verified": sessions_ok,
        "source_rights_cleared": rights_ok,
        "source_lineage_complete": lineage_ok,
        "ohlcv_integrity_passed": ohlcv_ok,
        "broker_identity_policy_passed": broker_ok,
        "point_in_time_leakage_checks_passed": pit_ok,
        "corporate_action_policy_reviewed": corporate_action_reviewed is True,
        "historical_coverage_threshold_met": coverage_ok,
        "holdout_protocol_defined": bool(holdout_protocol_id and holdout_protocol_id.strip()),
        "ohlcv_coverage": (ohlcv_report or {}).get("coverage_ratio"),
        "broker_identity_coverage": (broker_report or {}).get("verified_amount_coverage"),
        "evidence_snapshot_id": evidence_snapshot_id,
    }
    return {
        **values,
        "derived_gate_checks": {key: values[key] for key in REQUIRED_GATES},
        "training_readiness": evaluate_training_readiness(values),
        "policy": "derive_only_from_explicit_upstream_evidence_missing_means_blocked",
    }
