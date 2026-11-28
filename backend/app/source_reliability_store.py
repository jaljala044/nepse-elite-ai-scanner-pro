"""Append-only persistence for source lifecycle reliability events."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence_store import load_evidence_records, persist_evidence_batch
from .source_reliability_timeline import build_source_event_manifest, replay_source_reliability


def persist_source_reliability_batch(
    events: list[dict[str, Any]], *, batch_id: str, captured_at: str,
    received_at: str, storage_root: str | Path,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    """Persist validated source lifecycle events in the shared bronze store."""
    batch = build_source_event_manifest(
        events, batch_id=batch_id, captured_at=captured_at, received_at=received_at
    )
    existing = load_source_reliability_events(database_path=database_path)
    existing_ids = {
        row.get("event_id"): row.get("event_batch_id")
        for row in existing["events"] if row.get("event_id")
    }
    for event in batch["events"]:
        prior_batch = existing_ids.get(event["event_id"])
        if prior_batch and prior_batch != batch_id:
            raise ValueError("event_id_already_persisted:" + event["event_id"])
    payload = json.dumps(
        {"batch_id": batch_id, "events": batch["events"]},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    manifest = {
        "fetch_id": batch_id, "source_id": "source-reliability-event-envelope",
        "source_url": f"urn:nepse-source-reliability:{batch_id}",
        "payload_sha256": batch["payload_sha256"], "payload_bytes": batch["payload_bytes"],
        "requested_at_utc": captured_at, "received_at_utc": received_at,
        "parser_version": "source-reliability-store-v1", "rights_status": "unknown",
    }
    records = [{
        "source_row_number": index, "record_type": "source_reliability_event",
        "session_date": event["effective_date"], "event_batch_id": batch_id,
        "source_event": event,
    } for index, event in enumerate(batch["events"], start=1)]
    stored = persist_evidence_batch(
        payload, manifest, records, storage_root=storage_root,
        database_path=database_path,
    )
    return {
        **stored, "event_count": len(records), "event_manifest_sha256": batch["payload_sha256"],
        "source_validation_status": "review_required", "finality_status": "provisional",
        "production_admission_allowed": False,
    }


def load_source_reliability_events(
    *, database_path: str | Path | None = None,
) -> dict[str, Any]:
    rows = load_evidence_records(
        database_path=database_path, record_type="source_reliability_event"
    )
    events = [row["source_event"] for row in rows if isinstance(row.get("source_event"), dict)]
    return {
        "events": events, "event_count": len(events),
        "batch_ids": sorted({row.get("event_batch_id") for row in rows}),
        "source_validation_status": "review_required",
        "finality_status": "provisional", "production_admission_allowed": False,
    }


def source_reliability_readiness(
    *, database_path: str | Path | None,
    decision_time: str, expected_source_ids: list[str] | None = None,
    verified_session_dates: list[str] | None = None,
) -> dict[str, Any]:
    """Read-only readiness summary; absent DB/calendar is explicitly unknown."""
    path = Path(database_path).expanduser() if database_path else None
    if path is None or not path.is_file():
        return {
            "status": "not_configured", "store_configured": bool(path),
            "persisted_event_count": 0, "source_count": 0,
            "session_calendar_status": "not_configured",
            "production_admission_allowed": False,
            "recommendation_override": False,
        }
    loaded = load_source_reliability_events(database_path=path)
    replay = replay_source_reliability(
        loaded["events"], decision_time=decision_time,
        expected_source_ids=expected_source_ids,
        verified_session_dates=verified_session_dates,
    )
    return {
        "status": "assessed" if loaded["event_count"] else "empty_store",
        "store_configured": True, "persisted_event_count": loaded["event_count"],
        "batch_count": len(loaded["batch_ids"]), "source_count": replay["source_count"],
        "missing_expected_sources": replay["missing_expected_sources"],
        "excluded_future_or_invalid_event_count": replay["excluded_future_or_invalid_event_count"],
        "verified_session_count": replay["verified_session_count"],
        "session_calendar_status": replay["status"] if verified_session_dates else "not_configured",
        "sources": replay["sources"],
        "source_validation_status": loaded["source_validation_status"],
        "finality_status": loaded["finality_status"],
        "production_admission_allowed": False, "recommendation_override": False,
    }
