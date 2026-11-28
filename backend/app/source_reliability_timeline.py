"""Point-in-time source reliability timeline for NEPSE research evidence.

This module records source identity/availability events without approving a
publisher, asserting legal ownership, or promoting any evidence to production.
All event histories are append-only inputs; caller-owned persistence must retain
the original bytes and digest returned by :func:`build_source_event_manifest`.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json
from typing import Any
from urllib.parse import urlparse

CANDIDATE_SOURCES = (
    {"source_id": "sharesansar", "name": "ShareSansar", "status": "candidate_unreviewed"},
    {"source_id": "chukul", "name": "Chukul", "status": "candidate_unreviewed"},
    {"source_id": "sharehub_nepal", "name": "ShareHub Nepal", "status": "candidate_unreviewed"},
    {"source_id": "punji", "name": "Punji", "status": "candidate_unreviewed"},
    {"source_id": "merolagani", "name": "Merolagani", "status": "candidate_unreviewed"},
    {"source_id": "nepsealpha", "name": "NepseAlpha", "status": "candidate_unreviewed"},
    {"source_id": "chartnepali", "name": "ChartNepali", "status": "candidate_unreviewed"},
    {"source_id": "bullhouse_investment", "name": "Bullhouse Investment", "status": "candidate_unreviewed"},
)
EVENT_TYPES = {
    "source_registered", "hostname_changed", "ownership_group_changed",
    "source_suspended", "source_recovered", "outage_started",
    "outage_resolved", "source_corrected",
}
HEALTHY_CAPTURE_TYPES = {"capture_succeeded", "source_recovered"}


def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_timezone_aware_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_timezone_aware_required") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_timezone_aware_required")
    return parsed.astimezone(timezone.utc)


def _host(url: Any) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return parsed.hostname.lower()


def build_source_event_manifest(events: list[dict[str, Any]], *, batch_id: str,
                                captured_at: str, received_at: str) -> dict[str, Any]:
    """Validate and hash an immutable source-event batch; no trust promotion."""
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id_required")
    captured, received = _time(captured_at, "captured_at"), _time(received_at, "received_at")
    if received < captured:
        raise ValueError("received_before_capture")
    if not isinstance(events, list) or not events:
        raise ValueError("events_required")
    seen = set()
    normalized = []
    for i, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"event_{i}_must_be_object")
        event_id = str(event.get("event_id") or "").strip()
        source_id = str(event.get("source_id") or "").strip()
        event_type = event.get("event_type")
        if not event_id or event_id in seen:
            raise ValueError(f"event_{i}_id_missing_or_duplicate")
        seen.add(event_id)
        if not source_id:
            raise ValueError(f"event_{i}_source_id_required")
        if event_type not in EVENT_TYPES | {"capture_succeeded"}:
            raise ValueError(f"event_{i}_type_unsupported")
        effective = date.fromisoformat(str(event.get("effective_date") or ""))
        event_captured = _time(event.get("captured_at"), f"event_{i}_captured_at")
        available = _time(event.get("available_at"), f"event_{i}_available_at")
        if event_captured < captured or event_captured > received or available < event_captured or available > received:
            raise ValueError(f"event_{i}_event_time_outside_batch_window")
        item = dict(event)
        item["effective_date"] = effective.isoformat()
        item["captured_at"] = event_captured.isoformat()
        item["available_at"] = available.isoformat()
        if event_type == "capture_succeeded":
            if not _host(event.get("source_url")):
                raise ValueError(f"event_{i}_successful_capture_requires_https_source_url")
            digest = str(event.get("payload_sha256") or "").lower()
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(f"event_{i}_successful_capture_requires_sha256")
        if event_type == "hostname_changed":
            old_host, new_host = event.get("old_host"), event.get("new_host")
            if not old_host or not new_host or old_host.lower() == new_host.lower():
                raise ValueError(f"event_{i}_hostname_change_requires_distinct_hosts")
        if event_type == "ownership_group_changed":
            if not event.get("old_ownership_group_id") or not event.get("new_ownership_group_id"):
                raise ValueError(f"event_{i}_ownership_change_requires_both_groups")
        normalized.append(item)
    normalized.sort(key=lambda row: (row["effective_date"], row["available_at"], row["event_id"]))
    payload = json.dumps({"batch_id": batch_id, "events": normalized},
                         sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {
        "batch_id": batch_id, "events": normalized,
        "payload_sha256": sha256(payload).hexdigest(), "payload_bytes": len(payload),
        "captured_at": captured.isoformat(), "received_at": received.isoformat(),
        "immutability": "append_only_input_manifest",
        "publisher_approval": False, "production_admission_allowed": False,
    }


def replay_source_reliability(events: list[dict[str, Any]], *,
                              decision_time: str,
                              verified_session_dates: list[str] | None = None,
                              expected_source_ids: list[str] | None = None) -> dict[str, Any]:
    """Replay source lifecycle at a cutoff and report session coverage/outages.

    verified_session_dates must come from an independently validated exchange
    calendar. Candidate weekdays are intentionally not accepted as sessions.
    """
    cutoff = _time(decision_time, "decision_time")
    sessions = sorted({date.fromisoformat(x).isoformat() for x in (verified_session_dates or [])})
    expected = sorted(set(expected_source_ids or []))
    eligible, excluded = [], []
    for i, event in enumerate(events):
        if not isinstance(event, dict):
            excluded.append({"index": i, "reason": "invalid_event"})
            continue
        try:
            available = _time(event.get("available_at"), f"event_{i}_available_at")
            effective = date.fromisoformat(str(event.get("effective_date") or ""))
        except ValueError:
            excluded.append({"index": i, "reason": "invalid_event_time_or_date"})
            continue
        if available > cutoff or effective > cutoff.date():
            excluded.append({"index": i, "reason": "not_available_at_historical_cutoff"})
            continue
        if event.get("event_type") not in EVENT_TYPES | {"capture_succeeded"}:
            excluded.append({"index": i, "reason": "unsupported_event_type"})
            continue
        eligible.append(event)
    eligible.sort(key=lambda row: (row["effective_date"], row["available_at"], row.get("event_id", "")))
    by_source: dict[str, list[dict[str, Any]]] = {}
    for event in eligible:
        sid = str(event.get("source_id") or "").strip()
        if sid:
            by_source.setdefault(sid, []).append(event)
    reports = {}
    for sid in sorted(set(expected) | set(by_source)):
        rows = by_source.get(sid, [])
        suspended = False
        outage_open = False
        outage_start = None
        host_changes, ownership_changes, corrections = [], [], []
        successful_sessions = set()
        transitions = []
        for event in rows:
            typ = event["event_type"]
            if typ == "source_suspended":
                suspended = True
            elif typ == "source_recovered":
                suspended = False
                outage_open = False
                outage_start = None
            elif typ == "outage_started":
                outage_open, outage_start = True, event["effective_date"]
            elif typ == "outage_resolved":
                outage_open, outage_start = False, None
            elif typ == "hostname_changed":
                host_changes.append({"date": event["effective_date"], "old_host": event.get("old_host"),
                                     "new_host": event.get("new_host"), "review_required": True})
            elif typ == "ownership_group_changed":
                ownership_changes.append({"date": event["effective_date"],
                    "old_group": event.get("old_ownership_group_id"),
                    "new_group": event.get("new_ownership_group_id"), "review_required": True})
            elif typ == "source_corrected":
                corrections.append({"date": event["effective_date"], "correction_ref": event.get("correction_ref"),
                                    "review_required": True})
            elif typ == "capture_succeeded":
                successful_sessions.add(event["effective_date"])
            transitions.append({"date": event["effective_date"], "event_type": typ})
        missing = sorted(set(sessions) - successful_sessions)
        reports[sid] = {
            "status": "suspended" if suspended else "outage_open" if outage_open else
                      "healthy_capture_observed" if successful_sessions else "no_capture_evidence",
            "successful_capture_sessions": sorted(successful_sessions),
            "missing_verified_sessions": missing,
            "session_coverage": (len(set(sessions) & successful_sessions) / len(sessions)) if sessions else None,
            "session_calendar_status": "verified_sessions_supplied" if sessions else "calendar_unconfigured",
            "open_outage_since": outage_start,
            "hostname_changes": host_changes, "ownership_group_changes": ownership_changes,
            "corrections": corrections, "event_history": transitions,
            "review_required": bool(host_changes or ownership_changes or corrections),
        }
    missing_sources = sorted(set(expected) - set(by_source))
    return {
        "status": "assessed" if sessions else "calendar_unconfigured",
        "decision_time": cutoff.isoformat(), "source_count": len(reports),
        "sources": reports, "missing_expected_sources": missing_sources,
        "excluded_future_or_invalid_event_count": len(excluded), "excluded_events": excluded,
        "verified_session_count": len(sessions),
        "candidate_catalog": [dict(row, approved=False, hostname_verified=False) for row in CANDIDATE_SOURCES],
        "production_admission_allowed": False, "recommendation_override": False,
        "limitations": [
            "Candidate source names are not approved publishers; hostnames and ownership require independent review.",
            "A successful capture proves retrieval only, not correctness, completeness, exchange authority or redistribution rights.",
            "Session coverage is computed only when verified exchange-session dates are explicitly supplied.",
            "No outages are inferred from absent data unless expected sessions are supplied.",
        ],
    }
