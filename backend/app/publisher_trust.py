"""Reviewed publisher trust and explicit evidence freshness policy.

Publisher IDs supplied by observations are identifiers, not proof of
independence. Only entries in a server-owned, HMAC-attested registry can map
publishers to reviewed ownership groups and approved hostnames. Missing registry
or freshness policy means unknown/unconfigured and fails closed for corroboration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_timezone_aware_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_timezone_aware_required") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_timezone_aware_required")
    return parsed.astimezone(timezone.utc)


def sign_trust_payload(payload: dict[str, Any], key: str) -> str:
    if not isinstance(key, str) or len(key) < 32:
        raise ValueError("trust_hmac_key_must_be_at_least_32_characters")
    body = {k: v for k, v in payload.items() if k != "signature_hmac_sha256"}
    return hmac.new(key.encode(), _canonical(body), sha256).hexdigest()


def _verify_signature(payload: dict[str, Any], key: str) -> bool:
    supplied = payload.get("signature_hmac_sha256")
    return isinstance(supplied, str) and hmac.compare_digest(
        supplied, sign_trust_payload(payload, key)
    )


def load_publisher_trust_registry(
    registry_path: str | Path | None,
    hmac_key: str | None,
    *,
    decision_time: str,
) -> dict[str, Any]:
    """Load reviewed publisher/domain/ownership-group relationships."""
    empty = {
        "status": "not_configured", "publishers": {}, "verified": False,
        "independence_assessment_allowed": False,
    }
    if not registry_path or not hmac_key:
        return empty
    if not isinstance(hmac_key, str) or len(hmac_key) < 32:
        return {**empty, "status": "invalid_configuration", "reason": "hmac_key_too_short"}
    try:
        raw = Path(registry_path).read_bytes()
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("registry_exceeds_2_mib")
        registry = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {**empty, "status": "unavailable_or_invalid", "reason": str(exc)}
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        return {**empty, "status": "rejected", "reason": "unsupported_registry_schema"}
    if not _verify_signature(registry, hmac_key):
        return {**empty, "status": "rejected", "reason": "registry_signature_invalid"}
    try:
        generated = _utc(registry.get("generated_at"), "generated_at")
        cutoff = _utc(decision_time, "decision_time")
    except ValueError as exc:
        return {**empty, "status": "rejected", "reason": str(exc)}
    if generated > cutoff:
        return {**empty, "status": "rejected", "reason": "registry_generated_after_decision_time"}
    entries = registry.get("publishers")
    if not isinstance(entries, list) or not entries:
        return {**empty, "status": "rejected", "reason": "publisher_entries_required"}

    result: dict[str, Any] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            return {**empty, "status": "rejected", "reason": f"publisher_{index}_invalid"}
        publisher_id = entry.get("publisher_id")
        group_id = entry.get("ownership_group_id")
        hosts = entry.get("approved_hosts")
        attestation = entry.get("reviewer_attestation")
        if (not isinstance(publisher_id, str) or not publisher_id.strip()
                or not isinstance(group_id, str) or not group_id.strip()
                or not isinstance(hosts, list) or not hosts
                or any(not isinstance(host, str) or not host.strip() for host in hosts)
                or len(set(hosts)) != len(hosts)
                or not isinstance(attestation, dict)):
            return {**empty, "status": "rejected", "reason": f"publisher_{index}_contract_invalid"}
        if publisher_id in result:
            return {**empty, "status": "rejected", "reason": "duplicate_publisher_id"}
        if not _verify_signature(attestation, hmac_key):
            return {**empty, "status": "rejected", "reason": f"publisher_{index}_reviewer_signature_invalid"}
        try:
            reviewed = _utc(attestation.get("reviewed_at"), "reviewed_at")
        except ValueError as exc:
            return {**empty, "status": "rejected", "reason": str(exc)}
        if (attestation.get("decision") != "approved"
                or attestation.get("reviewer_id") is None
                or not str(attestation.get("reviewer_id")).strip()
                or attestation.get("scope") != "publisher_identity_and_affiliation"
                or reviewed > cutoff):
            return {**empty, "status": "rejected", "reason": f"publisher_{index}_attestation_invalid"}
        normalized_hosts = []
        for host in hosts:
            parsed = urlparse("//" + host)
            normalized = (parsed.hostname or "").lower()
            if not normalized or parsed.path or parsed.port or normalized != host.lower():
                return {**empty, "status": "rejected", "reason": f"publisher_{index}_host_invalid"}
            normalized_hosts.append(normalized)
        result[publisher_id] = {
            "ownership_group_id": group_id,
            "approved_hosts": sorted(set(normalized_hosts)),
            "reviewer_id": attestation["reviewer_id"],
            "reviewed_at": reviewed.isoformat(),
            "status": "reviewed_approved",
        }
    return {
        "status": "reviewed_registry_loaded", "publishers": result,
        "registry_sha256": sha256(raw).hexdigest(),
        "generated_at": generated.isoformat(),
        "verified": False,
        "independence_assessment_allowed": True,
        "limitations": [
            "Internal reviewer attestation is not legal proof of beneficial ownership.",
            "Ownership-group relationships are only as reliable as the reviewed registry.",
            "Registry approval does not establish official NEPSE source status.",
        ],
    }


def load_evidence_freshness_policy(
    policy_path: str | Path | None,
    hmac_key: str | None,
    *,
    decision_time: str,
) -> dict[str, Any]:
    """Load explicit per-source-class maximum age; never invent an SLA."""
    empty = {"status": "unconfigured", "max_age_seconds": {}, "freshness_assessment_allowed": False}
    if not policy_path or not hmac_key:
        return empty
    if not isinstance(hmac_key, str) or len(hmac_key) < 32:
        return {**empty, "status": "invalid_configuration"}
    try:
        raw = Path(policy_path).read_bytes()
        if len(raw) > 256 * 1024:
            raise ValueError("policy_exceeds_256_kib")
        policy = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {**empty, "status": "unavailable_or_invalid", "reason": str(exc)}
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        return {**empty, "status": "rejected", "reason": "unsupported_policy_schema"}
    if not _verify_signature(policy, hmac_key):
        return {**empty, "status": "rejected", "reason": "policy_signature_invalid"}
    try:
        generated = _utc(policy.get("generated_at"), "generated_at")
        cutoff = _utc(decision_time, "decision_time")
    except ValueError as exc:
        return {**empty, "status": "rejected", "reason": str(exc)}
    if generated > cutoff:
        return {**empty, "status": "rejected", "reason": "policy_generated_after_decision_time"}
    attestation = policy.get("reviewer_attestation")
    if not isinstance(attestation, dict) or not _verify_signature(attestation, hmac_key):
        return {**empty, "status": "rejected", "reason": "policy_reviewer_signature_invalid"}
    try:
        reviewed = _utc(attestation.get("reviewed_at"), "reviewed_at")
    except ValueError as exc:
        return {**empty, "status": "rejected", "reason": str(exc)}
    if (attestation.get("decision") != "approved"
            or attestation.get("scope") != "evidence_freshness_policy"
            or not str(attestation.get("reviewer_id") or "").strip()
            or reviewed > cutoff):
        return {**empty, "status": "rejected", "reason": "policy_reviewer_attestation_invalid"}
    limits = policy.get("max_age_seconds")
    if not isinstance(limits, dict) or not limits:
        return {**empty, "status": "rejected", "reason": "max_age_seconds_required"}
    normalized = {}
    for source_class, age in limits.items():
        if (not isinstance(source_class, str) or not source_class.strip()
                or isinstance(age, bool) or not isinstance(age, int) or age <= 0):
            return {**empty, "status": "rejected", "reason": "freshness_limit_invalid"}
        normalized[source_class] = age
    return {
        "status": "reviewed_policy_loaded", "max_age_seconds": normalized,
        "policy_sha256": sha256(raw).hexdigest(),
        "generated_at": generated.isoformat(),
        "reviewer_id": attestation["reviewer_id"],
        "freshness_assessment_allowed": True,
    }


def assess_publisher_evidence(
    observations: list[dict[str, Any]],
    *,
    registry: dict[str, Any],
    freshness_policy: dict[str, Any],
    decision_time: str,
) -> dict[str, Any]:
    """Annotate each observation; count unique reviewed ownership groups only."""
    cutoff = _utc(decision_time, "decision_time")
    publishers = registry.get("publishers") if registry.get("status") == "reviewed_registry_loaded" else None
    limits = freshness_policy.get("max_age_seconds") if freshness_policy.get("status") == "reviewed_policy_loaded" else None
    output = []
    for index, row in enumerate(observations):
        if not isinstance(row, dict):
            output.append({"index": index, "status": "invalid_observation"})
            continue
        publisher_id = row.get("publisher_id")
        entry = publishers.get(publisher_id) if isinstance(publishers, dict) else None
        host = urlparse(str(row.get("source_url") or "")).hostname
        host = host.lower() if host else None
        host_ok = bool(entry and host and host in entry["approved_hosts"])
        captured_value = row.get("captured_at")
        try:
            captured = _utc(captured_value, f"observation_{index}_captured_at")
            age = max(0, int((cutoff - captured).total_seconds()))
            time_valid = captured <= cutoff
        except ValueError:
            age, time_valid = None, False
        source_class = row.get("source_class")
        age_limit = limits.get(source_class) if isinstance(limits, dict) else None
        freshness = "unconfigured" if age_limit is None else (
            "fresh" if time_valid and age is not None and age <= age_limit else "stale_or_future"
        )
        group = entry["ownership_group_id"] if host_ok and time_valid else None
        status = "eligible_for_group_count" if group and freshness == "fresh" else (
            "freshness_unconfigured" if group and freshness == "unconfigured" else
            "publisher_or_host_unverified" if not host_ok else "stale_or_future"
        )
        output.append({
            "index": index, "publisher_id": publisher_id,
            "ownership_group_id": group, "approved_host_match": host_ok,
            "age_seconds": age, "freshness_status": freshness,
            "independence_status": status,
            "eligible_for_independence_count": status == "eligible_for_group_count",
        })
    groups = sorted({row["ownership_group_id"] for row in output if row.get("eligible_for_independence_count")})
    return {
        "status": "assessed" if publishers is not None and limits is not None else "insufficient_configuration",
        "observations": output,
        "eligible_independent_ownership_group_count": len(groups),
        "ownership_group_ids": groups,
        "independence_assessment_allowed": publishers is not None and limits is not None,
        "freshness_assessment_allowed": limits is not None,
        "production_admission_allowed": False,
        "limitations": [
            "A shared ownership group counts once even when it operates multiple publisher brands.",
            "Unconfigured freshness limits remain unknown and are not treated as fresh.",
            "This assessment is research metadata, not a production trade signal.",
        ],
    }
