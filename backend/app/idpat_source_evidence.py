"""Trusted-report adapter for IDPAT gates.

Only backend-generated validation reports should be passed here. Client-supplied
claims are not authenticated by this module or by the HTTP request schema.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation


GATE_REQUIREMENTS = {
    "market": {
        "fields": {
            "index_integrity_status": "passed",
            "calendar_status": "verified",
            "market_summary_finality_verified": True,
        },
    },
    "sector": {
        "fields": {
            "membership_status": "verified",
            "sector_data_status": "verified",
        },
        "ratios": {"price_coverage_ratio": Decimal("0.98")},
    },
    "broker": {
        "fields": {
            "reconciliation_status": "passed",
            "identity_policy_status": "passed",
        },
        "ratios": {"verified_amount_coverage": Decimal("0.95")},
    },
    "liquidity": {
        "fields": {
            "ohlcv_integrity_status": "passed",
            "turnover_status": "verified",
        },
        "ratios": {"per_security_coverage_ratio": Decimal("0.98")},
    },
    "execution": {
        "fields": {
            "session_calendar_status": "verified",
            "execution_constraints_status": "verified",
            "next_session_history_complete": True,
        },
    },
    "corporate_actions": {
        "fields": {
            "registry_status": "verified",
            "source_universe_completeness_verified": True,
            "point_in_time_eligible": True,
        },
    },
    "source_quality": {
        "fields": {
            "raw_hashes_verified": True,
            "lineage_complete": True,
            "rights_clearance": True,
            "unresolved_conflict_count": 0,
        },
    },
}


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _ratio(value, minimum):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return parsed.is_finite() and minimum <= parsed <= Decimal("1")


def derive_idpat_gate_evidence(reports, *, decision_time):
    """Derive gate attestations from validated report envelopes, fail closed."""
    cutoff = _timestamp(decision_time)
    if cutoff is None:
        raise ValueError("decision_time_must_be_timezone_aware")
    reports = reports if isinstance(reports, dict) else {}
    evidence, blocked = {}, []
    for gate, spec in GATE_REQUIREMENTS.items():
        report = reports.get(gate)
        reason = None
        if not isinstance(report, dict):
            reason = "validated_report_missing"
        elif report.get("report_status") != "validated":
            reason = "report_not_validated"
        elif not isinstance(report.get("source_id"), str) or not report["source_id"].strip():
            reason = "source_id_missing"
        elif not isinstance(report.get("evidence_id"), str) or not report["evidence_id"].strip():
            reason = "evidence_id_missing"
        else:
            available = _timestamp(report.get("available_at"))
            if available is None:
                reason = "available_at_invalid"
            elif available > cutoff:
                reason = "report_available_after_decision_time"
            else:
                for field, expected in spec["fields"].items():
                    if report.get(field) != expected:
                        reason = f"required_evidence_failed:{field}"
                        break
                if reason is None:
                    for field, minimum in spec.get("ratios", {}).items():
                        if not _ratio(report.get(field), minimum):
                            reason = f"coverage_below_threshold_or_invalid:{field}"
                            break
        evidence[gate] = {
            "status": "verified" if reason is None else "blocked",
            "reason": reason,
            "source_id": report.get("source_id") if isinstance(report, dict) else None,
            "evidence_id": report.get("evidence_id") if isinstance(report, dict) else None,
            "available_at": report.get("available_at") if isinstance(report, dict) else None,
        }
        if reason:
            blocked.append(f"{gate}:{reason}")
    gate_evidence = {
        name: {
            "status": "verified",
            "source_id": item["source_id"],
            "evidence_id": item["evidence_id"],
            "available_at": item["available_at"],
        }
        for name, item in evidence.items() if item["status"] == "verified"
    }
    return {
        "status": "ready_for_research_review" if not blocked else "blocked",
        "decision_time": cutoff.isoformat(),
        "gates": evidence,
        "blocked_gates": blocked,
        "gate_evidence": gate_evidence,
        "production_enabled": False,
        "policy": "backend_validated_reports_only_missing_or_late_evidence_blocks",
    }
