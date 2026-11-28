"""Persistent, point-in-time source data-quality evidence replay.

The store is an append-only diagnostic layer. It never promotes canonical
OHLCV/floorsheets and never authorizes recommendations or production admission.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence_store import load_evidence_records, persist_evidence_batch
from .source_data_quality_gate import (
    assess_source_capture_completeness,
    build_data_quality_report,
    reconcile_source_observations,
    resolve_record_corrections,
    validate_calendar_sessions,
    validate_capture_policy,
)

EVIDENCE_KINDS = {
    "calendar_session", "capture_policy", "source_capture",
    "market_observation", "record_correction", "source_lifecycle_event",
}


def _instant(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_timezone_aware_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_invalid_iso_timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_timezone_aware_required")
    return parsed.astimezone(timezone.utc)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _bundle_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(bundle, dict):
        raise ValueError("data_quality_bundle_must_be_object")
    mapping = {
        "calendar_sessions": "calendar_session",
        "capture_policies": "capture_policy",
        "captures": "source_capture",
        "observations": "market_observation",
        "correction_records": "record_correction",
        "reliability_events": "source_lifecycle_event",
    }
    rows = []
    for field, kind in mapping.items():
        values = bundle.get(field, [])
        if not isinstance(values, list):
            raise ValueError(f"{field}_must_be_list")
        for item in values:
            if not isinstance(item, dict):
                raise ValueError(f"{field}_items_must_be_objects")
            body = dict(item)
            identity = body.get("evidence_id")
            if identity is None:
                identity = hashlib.sha256(kind.encode() + b":" + _canonical(body)).hexdigest()
            if not isinstance(identity, str) or not identity.strip():
                raise ValueError("evidence_id_must_be_non_empty_string")
            rows.append({"evidence_id": identity, "evidence_kind": kind, "evidence": body})
    ids = [row["evidence_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_evidence_id_in_bundle")
    return rows


def persist_source_data_quality_batch(
    bundle: dict[str, Any], *, batch_id: str, captured_at: str,
    received_at: str, storage_root: str | Path,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    """Persist raw bundle bytes and typed provisional rows with exact retry semantics."""
    captured = _instant(captured_at, "captured_at")
    received = _instant(received_at, "received_at")
    if captured > received:
        raise ValueError("captured_at_cannot_follow_received_at")
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id_required")
    rows = _bundle_rows(bundle)
    if not rows:
        raise ValueError("data_quality_bundle_has_no_evidence")
    existing = load_evidence_records(
        database_path=database_path, record_type="source_data_quality_evidence"
    )
    prior = {
        row.get("evidence_id"): row.get("evidence_batch_id")
        for row in existing if row.get("evidence_id")
    }
    for row in rows:
        previous_batch = prior.get(row["evidence_id"])
        if previous_batch is not None and previous_batch != batch_id:
            raise ValueError("evidence_id_already_persisted:" + row["evidence_id"])
    payload = _canonical({"batch_id": batch_id, "bundle": bundle})
    digest = hashlib.sha256(payload).hexdigest()
    manifest = {
        "fetch_id": batch_id,
        "source_id": "source-data-quality-envelope",
        "source_url": f"urn:nepse-source-data-quality:{batch_id}",
        "payload_sha256": digest,
        "payload_bytes": len(payload),
        "requested_at_utc": captured.isoformat().replace("+00:00", "Z"),
        "received_at_utc": received.isoformat().replace("+00:00", "Z"),
        "parser_version": "source-data-quality-store-v1",
        "rights_status": "unknown",
    }
    normalized = [{
        "source_row_number": index,
        "record_type": "source_data_quality_evidence",
        "session_date": (
            item["evidence"].get("date")
            or item["evidence"].get("session_date")
            or item["evidence"].get("effective_date")
        ),
        "evidence_batch_id": batch_id,
        "evidence_id": item["evidence_id"],
        "evidence_kind": item["evidence_kind"],
        "evidence": item["evidence"],
    } for index, item in enumerate(rows, start=1)]
    stored = persist_evidence_batch(
        payload, manifest, normalized, storage_root=storage_root,
        database_path=database_path,
    )
    return {
        **stored,
        "evidence_count": len(rows),
        "evidence_kind_counts": {
            kind: sum(row["evidence_kind"] == kind for row in rows)
            for kind in sorted(EVIDENCE_KINDS)
        },
        "manifest_sha256": digest,
        "source_validation_status": "review_required",
        "finality_status": "provisional",
        "production_admission_allowed": False,
    }


def load_source_data_quality_evidence(
    *, database_path: str | Path | None = None,
) -> dict[str, Any]:
    rows = load_evidence_records(
        database_path=database_path, record_type="source_data_quality_evidence"
    )
    return {
        "rows": rows,
        "evidence_count": len(rows),
        "batch_ids": sorted({row.get("evidence_batch_id") for row in rows if row.get("evidence_batch_id")}),
        "source_validation_status": "review_required",
        "finality_status": "provisional",
        "production_admission_allowed": False,
    }


def replay_source_data_quality(
    rows: list[dict[str, Any]], *, decision_time: str,
) -> dict[str, Any]:
    """Replay only evidence available by cutoff; missing inputs remain unknown."""
    cutoff = _instant(decision_time, "decision_time")
    selected = []
    excluded = 0
    for row in rows:
        try:
            available = _instant(row.get("available_at"), "available_at")
        except ValueError:
            excluded += 1
            continue
        if available > cutoff:
            excluded += 1
            continue
        kind, body = row.get("evidence_kind"), row.get("evidence")
        if kind not in EVIDENCE_KINDS or not isinstance(body, dict):
            excluded += 1
            continue
        selected.append((kind, body))
    grouped = {kind: [body for row_kind, body in selected if row_kind == kind] for kind in EVIDENCE_KINDS}
    calendar = validate_calendar_sessions(grouped["calendar_session"], decision_time=decision_time)
    policies, invalid_policy_count = [], 0
    for item in grouped["capture_policy"]:
        try:
            policies.append(validate_capture_policy(item))
        except (TypeError, ValueError):
            invalid_policy_count += 1
    completeness = assess_source_capture_completeness(
        policies, grouped["source_capture"], calendar,
        decision_time=decision_time,
        reliability_events=grouped["source_lifecycle_event"],
    )
    try:
        reconciliation = reconcile_source_observations(grouped["market_observation"])
        invalid_observation_count = 0
    except (TypeError, ValueError):
        reconciliation = {"results": [], "conflict_count": 0, "promotion_allowed": False}
        invalid_observation_count = len(grouped["market_observation"])
    corrections = None
    correction_history_invalid = False
    if grouped["record_correction"]:
        try:
            corrections = resolve_record_corrections(
                grouped["record_correction"], decision_time=decision_time
            )
        except (TypeError, ValueError):
            correction_history_invalid = True
    report = build_data_quality_report(
        calendar=calendar, completeness=completeness,
        reconciliation=reconciliation, record_corrections=corrections,
    )
    if invalid_policy_count or invalid_observation_count or correction_history_invalid:
        report["reasons"].append("persisted_evidence_validation_failed")
        report["data_quality"] = "LOW"
        report["confidence"] = "LOW"
    # Two distinct source IDs are required before a row is described as
    # cross-source corroborated. This does not prove publisher independence;
    # ownership-group review remains a separate trust gate.
    single_source_groups = sum(
        item.get("status") == "single_source_only"
        for item in reconciliation.get("results", [])
    )
    if single_source_groups:
        report["reasons"].append("cross_source_corroboration_incomplete")
        report["data_quality"] = "LOW"
        report["confidence"] = "LOW"
    return {
        "status": "assessed" if selected else "insufficient_evidence",
        "decision_time": cutoff.isoformat(),
        "selected_evidence_count": len(selected),
        "excluded_future_or_invalid_count": excluded,
        "evidence_kind_counts": {kind: len(values) for kind, values in grouped.items()},
        "calendar": {
            "status": calendar["status"],
            "accepted_session_count": calendar["accepted_session_count"],
            "rejected_count": len(calendar["rejected"]),
        },
        "capture_completeness": completeness,
        "cross_source_reconciliation": reconciliation,
        "correction_history": corrections,
        "invalid_capture_policy_count": invalid_policy_count,
        "invalid_observation_count": invalid_observation_count,
        "correction_history_invalid": correction_history_invalid,
        "data_quality_report": report,
        "source_validation_status": "review_required",
        "finality_status": "provisional",
        "canonical_promotion_allowed": False,
        "ohlcv_admission_allowed": False,
        "floorsheet_admission_allowed": False,
        "production_admission_allowed": False,
        "recommendation_override": False,
    }


def source_data_quality_readiness(
    *, database_path: str | Path | None, decision_time: str,
) -> dict[str, Any]:
    """Read-only readiness. An absent DB is not created as a side effect."""
    path = Path(database_path).expanduser() if database_path else None
    if path is None or not path.is_file():
        return {
            "status": "not_configured",
            "store_configured": bool(path),
            "persisted_evidence_count": 0,
            "data_quality": "LOW",
            "confidence": "LOW",
            "missing_reason": "persistent_calendar_capture_policy_store_not_configured",
            "production_admission_allowed": False,
            "recommendation_override": False,
        }
    loaded = load_source_data_quality_evidence(database_path=path)
    replay = replay_source_data_quality(loaded["rows"], decision_time=decision_time)
    return {
        "status": replay["status"],
        "store_configured": True,
        "persisted_evidence_count": loaded["evidence_count"],
        "batch_count": len(loaded["batch_ids"]),
        "data_quality": replay["data_quality_report"]["data_quality"],
        "confidence": replay["data_quality_report"]["confidence"],
        "replay": replay,
        "production_admission_allowed": False,
        "recommendation_override": False,
    }
