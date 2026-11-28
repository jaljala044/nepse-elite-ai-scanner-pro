"""Server-owned HMAC review attestations for calendar and capture policies.

HMAC protects internal configuration integrity. It does not prove a human's
legal identity, NEPSE authority, publisher ownership or official exchange status.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REVIEW_SCOPES = {"calendar_session", "capture_policy"}


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_timezone_aware_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_invalid_iso_timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_timezone_aware_required")
    return parsed.astimezone(timezone.utc)


def _key(key: str | None) -> bytes:
    if not isinstance(key, str) or len(key) < 32:
        raise ValueError("review_hmac_key_must_be_at_least_32_characters")
    return key.encode("utf-8")


def _signature(payload: dict[str, Any], key: str) -> str:
    body = {name: value for name, value in payload.items() if name != "signature_hmac_sha256"}
    return hmac.new(_key(key), _canonical(body), hashlib.sha256).hexdigest()


def sign_review_registry(registry: dict[str, Any], key: str) -> dict[str, Any]:
    result = dict(registry)
    result.pop("signature_hmac_sha256", None)
    result["signature_hmac_sha256"] = _signature(result, key)
    return result


def _evidence_digest(evidence: dict[str, Any]) -> str:
    body = {name: value for name, value in evidence.items() if name != "review_attestation"}
    return hashlib.sha256(_canonical(body)).hexdigest()


def sign_review_attestation(
    evidence: dict[str, Any], *, reviewer_id: str, scope: str,
    reviewed_at: str, key: str,
) -> dict[str, Any]:
    if scope not in REVIEW_SCOPES:
        raise ValueError("review_scope_unsupported")
    payload = {
        "reviewer_id": reviewer_id,
        "scope": scope,
        "decision": "approved",
        "reviewed_at": _utc(reviewed_at, "reviewed_at").isoformat(),
        "evidence_sha256": _evidence_digest(evidence),
    }
    return {**payload, "signature_hmac_sha256": _signature(payload, key)}


def load_source_quality_review_registry(
    registry_path: str | Path | None, hmac_key: str | None,
    *, decision_time: str,
) -> dict[str, Any]:
    empty = {"status": "not_configured", "reviewers": {}, "review_attestation_allowed": False}
    if not registry_path or not hmac_key:
        return empty
    try:
        _key(hmac_key)
        raw = Path(registry_path).read_bytes()
        if len(raw) > 512 * 1024:
            raise ValueError("review_registry_exceeds_512_kib")
        registry = json.loads(raw.decode("utf-8"))
        if not isinstance(registry, dict) or registry.get("schema_version") != 1:
            raise ValueError("review_registry_schema_invalid")
        if not hmac.compare_digest(
            str(registry.get("signature_hmac_sha256") or ""),
            _signature(registry, hmac_key),
        ):
            raise ValueError("review_registry_signature_invalid")
        generated = _utc(registry.get("generated_at"), "generated_at")
        cutoff = _utc(decision_time, "decision_time")
        if generated > cutoff:
            raise ValueError("review_registry_generated_after_decision_time")
        entries = registry.get("reviewers")
        if not isinstance(entries, list) or not entries:
            raise ValueError("reviewer_entries_required")
        reviewers = {}
        for item in entries:
            if not isinstance(item, dict):
                raise ValueError("reviewer_entry_invalid")
            reviewer_id = item.get("reviewer_id")
            scopes = item.get("allowed_scopes")
            if (not isinstance(reviewer_id, str) or not reviewer_id.strip()
                    or reviewer_id in reviewers or not isinstance(scopes, list)
                    or not scopes or any(scope not in REVIEW_SCOPES for scope in scopes)
                    or item.get("status") != "approved"):
                raise ValueError("reviewer_entry_contract_invalid")
            reviewers[reviewer_id] = {"allowed_scopes": sorted(set(scopes)), "status": "approved"}
        return {
            "status": "review_registry_loaded", "reviewers": reviewers,
            "registry_sha256": hashlib.sha256(raw).hexdigest(),
            "generated_at": generated.isoformat(),
            "review_attestation_allowed": True,
            "verified": False,
            "limitations": [
                "HMAC establishes internal payload integrity, not the reviewer's real-world identity.",
                "Reviewer scope approval is an application control, not NEPSE certification.",
            ],
        }
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {**empty, "status": "rejected", "reason": str(exc)}


def validate_review_attestation(
    evidence: dict[str, Any], *, scope: str,
    registry: dict[str, Any], hmac_key: str | None,
    decision_time: str,
) -> dict[str, Any]:
    if scope not in REVIEW_SCOPES:
        return {"eligible": False, "reason": "review_scope_unsupported"}
    if registry.get("status") != "review_registry_loaded" or not registry.get("review_attestation_allowed"):
        return {"eligible": False, "reason": "review_registry_unavailable"}
    try:
        key = hmac_key
        _key(key)
        cutoff = _utc(decision_time, "decision_time")
        attestation = evidence.get("review_attestation")
        if not isinstance(attestation, dict):
            raise ValueError("review_attestation_missing")
        reviewer_id = attestation.get("reviewer_id")
        reviewer = registry["reviewers"].get(reviewer_id)
        if not reviewer or scope not in reviewer["allowed_scopes"]:
            raise ValueError("reviewer_scope_not_approved")
        if attestation.get("scope") != scope or attestation.get("decision") != "approved":
            raise ValueError("review_attestation_scope_or_decision_invalid")
        reviewed = _utc(attestation.get("reviewed_at"), "reviewed_at")
        if reviewed > cutoff:
            raise ValueError("review_attestation_after_decision_time")
        if attestation.get("evidence_sha256") != _evidence_digest(evidence):
            raise ValueError("reviewed_evidence_payload_hash_mismatch")
        if not hmac.compare_digest(
            str(attestation.get("signature_hmac_sha256") or ""),
            _signature(attestation, key),
        ):
            raise ValueError("review_attestation_signature_invalid")
        return {
            "eligible": True, "reviewer_id": reviewer_id,
            "reviewed_at": reviewed.isoformat(), "scope": scope,
        }
    except (TypeError, ValueError, KeyError) as exc:
        return {"eligible": False, "reason": str(exc)}
