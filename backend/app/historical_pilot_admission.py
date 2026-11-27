"""Join validated source captures, first-trade verification and panel readiness."""
from __future__ import annotations
from typing import Mapping


def build_pilot_admission_bundle(
    *,
    capture_reports: Mapping[str, Mapping[str, object]],
    first_trade_report: Mapping[str, object],
    panel_readiness_report: Mapping[str, object],
    required_capture_keys: list[str],
) -> dict:
    """Validate required mapping keys against each report's manifest capture identity."""
    if not required_capture_keys or len(required_capture_keys) != len(set(required_capture_keys)):
        raise ValueError("required_capture_keys must be nonempty and unique")
    missing, blocked, invalid_identity = [], [], []
    actual_ids = []
    for key in required_capture_keys:
        report = capture_reports.get(key)
        if not isinstance(report, Mapping):
            missing.append(key)
            continue
        if report.get("status") != "CAPTURE_VALIDATED":
            blocked.append(key)
            continue
        capture_id = report.get("capture_id")
        if report.get("capture_key") != key or not isinstance(capture_id, str) or not capture_id.strip():
            invalid_identity.append({"capture_key": key, "capture_id": capture_id, "reason": "capture_report_identity_missing_or_mismatched"})
            continue
        actual_ids.append(capture_id)
    duplicate_ids = sorted({capture_id for capture_id in actual_ids if actual_ids.count(capture_id) > 1})
    if duplicate_ids:
        invalid_identity.extend({"capture_id": capture_id, "reason": "duplicate_manifest_capture_id"} for capture_id in duplicate_ids)

    first_trade_complete = first_trade_report.get("all_cohort_first_trades_verified") is True
    panel_ready = panel_readiness_report.get("status") == "READY_FOR_BOUNDED_RESEARCH"
    all_capture_ok = not missing and not blocked and not invalid_identity
    ready = all_capture_ok and first_trade_complete and panel_ready
    reasons = []
    if missing: reasons.append({"reason": "required_capture_reports_missing", "capture_keys": missing})
    if blocked: reasons.append({"reason": "required_capture_reports_blocked", "capture_keys": blocked})
    if invalid_identity: reasons.append({"reason": "capture_manifest_identity_invalid", "details": invalid_identity})
    if not first_trade_complete:
        reasons.append({"reason": "official_first_trade_verification_incomplete", "unresolved": first_trade_report.get("unresolved_count")})
    if not panel_ready:
        reasons.append({"reason": "historical_panel_not_ready", "panel_status": panel_readiness_report.get("status")})
    return {
        "status": "BOUNDED_PILOT_EVIDENCE_READY" if ready else "BLOCKED",
        "required_capture_count": len(required_capture_keys),
        "validated_capture_count": len(actual_ids) if all_capture_ok else max(0, len(actual_ids) - len(duplicate_ids)),
        "required_capture_keys": required_capture_keys,
        "validated_capture_ids": sorted(actual_ids),
        "blocking_reasons": reasons,
        "first_trade_verified_count": first_trade_report.get("verified_count", 0),
        "first_trade_cohort_count": first_trade_report.get("cohort_count", 0),
        "panel_status": panel_readiness_report.get("status"),
        "bounded_research_review_allowed": ready,
        "canonical_promotion_allowed": False,
        "backtest_admission_allowed": False,
        "production_enabled": False,
        "limitations": [
            "This bundle joins upstream reports and does not independently re-fetch or re-hash source payloads.",
            "Each required capture key must resolve to a validated report with a matching key and unique manifest capture ID.",
            "A ready bounded pilot still requires human review and independent source-completeness assessment.",
            "This report does not establish strategy performance or authorize live trading.",
        ],
    }
