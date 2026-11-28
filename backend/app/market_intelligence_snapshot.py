"""Fail-closed composition contract for the Part 2 NEPSE intelligence layer.

This module composes server-validated outputs; it does not calculate indicators,
upgrade evidence, infer missing values, or issue trading recommendations.
Only trusted backend callers should supply artifacts after validating their
underlying manifests and source records.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo
from math import isfinite
from typing import Any, Mapping

REQUIRED_MODULES = (
    "market_health",
    "index_intelligence",
    "sector_rotation",
    "relative_strength",
    "broker_profiles",
    "broker_sector_rotation",
    "wyckoff",
    "market_structure",
)
ALLOWED_STATUSES = {
    "observed",
    "research_only",
    "descriptive_only",
    "insufficient_evidence",
    "unavailable",
    "withheld",
}


def _aware_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_timezone_aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed


def _coverage(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not isfinite(parsed) or not 0 <= parsed <= 1:
        return None
    return parsed


def _nonempty_ids(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None
    normalized = [item.strip() for item in value]
    if len(normalized) != len(set(normalized)):
        return None
    return normalized


def _assess_artifact(name: str, artifact: Any, *, decision_date: date,
                     decision_timestamp: datetime) -> dict:
    base = {
        "module": name,
        "status": "unavailable",
        "admitted": False,
        "coverage_ratio": None,
        "source_ids": [],
        "evidence_ids": [],
        "data": None,
        "reasons": [],
        "as_of_date": None,
        "session_calendar_id": None,
    }
    if not isinstance(artifact, Mapping):
        return {**base, "reasons": ["artifact_missing_or_not_an_object"]}

    status = artifact.get("status")
    if not isinstance(status, str) or status not in ALLOWED_STATUSES:
        return {**base, "reasons": ["unrecognized_artifact_status"]}

    reasons = []
    try:
        as_of_date = date.fromisoformat(str(artifact["as_of_date"]))
    except (KeyError, TypeError, ValueError):
        as_of_date = None
        reasons.append("invalid_as_of_date")
    try:
        available_at = _aware_timestamp(artifact.get("available_at"), "available_at")
    except ValueError:
        available_at = None
        reasons.append("invalid_available_at")

    if as_of_date is not None and as_of_date > decision_date:
        reasons.append("artifact_as_of_after_decision_date")
    if available_at is not None and available_at > decision_timestamp:
        reasons.append("artifact_available_after_decision_time")

    source_ids = _nonempty_ids(artifact.get("source_ids"))
    evidence_ids = _nonempty_ids(artifact.get("evidence_ids"))
    if source_ids is None:
        reasons.append("source_ids_missing_or_invalid")
        source_ids = []
    if evidence_ids is None:
        reasons.append("evidence_ids_missing_or_invalid")
        evidence_ids = []

    coverage = _coverage(artifact.get("coverage_ratio"))
    if coverage is None or coverage <= 0:
        reasons.append("coverage_ratio_missing_or_invalid")
        coverage = None

    if artifact.get("source_validation_status") != "verified":
        reasons.append("source_not_verified")
    if artifact.get("finality_status") != "final":
        reasons.append("source_finality_not_verified")
    if artifact.get("evidence_gate_passed") is not True:
        reasons.append("upstream_evidence_gate_not_passed")
    if not isinstance(artifact.get("data"), Mapping):
        reasons.append("data_payload_missing_or_invalid")

    admitted = not reasons and status in {"observed", "research_only", "descriptive_only"}
    if not admitted and not reasons:
        reasons.append("upstream_module_not_ready")
    return {
        "module": name,
        "status": status if admitted else ("withheld" if status == "withheld" else "unavailable"),
        "admitted": admitted,
        "coverage_ratio": coverage,
        "as_of_date": as_of_date.isoformat() if admitted and as_of_date else None,
        "session_calendar_id": (artifact.get("session_calendar_id") if admitted else None),
        "source_ids": source_ids if admitted else [],
        "evidence_ids": evidence_ids if admitted else [],
        "data": dict(artifact["data"]) if admitted else None,
        "reasons": reasons,
    }


def build_market_intelligence_snapshot(
    artifacts: Mapping[str, Any] | None,
    *,
    decision_date: str,
    decision_time: str,
    required_modules: tuple[str, ...] = REQUIRED_MODULES,
) -> dict:
    """Compose a point-in-time Part 2 snapshot without generating a score.

    Each artifact must be a backend-produced envelope with verified source and
    finality status, evidence-gate attestation, unique lineage IDs, coverage,
    an as-of date and a timezone-aware availability timestamp. Missing or
    rejected modules remain unavailable; they are never treated as neutral or
    as zero activity.
    """
    try:
        cutoff_date = date.fromisoformat(decision_date)
    except (TypeError, ValueError):
        raise ValueError("decision_date_must_be_iso_date") from None
    cutoff_time = _aware_timestamp(decision_time, "decision_time")
    if cutoff_time.astimezone(ZoneInfo('Asia/Kathmandu')).date() < cutoff_date:
        raise ValueError("decision_time_precedes_decision_date")
    if not isinstance(required_modules, tuple) or not required_modules:
        raise ValueError("required_modules_must_be_a_nonempty_tuple")
    if any(not isinstance(name, str) or not name.strip() for name in required_modules):
        raise ValueError("required_module_names_must_be_nonempty")
    if len(required_modules) != len(set(required_modules)):
        raise ValueError("required_modules_must_be_unique")
    if artifacts is not None and not isinstance(artifacts, Mapping):
        raise ValueError("artifacts_must_be_an_object")

    supplied = artifacts or {}
    modules = {
        name: _assess_artifact(
            name, supplied.get(name), decision_date=cutoff_date,
            decision_timestamp=cutoff_time,
        )
        for name in required_modules
    }
    admitted_names = [name for name, item in modules.items() if item["admitted"]]
    missing_names = [name for name, item in modules.items() if not item["admitted"]]
    all_admitted = not missing_names

    # A unified snapshot must represent one exchange session. If any module
    # supplies a calendar identity, every admitted module must supply the same
    # identity; partial calendar metadata is not treated as aligned.
    admitted_as_of = {
        item["as_of_date"] for item in modules.values() if item["admitted"]
    }
    calendar_ids = [
        item["session_calendar_id"] for item in modules.values() if item["admitted"]
    ]
    calendar_aligned = (
        not calendar_ids
        or (
            all(isinstance(value, str) and value.strip() for value in calendar_ids)
            and len(set(calendar_ids)) == 1
        )
    )
    as_of_aligned = len(admitted_as_of) <= 1
    alignment_ok = as_of_aligned and calendar_aligned
    alignment = {
        "status": "aligned" if alignment_ok else "mismatch",
        "as_of_dates": sorted(admitted_as_of),
        "session_calendar_ids": sorted({
            value for value in calendar_ids if isinstance(value, str) and value.strip()
        }),
        "reasons": [
            reason for condition, reason in (
                (not as_of_aligned, "module_as_of_date_mismatch"),
                (not calendar_aligned, "session_calendar_identity_missing_or_mismatched"),
            ) if condition
        ],
    }
    source_ids = sorted({value for item in modules.values() for value in item["source_ids"]})
    evidence_ids = sorted({value for item in modules.values() for value in item["evidence_ids"]})

    return {
        "status": "research_only" if all_admitted and alignment_ok else (
            "partial_evidence" if admitted_names else "insufficient_evidence"
        ),
        "alignment": alignment,
        "decision_date": cutoff_date.isoformat(),
        "decision_time": cutoff_time.isoformat(),
        "required_modules": list(required_modules),
        "admitted_modules": admitted_names,
        "missing_modules": missing_names,
        "module_count": len(required_modules),
        "admitted_module_count": len(admitted_names),
        "coverage_ratio": len(admitted_names) / len(required_modules),
        "modules": modules,
        "source_ids": source_ids,
        "evidence_ids": evidence_ids,
        "production_score": None,
        "probability": None,
        "signals_enabled": False,
        "trade_actions_enabled": False,
        "recommendation": "NOT_EVALUATED",
        "policy": "missing_or_unverified_evidence_remains_unknown_no_neutral_imputation",
        "interpretation_boundary": (
            "Composition only. This snapshot does not independently validate "
            "upstream sources, prove broker intent or ownership, or authorize "
            "BUY/SELL/HOLD decisions."
        ),
    }
