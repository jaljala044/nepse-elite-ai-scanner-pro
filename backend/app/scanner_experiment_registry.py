"""Append-only, hash-chained experiment registry for reproducible scanner research."""
from __future__ import annotations
import hashlib
import json

EVENT_TYPES = {"EXPERIMENT_REGISTERED", "EXPERIMENT_COMPLETED", "EXPERIMENT_REJECTED"}

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)

def _hash(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

def _verify(events):
    previous = "GENESIS"
    seen = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError("registry_event_invalid")
        if event.get("sequence") != index + 1 or event.get("previous_event_hash") != previous:
            raise ValueError("registry_chain_order_or_link_invalid")
        if event.get("event_type") not in EVENT_TYPES or not event.get("run_id"):
            raise ValueError("registry_event_type_or_run_id_invalid")
        if event.get("event_id") in seen:
            raise ValueError("registry_duplicate_event_id")
        body = {k: v for k, v in event.items() if k != "event_hash"}
        digest = _hash(body)
        if event.get("event_hash") != digest:
            raise ValueError("registry_event_hash_mismatch")
        seen.add(event["event_id"])
        previous = digest
    return previous

def append_experiment_events(*, existing_events, new_events):
    """Return a new immutable event list; never edits or deletes prior events."""
    if not isinstance(existing_events, list) or not isinstance(new_events, list):
        raise ValueError("registry_event_lists_required")
    previous = _verify(existing_events)
    result = list(existing_events)
    known_ids = {e["event_id"] for e in existing_events}
    for raw in new_events:
        if not isinstance(raw, dict) or raw.get("event_type") not in EVENT_TYPES:
            raise ValueError("registry_new_event_invalid")
        event_id = raw.get("event_id")
        run_id = raw.get("run_id")
        occurred_at = raw.get("occurred_at")
        if not isinstance(event_id, str) or not event_id or event_id in known_ids:
            raise ValueError("registry_event_id_missing_or_duplicate")
        if not isinstance(run_id, str) or not run_id or not isinstance(occurred_at, str) or not occurred_at:
            raise ValueError("registry_run_id_or_timestamp_missing")
        payload = raw.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("registry_event_payload_required")
        body = {"sequence": len(result) + 1, "event_id": event_id,
            "event_type": raw["event_type"], "run_id": run_id,
            "occurred_at": occurred_at, "payload": payload,
            "previous_event_hash": previous}
        digest = _hash(body)
        event = {**body, "event_hash": digest}
        result.append(event)
        known_ids.add(event_id)
        previous = digest
    return {"schema_version": "nepse-experiment-registry-1.0.0",
        "events": result, "event_count": len(result),
        "head_hash": previous, "append_only": True,
        "limitations": ["Hash chaining detects later edits but does not provide external timestamping, access control, durable storage or signer identity.",
            "Persist returned events in versioned, access-controlled storage; never overwrite prior snapshots."]}
