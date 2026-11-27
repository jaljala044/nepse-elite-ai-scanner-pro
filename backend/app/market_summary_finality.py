"""Signed finality and session-completeness gate for NEPSE market summaries.

This gate consumes an already source-validated review-only capture plus a
separately reviewed exact session calendar. It does not discover holidays or
authenticate calendar truth. A trusted reviewer must attest the calendar and
capture; the signature key must be held outside the repository.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import hmac
import json
from typing import Any


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_must_be_timezone_aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _date(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_iso_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field}_must_be_iso_date") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{field}_must_be_iso_date")
    return value


def _digest(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(char in "0123456789abcdef" for char in value.lower()))


def attestation_payload(attestation: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in attestation.items() if key != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sign_finality_attestation(attestation: dict[str, Any], reviewer_key: bytes) -> str:
    """Signing helper for controlled review tooling; never store keys in source."""
    if not isinstance(reviewer_key, bytes) or len(reviewer_key) < 32:
        raise ValueError("reviewer_key_must_be_at_least_32_bytes")
    return hmac.new(reviewer_key, attestation_payload(attestation), hashlib.sha256).hexdigest()


def validate_market_summary_finality(
    capture: dict[str, Any],
    *,
    session_calendar: dict[str, Any],
    attestation: dict[str, Any],
    reviewer_keys: dict[str, bytes],
    decision_time: str,
) -> dict[str, Any]:
    """Require signed independent finality review and exact session reconciliation."""
    cutoff = _utc(decision_time, "decision_time")
    if capture.get("status") != "review_only" or capture.get("promotion_allowed") is not False:
        raise ValueError("capture_must_be_source_validated_review_only")
    capture_digest = capture.get("source_payload_sha256")
    if not _digest(capture_digest):
        raise ValueError("capture_payload_digest_invalid")
    rows = capture.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("capture_rows_missing")
    observed = []
    for row in rows:
        if not isinstance(row, dict) or row.get("source_payload_sha256") != capture_digest:
            raise ValueError("capture_row_provenance_mismatch")
        observed.append(_date(row.get("session_date"), "capture_session_date"))
    if observed != sorted(set(observed)):
        raise ValueError("capture_sessions_must_be_unique_ascending")

    if not isinstance(session_calendar, dict) or session_calendar.get("status") != "verified":
        raise ValueError("verified_session_calendar_required")
    calendar_id = session_calendar.get("calendar_id")
    calendar_digest = session_calendar.get("calendar_sha256")
    calendar_source = session_calendar.get("source_id")
    if not isinstance(calendar_id, str) or not calendar_id.strip():
        raise ValueError("calendar_id_required")
    if not isinstance(calendar_source, str) or not calendar_source.strip():
        raise ValueError("calendar_source_id_required")
    if not _digest(calendar_digest):
        raise ValueError("calendar_sha256_invalid")
    calendar_dates = session_calendar.get("session_dates")
    if not isinstance(calendar_dates, list) or not calendar_dates:
        raise ValueError("calendar_session_dates_required")
    normalized_calendar = [_date(item, "calendar_session_date") for item in calendar_dates]
    if normalized_calendar != sorted(set(normalized_calendar)):
        raise ValueError("calendar_sessions_must_be_unique_ascending")

    if not isinstance(attestation, dict):
        raise ValueError("finality_attestation_required")
    reviewer = attestation.get("reviewer")
    key = reviewer_keys.get(reviewer) if isinstance(reviewer, str) else None
    signature = attestation.get("signature")
    if not isinstance(key, bytes) or len(key) < 32 or not isinstance(signature, str):
        raise ValueError("trusted_reviewer_signature_required")
    expected_signature = sign_finality_attestation(attestation, key)
    if not hmac.compare_digest(expected_signature, signature):
        raise ValueError("finality_attestation_signature_invalid")
    if attestation.get("decision") != "final":
        raise ValueError("reviewer_did_not_attest_finality")
    if not isinstance(attestation.get("validation_id"), str) or not attestation["validation_id"].strip():
        raise ValueError("finality_validation_id_required")
    refs = attestation.get("evidence_refs")
    if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or not x.strip() for x in refs):
        raise ValueError("independent_finality_evidence_refs_required")
    reviewed_at = _utc(attestation.get("reviewed_at"), "reviewed_at")
    if reviewed_at > cutoff:
        raise ValueError("finality_review_after_decision_time")
    if attestation.get("capture_payload_sha256") != capture_digest:
        raise ValueError("attestation_capture_digest_mismatch")
    if attestation.get("calendar_sha256") != calendar_digest:
        raise ValueError("attestation_calendar_digest_mismatch")
    if attestation.get("calendar_id") != calendar_id:
        raise ValueError("attestation_calendar_id_mismatch")
    if session_calendar.get("available_at") is None or _utc(
            session_calendar.get("available_at"), "calendar_available_at") > cutoff:
        raise ValueError("calendar_not_available_at_decision_time")
    if _utc(capture.get("retrieved_at"), "capture_retrieved_at") > cutoff:
        raise ValueError("capture_not_available_at_decision_time")

    missing = sorted(set(normalized_calendar) - set(observed))
    unexpected = sorted(set(observed) - set(normalized_calendar))
    if missing or unexpected:
        return {
            "status": "insufficient_evidence",
            "finality_status": "unverified",
            "evidence_gate_passed": False,
            "promotion_allowed": False,
            "missing_sessions": missing,
            "unexpected_sessions": unexpected,
            "capture_sessions": len(observed),
            "calendar_sessions_in_capture_range": len([
                day for day in normalized_calendar
                if observed[0] <= day <= observed[-1]
            ]),
            "reason": "capture_calendar_session_mismatch",
        }
    return {
        "status": "attested_final",
        "finality_status": "final",
        "evidence_gate_passed": True,
        "promotion_allowed": True,
        "capture_payload_sha256": capture_digest,
        "calendar_id": calendar_id,
        "calendar_sha256": calendar_digest,
        "calendar_source_id": calendar_source,
        "reviewer": reviewer,
        "validation_id": attestation["validation_id"],
        "reviewed_at": reviewed_at.isoformat(),
        "evidence_refs": list(refs),
        "session_count": len(observed),
        "first_session": observed[0],
        "last_session": observed[-1],
        "evidence_class": "signed_independent_finality_and_calendar_attestation",
        "limitations": [
            "This gate verifies the signed review and exact date reconciliation, not the truth of reviewer claims.",
            "Calendar source authority and reviewer key governance must be controlled outside this module.",
            "The caller must independently pin and verify the source capture and calendar artifacts before invoking this gate.",
        ],
    }
