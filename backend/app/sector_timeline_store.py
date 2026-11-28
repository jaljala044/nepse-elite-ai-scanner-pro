"""Append-only persistence adapter for point-in-time sector timeline events.

The existing evidence store remains the bronze layer. Timeline events are stored
as provisional evidence records; this module never promotes them or opens the
scanner's production admission gate.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence_store import load_evidence_records, persist_evidence_batch
from .sector_historical_timeline import build_sector_timeline_snapshot


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_required")
    return value.strip()


def _aware_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_timezone_aware_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_timezone_aware_required") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_timezone_aware_required")
    return parsed.astimezone(timezone.utc)


def persist_sector_timeline_batch(
    events: list[dict[str, Any]],
    *,
    batch_id: str,
    requested_at_utc: str,
    received_at_utc: str,
    storage_root: str | Path,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    """Persist an immutable event batch through the shared raw-evidence store.

    The batch envelope is an internal capture container, not the original
    publisher. Original event source/publisher IDs, timestamps, references and
    payload digests remain nested unchanged in each timeline_event.
    """
    batch_id = _required_text(batch_id, "batch_id")
    _required_text(requested_at_utc, "requested_at_utc")
    _required_text(received_at_utc, "received_at_utc")
    received = _aware_utc(received_at_utc, "received_at_utc")
    requested = _aware_utc(requested_at_utc, "requested_at_utc")
    if requested > received:
        raise ValueError("requested_at_after_received_at")
    if not isinstance(events, list) or not events:
        raise ValueError("events_must_be_non_empty_list")

    seen: set[str] = set()
    existing = load_evidence_records(
        database_path=database_path, record_type="sector_membership"
    )
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"event_{index}_must_be_object")
        event_id = _required_text(event.get("event_id"), f"event_{index}_event_id")
        if event_id in seen:
            raise ValueError(f"duplicate_event_id_in_batch:{event_id}")
        seen.add(event_id)
        if any(
            row.get("timeline_event", {}).get("event_id") == event_id
            and row.get("fetch_id") != batch_id
            for row in existing
        ):
            raise ValueError(f"event_id_already_persisted:{event_id}")
        _required_text(event.get("effective_from"), f"event_{index}_effective_from")
        captured = _aware_utc(event.get("captured_at"), f"event_{index}_captured_at")
        available = _aware_utc(event.get("available_at"), f"event_{index}_available_at")
        if available < captured:
            raise ValueError(f"event_{index}_available_before_capture")
        if available > received:
            raise ValueError(f"event_{index}_available_after_batch_receipt")

    payload = json.dumps(
        {"batch_id": batch_id, "events": events},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    manifest = {
        "fetch_id": batch_id,
        "source_id": "sector-timeline-batch-envelope",
        "source_url": f"urn:nepse-sector-timeline-batch:{batch_id}",
        "payload_sha256": digest,
        "payload_bytes": len(payload),
        "requested_at_utc": requested_at_utc,
        "received_at_utc": received_at_utc,
        "parser_version": "sector-timeline-store-v1",
        "rights_status": "unknown",
    }
    records = [
        {
            "source_row_number": index,
            "record_type": "sector_membership",
            "session_date": event["effective_from"],
            "timeline_batch_id": batch_id,
            "timeline_event": event,
        }
        for index, event in enumerate(events, start=1)
    ]
    stored = persist_evidence_batch(
        payload,
        manifest,
        records,
        storage_root=storage_root,
        database_path=database_path,
    )
    return {
        **stored,
        "event_count": len(events),
        "immutability": "append_only_idempotent",
        "original_publisher_provenance_preserved": True,
        "production_admission_allowed": False,
    }


def load_sector_timeline_events(
    *,
    database_path: str | Path | None = None,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """Load nested timeline events without promoting provisional records."""
    rows = load_evidence_records(
        database_path=database_path, record_type="sector_membership"
    )
    selected = [
        row for row in rows
        if batch_id is None or row.get("timeline_batch_id") == batch_id
    ]
    events = [
        row["timeline_event"]
        for row in selected
        if isinstance(row.get("timeline_event"), dict)
    ]
    return {
        "events": events,
        "event_count": len(events),
        "record_count": len(selected),
        "batch_ids": sorted({row.get("timeline_batch_id") for row in selected}),
        "source_validation_status": "review_required",
        "finality_status": "provisional",
        "production_admission_allowed": False,
    }


def replay_persisted_sector_timeline(
    *,
    as_of_date: str,
    decision_time: str,
    allowed_sector_codes: set[str],
    known_security_ids: set[str],
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    """Replay persisted observations using the existing point-in-time rules."""
    loaded = load_sector_timeline_events(database_path=database_path)
    result = build_sector_timeline_snapshot(
        loaded["events"],
        as_of_date=as_of_date,
        decision_time=decision_time,
        allowed_sector_codes=allowed_sector_codes,
        known_security_ids=known_security_ids,
    )
    result["persistence"] = {
        "record_count": loaded["record_count"],
        "batch_ids": loaded["batch_ids"],
        "source_validation_status": loaded["source_validation_status"],
        "finality_status": loaded["finality_status"],
    }
    result["verified"] = False
    result["admission_allowed"] = False
    result["production_admission_allowed"] = False
    return result



def replay_persisted_trusted_sector_timeline(
    *,
    as_of_date: str,
    decision_time: str,
    allowed_sector_codes: set[str],
    known_security_ids: set[str],
    registry_path: str | Path | None,
    freshness_policy_path: str | Path | None,
    hmac_key: str | None,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load append-only timeline evidence and replay it through trust gates."""
    from .trusted_sector_reconciliation import replay_trusted_sector_timeline

    loaded = load_sector_timeline_events(database_path=database_path)
    result = replay_trusted_sector_timeline(
        loaded["events"], as_of_date=as_of_date, decision_time=decision_time,
        allowed_sector_codes=allowed_sector_codes,
        known_security_ids=known_security_ids,
        registry_path=registry_path, freshness_policy_path=freshness_policy_path,
        hmac_key=hmac_key,
    )
    result["persistence"] = {
        "record_count": loaded["record_count"],
        "batch_ids": loaded["batch_ids"],
        "source_validation_status": loaded["source_validation_status"],
        "finality_status": loaded["finality_status"],
    }
    result["production_admission_allowed"] = False
    return result
