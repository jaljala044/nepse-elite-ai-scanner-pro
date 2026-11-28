"""Server-side, HMAC-attested sector membership registry.

A valid signature proves an internal reviewer attested to a payload; it does
not authenticate NEPSE or turn a secondary publisher into an exchange source.
Registry outputs remain research-only and cannot authorize ranking or trades.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
from pathlib import Path
from typing import Any

from .sector_membership_manifest import audit_sector_membership_manifest


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _signature(value: dict[str, Any], key: str) -> str:
    return hmac.new(key.encode("utf-8"), _canonical(value), sha256).hexdigest()


def sign_registry_payload(payload: dict[str, Any], key: str) -> str:
    """Helper for controlled registry publishing and deterministic tests."""
    if not isinstance(key, str) or len(key) < 32:
        raise ValueError("registry_hmac_key_must_be_at_least_32_characters")
    body = {name: value for name, value in payload.items() if name != "registry_signature_hmac_sha256"}
    return _signature(body, key)


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_timezone_aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def load_sector_evidence_registry(
    registry_path: str | Path | None,
    hmac_key: str | None,
    *,
    expected_symbols: list[str],
    decision_time: str,
) -> dict[str, Any]:
    """Load and audit the server-owned registry; fail closed on every mismatch."""
    empty = {
        "status": "not_configured", "membership": {}, "coverage_pct": 0.0,
        "verified": False, "admission_allowed": False,
        "production_recommendations_enabled": False,
    }
    if not registry_path or not hmac_key:
        return empty
    if not isinstance(hmac_key, str) or len(hmac_key) < 32:
        return {**empty, "status": "invalid_configuration", "reason": "hmac_key_too_short"}
    try:
        raw = Path(registry_path).read_bytes()
        if len(raw) > 5 * 1024 * 1024:
            return {**empty, "status": "rejected", "reason": "registry_exceeds_5_mib"}
        registry = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {**empty, "status": "unavailable", "reason": "registry_file_unavailable_or_invalid"}
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        return {**empty, "status": "rejected", "reason": "unsupported_registry_schema"}
    supplied = registry.get("registry_signature_hmac_sha256")
    body = {name: value for name, value in registry.items() if name != "registry_signature_hmac_sha256"}
    expected_signature = _signature(body, hmac_key)
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied, expected_signature):
        return {**empty, "status": "rejected", "reason": "registry_signature_invalid"}
    try:
        generated_at = _utc(registry.get("generated_at"), "generated_at")
        cutoff = _utc(decision_time, "decision_time")
    except ValueError as exc:
        return {**empty, "status": "rejected", "reason": str(exc)}
    if generated_at > cutoff:
        return {**empty, "status": "rejected", "reason": "registry_generated_after_decision_time"}
    allowed = registry.get("allowed_sector_codes")
    entries = registry.get("entries")
    if (not isinstance(allowed, list) or not allowed
            or any(not isinstance(code, str) or not code.strip() or code != code.strip() for code in allowed)
            or len(set(allowed)) != len(allowed) or not isinstance(entries, list)):
        return {**empty, "status": "rejected", "reason": "registry_contract_invalid"}
    membership: dict[str, str] = {}
    audited = []
    seen_symbols: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            return {**empty, "status": "rejected", "reason": f"entry_{index}_invalid"}
        attestation = entry.get("reviewer_attestation")
        manifest = entry.get("manifest")
        if not isinstance(attestation, dict) or not isinstance(manifest, dict):
            return {**empty, "status": "rejected", "reason": f"entry_{index}_attestation_or_manifest_missing"}
        signed = {name: value for name, value in attestation.items() if name != "signature_hmac_sha256"}
        signature = attestation.get("signature_hmac_sha256")
        if not isinstance(signature, str) or not hmac.compare_digest(signature, _signature(signed, hmac_key)):
            return {**empty, "status": "rejected", "reason": f"entry_{index}_reviewer_signature_invalid"}
        reviewer = attestation.get("reviewer_id")
        scope = attestation.get("scope")
        decision = attestation.get("decision")
        try:
            reviewed_at = _utc(attestation.get("reviewed_at"), "reviewed_at")
        except ValueError as exc:
            return {**empty, "status": "rejected", "reason": str(exc)}
        if (not isinstance(reviewer, str) or not reviewer.strip()
                or scope != "sector_membership_research"
                or decision != "approved_for_research"
                or reviewed_at > cutoff):
            return {**empty, "status": "rejected", "reason": f"entry_{index}_reviewer_attestation_invalid"}
        try:
            audit = audit_sector_membership_manifest(
                manifest, expected_symbols=entry.get("expected_symbols"),
                allowed_sector_codes=set(allowed), decision_time=decision_time,
                minimum_coverage=1.0,
            )
        except (ValueError, TypeError) as exc:
            return {**empty, "status": "rejected", "reason": f"entry_{index}_manifest_audit_failed:{exc}"}
        if audit["status"] != "review_ready":
            return {**empty, "status": "insufficient_evidence", "reason": f"entry_{index}_membership_coverage_incomplete"}
        overlap = seen_symbols.intersection(audit["membership"])
        if overlap:
            return {**empty, "status": "rejected", "reason": "duplicate_symbol_across_registry_entries"}
        seen_symbols.update(audit["membership"])
        membership.update(audit["membership"])
        audited.append({
            "source_id": audit["source_id"],
            "manifest_sha256": audit["manifest_sha256"],
            "reviewer_id": reviewer,
            "reviewed_at": reviewed_at.isoformat(),
            "membership_count": len(audit["membership"]),
            "evidence_class": "internally_attested_secondary_or_primary_source_review",
        })
    expected = {str(symbol).strip().upper() for symbol in expected_symbols}
    missing = sorted(expected - set(membership))
    unexpected = sorted(set(membership) - expected)
    coverage = len(expected.intersection(membership)) / len(expected) if expected else 0.0
    if missing or unexpected or not expected:
        return {
            **empty, "status": "insufficient_evidence", "membership": {},
            "coverage_pct": round(coverage * 100, 2),
            "missing_symbols": missing, "unexpected_symbols": unexpected,
            "reason": "registry_does_not_exactly_cover_candidate_universe",
        }
    return {
        "status": "internally_attested_research_only",
        "membership": membership,
        "coverage_pct": round(coverage * 100, 2),
        "audited_entries": audited,
        "generated_at": generated_at.isoformat(),
        "registry_sha256": sha256(raw).hexdigest(),
        "verified": False,
        "admission_allowed": False,
        "production_recommendations_enabled": False,
        "limitations": [
            "HMAC verifies internal registry integrity and reviewer attestation, not publisher authenticity.",
            "Internal review does not establish official NEPSE sector membership.",
            "This registry is research-only and cannot authorize scoring, ranking or trade recommendations.",
        ],
    }
