"""Reviewed source trust registry and append-only evidence promotion ledger.

Source identity/trust and legal redistribution rights are distinct controls.
A publisher's own status fields never constitute independent validation.
No source is approved by default: callers must supply a reviewed registry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Iterable


RECORD_TYPES = {
    "ohlcv", "index_ohlcv", "market_summary", "floorsheet",
    "sector_membership", "sector_price", "corporate_action",
    "broker_observation",
}

REQUIRED_CHECKS = {
    "ohlcv": {
        "payload_integrity", "source_identity", "schema_mapping",
        "instrument_identity", "session_calendar", "point_in_time",
        "corporate_action_basis", "price_integrity",
    },
    "index_ohlcv": {
        "payload_integrity", "source_identity", "schema_mapping",
        "session_calendar", "point_in_time", "price_integrity",
    },
    "market_summary": {
        "payload_integrity", "source_identity", "schema_mapping",
        "session_calendar", "point_in_time", "market_reconciliation",
    },
    "floorsheet": {
        "payload_integrity", "source_identity", "schema_mapping",
        "session_calendar", "point_in_time", "trade_identity",
        "coverage_completeness",
    },
    "sector_membership": {
        "payload_integrity", "source_identity", "schema_mapping",
        "issuer_identity", "effective_dating",
    },
    "sector_price": {
        "payload_integrity", "source_identity", "schema_mapping",
        "session_calendar", "point_in_time", "constituent_mapping",
    },
    "corporate_action": {
        "payload_integrity", "source_identity", "schema_mapping",
        "issuer_identity", "effective_dating", "official_notice",
    },
    "broker_observation": {
        "payload_integrity", "source_identity", "schema_mapping",
        "broker_identity", "point_in_time",
    },
}

POLICY_STATES = {"review_required", "active", "suspended", "revoked"}
CANONICAL_TRUST_TIERS = {"exchange_primary", "official_registry"}
RIGHTS_STATES = {"unknown", "review_required", "research_only", "internal_use", "redistribution_permitted", "prohibited"}
TRUST_TIERS = {
    "exchange_primary", "official_registry", "licensed_publisher",
    "secondary_publisher", "user_supplied", "derived", "unknown",
}


def _utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _sha256(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        c not in "0123456789abcdef" for c in value.lower()
    ):
        raise ValueError(f"{field} must be a SHA-256 hex digest")
    return value.lower()


@dataclass(frozen=True)
class SourcePolicy:
    source_id: str
    publisher_name: str
    trust_tier: str
    allowed_record_types: tuple[str, ...]
    canonical_record_types: tuple[str, ...]
    status: str
    effective_from: str
    effective_to: str | None
    reviewer: str
    reviewed_at: str
    evidence_refs: tuple[str, ...]
    rights_state: str = "unknown"
    redistribution_allowed: bool = False
    rights_evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.publisher_name.strip():
            raise ValueError("source_id and publisher_name are required")
        if self.trust_tier not in TRUST_TIERS:
            raise ValueError("unsupported trust_tier")
        if self.status not in POLICY_STATES:
            raise ValueError("unsupported source policy status")
        if self.rights_state not in RIGHTS_STATES:
            raise ValueError("unsupported rights_state")
        if not self.reviewer.strip() or not self.evidence_refs or any(
            not ref.strip() for ref in self.evidence_refs
        ):
            raise ValueError("reviewer and non-empty evidence_refs are required")
        allowed = set(self.allowed_record_types)
        canonical = set(self.canonical_record_types)
        if not allowed or not allowed <= RECORD_TYPES or not canonical <= allowed:
            raise ValueError("record types must be supported and canonical types must be allowed")
        if canonical and self.trust_tier not in CANONICAL_TRUST_TIERS:
            raise ValueError("only exchange_primary or official_registry sources may supply canonical records")
        start = date.fromisoformat(self.effective_from)
        if self.effective_to:
            end = date.fromisoformat(self.effective_to)
            if end < start:
                raise ValueError("effective_to cannot precede effective_from")
        _utc(self.reviewed_at, "reviewed_at")
        if self.redistribution_allowed and self.rights_state != "redistribution_permitted":
            raise ValueError("redistribution requires explicit redistribution_permitted rights")
        if self.redistribution_allowed and not (self.rights_evidence_ref or "").strip():
            raise ValueError("redistribution requires a dedicated rights_evidence_ref")
        if self.rights_state == "redistribution_permitted" and not (self.rights_evidence_ref or "").strip():
            raise ValueError("permitted rights state requires a dedicated rights_evidence_ref")


def build_source_registry(policies: Iterable[SourcePolicy]) -> dict[str, Any]:
    items = sorted(list(policies), key=lambda item: item.source_id)
    ids = [item.source_id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source_id in registry")
    body = {"schema_version": 1, "sources": [asdict(item) for item in items]}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "registry_sha256": hashlib.sha256(canonical.encode()).hexdigest()}



def verify_source_registry(registry: dict[str, Any], expected_sha256: str) -> bool:
    expected = _sha256(expected_sha256, "expected_registry_sha256")
    body = {"schema_version": registry.get("schema_version"), "sources": registry.get("sources")}
    actual = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return registry.get("registry_sha256") == actual == expected


def _validation_signature_payload(validation: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in validation.items() if key != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_reviewer_signature(validation: dict[str, Any], reviewer_keys: dict[str, bytes]) -> bool:
    reviewer = validation.get("reviewer")
    signature = validation.get("signature")
    key = reviewer_keys.get(reviewer) if isinstance(reviewer, str) else None
    if not isinstance(key, bytes) or not key or not isinstance(signature, str):
        return False
    expected = hmac.new(key, _validation_signature_payload(validation), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def resolve_source_policy(
    registry: dict[str, Any], *, source_id: str, record_type: str,
    session_date: str, decision_time: str,
) -> tuple[SourcePolicy | None, list[str]]:
    reasons: list[str] = []
    if record_type not in RECORD_TYPES:
        return None, ["unsupported_record_type"]
    try:
        parsed_session = date.fromisoformat(session_date)
        cutoff = _utc(decision_time, "decision_time")
        policies = registry.get("sources", [])
        matches = [item for item in policies if item.get("source_id") == source_id]
        if len(matches) != 1:
            return None, ["source_not_registered_or_ambiguous"]
        policy = SourcePolicy(**{
            **matches[0],
            "allowed_record_types": tuple(matches[0]["allowed_record_types"]),
            "canonical_record_types": tuple(matches[0]["canonical_record_types"]),
            "evidence_refs": tuple(matches[0]["evidence_refs"]),
        })
        if policy.status != "active":
            reasons.append("source_policy_not_active")
        if record_type not in policy.allowed_record_types:
            reasons.append("record_type_not_allowed_for_source")
        if record_type not in policy.canonical_record_types:
            reasons.append("source_not_approved_for_canonical_record_type")
        if parsed_session < date.fromisoformat(policy.effective_from):
            reasons.append("source_policy_not_yet_effective_for_session")
        if policy.effective_to and parsed_session > date.fromisoformat(policy.effective_to):
            reasons.append("source_policy_expired_for_session")
        if _utc(policy.reviewed_at, "reviewed_at") > cutoff:
            reasons.append("source_policy_review_occurs_after_decision_time")
        return policy, reasons
    except (KeyError, TypeError, ValueError):
        return None, ["invalid_source_registry_or_decision_metadata"]


def validate_promotion_evidence(
    record: dict[str, Any], *, raw_payload_sha256: str,
    validation: dict[str, Any], decision_time: str,
) -> list[str]:
    reasons: list[str] = []
    record_type = record.get("record_type")
    if record_type not in REQUIRED_CHECKS:
        return ["unsupported_record_type"]
    try:
        digest = _sha256(record.get("source_payload_sha256"), "source_payload_sha256")
        raw_digest = _sha256(raw_payload_sha256, "raw_payload_sha256")
        if digest != raw_digest:
            reasons.append("record_payload_digest_mismatch")
        validation_digest = _sha256(validation.get("payload_sha256"), "validation.payload_sha256")
        if validation_digest != raw_digest:
            reasons.append("validation_payload_digest_mismatch")
        available = _utc(record.get("available_at"), "available_at")
        cutoff = _utc(decision_time, "decision_time")
        validated = _utc(validation.get("validated_at"), "validated_at")
        if available > cutoff:
            reasons.append("record_not_available_at_decision_time")
        if validated > cutoff:
            reasons.append("validation_occurs_after_decision_time")
        if not validation.get("reviewer") or not validation.get("validation_id"):
            reasons.append("validation_reviewer_or_id_missing")
        checks = validation.get("checks", {})
        evidence_refs = validation.get("evidence_refs", {})
        for check in sorted(REQUIRED_CHECKS[record_type]):
            if checks.get(check) != "passed":
                reasons.append(f"required_check_not_passed:{check}")
            refs = evidence_refs.get(check, [])
            if not isinstance(refs, list) or not refs or any(not str(ref).strip() for ref in refs):
                reasons.append(f"independent_evidence_reference_missing:{check}")
    except (TypeError, ValueError):
        reasons.append("invalid_promotion_evidence_metadata")
    return sorted(set(reasons))


def build_promotion_event(
    *, decision_id: str, action: str, record: dict[str, Any],
    registry: dict[str, Any], raw_payload_sha256: str,
    validation: dict[str, Any], decision_time: str,
    trusted_registry_sha256: str, reviewer_keys: dict[str, bytes],
) -> dict[str, Any]:
    if action not in {"promote", "reject", "revoke"}:
        raise ValueError("action must be promote, reject or revoke")
    if not decision_id.strip():
        raise ValueError("decision_id is required")
    reasons = []
    if not verify_source_registry(registry, trusted_registry_sha256):
        reasons.append("source_registry_digest_not_trusted")
    if not verify_reviewer_signature(validation, reviewer_keys):
        reasons.append("reviewer_signature_invalid_or_untrusted")
    if action == "promote":
        _, policy_reasons = resolve_source_policy(
            registry, source_id=record.get("source_id", ""),
            record_type=record.get("record_type", ""),
            session_date=record.get("session_date", ""),
            decision_time=decision_time,
        )
        reasons.extend(policy_reasons)
        reasons.extend(validate_promotion_evidence(
            record, raw_payload_sha256=raw_payload_sha256,
            validation=validation, decision_time=decision_time,
        ))
    elif action == "revoke":
        if not record.get("record_id"):
            reasons.append("record_id_required_for_revocation")
        if not validation.get("reviewer") or not validation.get("validation_id") or not validation.get("evidence_refs"):
            reasons.append("revocation_reviewer_and_evidence_required")
        try:
            if _utc(validation.get("validated_at"), "validated_at") > _utc(decision_time, "decision_time"):
                reasons.append("revocation_validation_occurs_after_decision_time")
        except (TypeError, ValueError):
            reasons.append("invalid_revocation_validation_timestamp")
    body = {
        "schema_version": 1, "decision_id": decision_id, "action": action,
        "record_id": record.get("record_id"), "source_id": record.get("source_id"),
        "record_type": record.get("record_type"),
        "source_payload_sha256": record.get("source_payload_sha256"),
        "decision_time": _utc(decision_time, "decision_time").isoformat().replace("+00:00", "Z"),
        "validation_id": validation.get("validation_id"),
        "reviewer": validation.get("reviewer"),
        "evidence_refs": validation.get("evidence_refs", {}),
        "accepted": action in {"promote", "revoke"} and not reasons,
        "reasons": sorted(set(reasons)),
        "registry_sha256": registry.get("registry_sha256"),
        "validation_signature": validation.get("signature"),
    }
    return body


def _event_hash(event: dict[str, Any]) -> str:
    body = {key: value for key, value in event.items() if key not in {"previous_event_sha256", "event_sha256"}}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def append_promotion_event(path: str | Path, event: dict[str, Any]) -> dict[str, Any]:
    """Append an immutable hash-chained event; never rewrite earlier decisions."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = verify_promotion_ledger(target)
    if not existing["valid"]:
        raise ValueError("cannot append to an invalid promotion ledger")
    for prior in existing["events"]:
        if prior["decision_id"] == event.get("decision_id"):
            comparable = {k: v for k, v in prior.items() if k not in {"previous_event_sha256", "event_sha256"}}
            if comparable == event:
                return {"idempotent": True, "event": prior}
            raise ValueError("decision_id already exists with conflicting event")
    stored = dict(event)
    stored["previous_event_sha256"] = existing["last_event_sha256"]
    stored["event_sha256"] = _event_hash(stored)
    line = (json.dumps(stored, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(fd, "ab", closefd=False) as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    return {"idempotent": False, "event": stored}


def verify_promotion_ledger(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {"valid": True, "events": [], "last_event_sha256": None, "errors": []}
    events = []
    errors = []
    previous = None
    for number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            event = json.loads(line)
            if event.get("previous_event_sha256") != previous:
                errors.append(f"line_{number}:previous_hash_mismatch")
            if event.get("event_sha256") != _event_hash(event):
                errors.append(f"line_{number}:event_hash_mismatch")
            if any(item.get("decision_id") == event.get("decision_id") for item in events):
                errors.append(f"line_{number}:duplicate_decision_id")
            previous = event.get("event_sha256")
            events.append(event)
        except (json.JSONDecodeError, TypeError, AttributeError):
            errors.append(f"line_{number}:invalid_json_event")
            break
    return {"valid": not errors, "events": events,
            "last_event_sha256": previous, "errors": errors}


def active_promoted_record_ids(path: str | Path) -> set[str]:
    audit = verify_promotion_ledger(path)
    if not audit["valid"]:
        raise ValueError("promotion ledger integrity check failed")
    state: dict[str, bool] = {}
    for event in audit["events"]:
        record_id = event.get("record_id")
        if event.get("action") == "promote" and event.get("accepted") is True:
            state[record_id] = True
        elif event.get("action") == "revoke" and event.get("accepted") is True:
            state[record_id] = False
    return {record_id for record_id, active in state.items() if active and record_id}
