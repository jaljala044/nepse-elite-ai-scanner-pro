"""Join official capture, first-trade verification and panel readiness reports."""
from __future__ import annotations
from typing import Mapping


def build_pilot_admission_bundle(
    *,
    capture_reports: Mapping[str, Mapping[str, object]],
    first_trade_report: Mapping[str, object],
    panel_readiness_report: Mapping[str, object],
    required_capture_ids: list[str],
) -> dict:
    """Produce one fail-closed evidence decision; never upgrades input reports."""
    if not required_capture_ids or len(required_capture_ids) != len(set(required_capture_ids)):
        raise ValueError("required_capture_ids must be nonempty and unique")
    missing = [capture_id for capture_id in required_capture_ids if capture_id not in capture_reports]
    blocked = [
        capture_id for capture_id in required_capture_ids
        if capture_id in capture_reports and capture_reports[capture_id].get("status") != "CAPTURE_VALIDATED"
    ]
    first_trade_complete = first_trade_report.get("all_cohort_first_trades_verified") is True
    panel_ready = panel_readiness_report.get("status") == "READY_FOR_BOUNDED_RESEARCH"
    all_capture_ok = not missing and not blocked
    ready = all_capture_ok and first_trade_complete and panel_ready
    reasons = []
    if missing: reasons.append({"reason": "required_capture_reports_missing", "capture_ids": missing})
    if blocked: reasons.append({"reason": "required_capture_reports_blocked", "capture_ids": blocked})
    if not first_trade_complete:
        reasons.append({"reason": "official_first_trade_verification_incomplete", "unresolved": first_trade_report.get("unresolved_count")})
    if not panel_ready:
        reasons.append({"reason": "historical_panel_not_ready", "panel_status": panel_readiness_report.get("status")})
    return {
        "status": "BOUNDED_PILOT_EVIDENCE_READY" if ready else "BLOCKED",
        "required_capture_count": len(required_capture_ids),
        "validated_capture_count": len(required_capture_ids) - len(missing) - len(blocked),
        "first_trade_verified_count": first_trade_report.get("verified_count", 0),
        "first_trade_cohort_count": first_trade_report.get("cohort_count", 0),
        "panel_status": panel_readiness_report.get("status"),
        "blocking_reasons": reasons,
        "bounded_research_review_allowed": ready,
        "canonical_promotion_allowed": False,
        "backtest_admission_allowed": False,
        "production_enabled": False,
        "limitations": [
            "This bundle joins upstream reports and does not independently re-fetch or re-hash source payloads.",
            "A ready bounded pilot still requires human review and independent source-completeness assessment.",
            "This report does not establish strategy performance or authorize live trading.",
        ],
    }
