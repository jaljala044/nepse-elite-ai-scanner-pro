"""Canonical read gate joining immutable bronze evidence to signed promotion decisions.

Bronze rows remain provisional and immutable. This module creates a verified
read view only when a matching, signed, point-in-time promotion exists and the
raw payload bytes still match their stored SHA-256 digest.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .evidence_store import load_evidence_record_details
from .source_trust_registry import (
    active_promoted_record_ids,
    verify_promotion_ledger,
)


def load_canonical_evidence_records(
    *,
    database_path: str | Path | None,
    ledger_path: str | Path,
    registry: dict[str, Any],
    trusted_registry_sha256: str,
    reviewer_keys: dict[str, bytes],
    record_type: str | None = None,
) -> dict[str, Any]:
    """Return only currently promoted rows whose raw object and signed decision verify.

    This is a read-only view. It does not mutate bronze rows or write canonical
    tables. A corrupt ledger, missing raw object, digest mismatch, or promoted
    decision without a matching bronze row fails the entire read closed.
    """
    audit = verify_promotion_ledger(ledger_path)
    if not audit["valid"]:
        raise ValueError("promotion ledger integrity check failed")

    active_ids = active_promoted_record_ids(
        ledger_path,
        registry=registry,
        trusted_registry_sha256=trusted_registry_sha256,
        reviewer_keys=reviewer_keys,
    )
    latest_promotions: dict[str, dict[str, Any]] = {}
    for event in audit["events"]:
        record_id = event.get("record_id")
        if (
            record_id in active_ids
            and event.get("action") == "promote"
            and event.get("accepted") is True
        ):
            latest_promotions[record_id] = event

    if record_type:
        latest_type_by_id: dict[str, str] = {}
        for event in audit["events"]:
            if event.get("record_id") in active_ids and event.get("action") in {"promote", "revoke"} and event.get("accepted") is True:
                latest_type_by_id[event["record_id"]] = event.get("record_type", "")
        active_ids = {record_id for record_id in active_ids if latest_type_by_id.get(record_id) == record_type}

    bronze_rows = load_evidence_record_details(
        database_path=database_path, record_type=record_type
    )
    bronze_by_id = {row["record_id"]: row for row in bronze_rows}
    missing = sorted(active_ids - set(bronze_by_id))
    if missing:
        raise ValueError("promotion ledger references records absent from bronze evidence store")

    canonical = []
    for record_id in sorted(active_ids):
        row = bronze_by_id[record_id]
        event = latest_promotions.get(record_id)
        if event is None:
            raise ValueError("active promotion has no accepted promotion event")
        for field in (
            "source_id", "record_type", "source_payload_sha256",
            "session_date", "available_at",
        ):
            if row.get(field) != event.get(field):
                raise ValueError(f"bronze row and promotion decision mismatch: {field}")

        raw_path = Path(row["raw_payload_path"])
        try:
            raw_payload = raw_path.read_bytes()
        except OSError as exc:
            raise ValueError("promoted record raw payload object is unavailable") from exc
        actual_digest = hashlib.sha256(raw_payload).hexdigest()
        if actual_digest != row.get("source_payload_sha256"):
            raise ValueError("promoted record raw payload digest mismatch")

        attestation = event["validation_attestation"]
        checks = attestation.get("checks", {})
        row["bronze_source_validation_status"] = row.get("source_validation_status")
        row["bronze_finality_status"] = row.get("finality_status")
        row["source_validation_status"] = "verified"
        row["finality_status"] = "final" if checks.get("exchange_finality") == "passed" else "not_applicable"
        row["canonical_status"] = "promoted"
        row["canonical_eligible"] = True
        row["promotion_decision_id"] = event["decision_id"]
        row["promotion_decided_at"] = event["decision_time"]
        row["promotion_reviewer"] = event["reviewer"]
        row["promotion_validation_id"] = event["validation_id"]
        row.pop("raw_payload_path", None)
        canonical.append(row)

    return {
        "status": "ready" if canonical else "no_canonical_records",
        "canonical_eligible": bool(canonical),
        "registry_sha256": registry.get("registry_sha256"),
        "promotion_ledger_valid": True,
        "promoted_record_count": len(canonical),
        "withheld_record_count": max(0, len(bronze_rows) - len(canonical)),
        "records": canonical,
        "production_source_claim": False,
    }
