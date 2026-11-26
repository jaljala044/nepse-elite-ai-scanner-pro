"""Fail-closed canonical projection of promoted bronze evidence."""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .evidence_store import load_evidence_record_details
from .source_trust_registry import resolve_source_policy, validate_promotion_evidence, verify_promotion_ledger, verify_reviewer_signature, verify_source_registry

def load_canonical_evidence_records(*, database_path: str | Path | None, ledger_path: str | Path, registry: dict[str, Any], trusted_registry_sha256: str, reviewer_keys: dict[str, bytes], decision_time: str, record_type: str | None = None) -> dict[str, Any]:
    """Read only currently promoted rows after rechecking every trust boundary."""
    if not verify_source_registry(registry, trusted_registry_sha256):
        raise ValueError("source registry digest or schema is invalid")
    audit = verify_promotion_ledger(ledger_path)
    if not audit["valid"]:
        raise ValueError("promotion ledger integrity check failed")
    rows = load_evidence_record_details(database_path=database_path, record_type=record_type)
    by_id = {row["record_id"]: row for row in rows}
    state: dict[str, dict[str, Any]] = {}
    for event in audit["events"]:
        action, record_id = event.get("action"), event.get("record_id")
        if not record_id or action not in {"promote", "revoke"} or event.get("accepted") is not True:
            continue
        attestation = event.get("validation_attestation")
        if not isinstance(attestation, dict) or not verify_reviewer_signature(attestation, reviewer_keys):
            raise ValueError("accepted ledger event has no valid reviewer attestation")
        if event.get("registry_sha256") != registry.get("registry_sha256"):
            raise ValueError("ledger event is bound to a different source registry")
        if action == "revoke":
            if not event.get("reviewer") or not event.get("validation_id") or not event.get("evidence_refs"):
                raise ValueError("accepted revocation lacks reviewer or evidence")
        state[record_id] = {"action": action, "event": event}
    canonical = []
    for record_id, current in sorted(state.items()):
        if current["action"] != "promote":
            continue
        row = by_id.get(record_id)
        if row is None:
            raise ValueError("promotion ledger references a record absent from bronze evidence")
        event = current["event"]
        for field in ("source_id", "record_type", "source_payload_sha256", "session_date", "available_at"):
            if row.get(field) != event.get(field):
                raise ValueError(f"bronze row and promotion decision mismatch: {field}")
        event_cutoff = datetime.fromisoformat(event["decision_time"].replace("Z", "+00:00"))
        requested_cutoff = datetime.fromisoformat(decision_time.replace("Z", "+00:00"))
        if event_cutoff > requested_cutoff:
            continue
        attestation = event["validation_attestation"]
        _, policy_reasons = resolve_source_policy(registry, source_id=row.get("source_id", ""), record_type=row.get("record_type", ""), session_date=str(row.get("session_date") or ""), decision_time=event["decision_time"])
        if policy_reasons:
            raise ValueError("promoted record source policy is no longer verifiable")
        reasons = validate_promotion_evidence(row, raw_payload_sha256=row["source_payload_sha256"], validation=attestation, decision_time=decision_time)
        if reasons:
            raise ValueError("promoted record validation failed: " + ",".join(reasons))
        try:
            raw_digest = hashlib.sha256(Path(row["raw_payload_path"]).read_bytes()).hexdigest()
        except OSError as exc:
            raise ValueError("promoted record raw object is unavailable") from exc
        if raw_digest != row.get("source_payload_sha256"):
            raise ValueError("promoted record raw payload digest mismatch")
        checks = attestation.get("checks", {})
        if row.get("record_type") in {"ohlcv", "index_ohlcv", "market_summary", "floorsheet"} and checks.get("exchange_finality") != "passed":
            raise ValueError("exchange finality is not independently attested")
        item = dict(row)
        item["bronze_source_validation_status"] = item.get("source_validation_status")
        item["bronze_finality_status"] = item.get("finality_status")
        item["source_validation_status"] = "verified"
        item["finality_status"] = "final"
        item["canonical_status"] = "promoted"
        item["canonical_eligible"] = True
        item["promotion_decision_id"] = event["decision_id"]
        item["promotion_decided_at"] = event["decision_time"]
        item["promotion_reviewer"] = event["reviewer"]
        item.pop("raw_payload_path", None)
        canonical.append(item)
    return {"status": "ready" if canonical else "no_canonical_records", "canonical_eligible": bool(canonical), "registry_sha256": registry.get("registry_sha256"), "promotion_ledger_valid": True, "promoted_record_count": len(canonical), "withheld_record_count": max(0, len(rows)-len(canonical)), "records": canonical, "production_source_claim": False}
