"""Steps 92-93: evidence request inventory and event-level source matrix."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from typing import Any

def _dt(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field}_missing_or_invalid")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return result

def build_evidence_request_inventory(*, required_events: list[dict[str, Any]], archived_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a deterministic request list; never infer missing IDs or evidence."""
    by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for artifact in archived_artifacts:
        for event_id in artifact.get("event_ids", []):
            by_event[str(event_id)].append(artifact)
    requests = []
    seen = set()
    for event in required_events:
        event_id = str(event.get("event_id", "")).strip()
        if not event_id or event_id in seen:
            requests.append({"event_id": event_id or None, "status": "INVALID_OR_DUPLICATE_REQUIREMENT"})
            continue
        seen.add(event_id)
        evidence = sorted(by_event.get(event_id, []), key=lambda x: str(x.get("artifact_id", "")))
        publishers = sorted({str(x.get("publisher_id", "")) for x in evidence if x.get("publisher_id")})
        has_primary = any(x.get("source_tier") == "primary_nepse_or_cdsc" for x in evidence)
        requests.append({
            "event_id": event_id,
            "event_type": event.get("event_type"),
            "symbol_or_security_id": event.get("symbol_or_security_id"),
            "effective_date": event.get("effective_date"),
            "status": "EVIDENCE_PRESENT_REVIEW_REQUIRED" if evidence else "EVIDENCE_NOT_SUPPLIED",
            "artifact_ids": [str(x.get("artifact_id")) for x in evidence],
            "publisher_count": len(publishers),
            "primary_evidence_present": has_primary,
            "next_required_action": "independent_review" if evidence and has_primary else "obtain_primary_and_independent_evidence"
        })
    return {"status": "INVENTORY_BUILT", "required_event_count": len(required_events), "requests": requests,
            "unresolved_event_ids": [x["event_id"] for x in requests if x.get("status") != "EVIDENCE_PRESENT_REVIEW_REQUIRED"]}

def reconcile_event_source_matrix(*, assertions: list[dict[str, Any]], verified_artifacts: dict[str, dict[str, Any]], required_event_ids: list[str], decision_cutoff: str) -> dict[str, Any]:
    """Reconcile per-event independent assertions; does not approve price adjustments."""
    cutoff = _dt(decision_cutoff, "decision_cutoff")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors = []
    for index, row in enumerate(assertions):
        try:
            event_id = str(row.get("event_id", "")).strip()
            if not event_id:
                raise ValueError("event_id_missing")
            artifact_id = str(row.get("artifact_id", "")).strip()
            artifact = verified_artifacts.get(artifact_id)
            if not artifact:
                raise ValueError("artifact_not_in_verified_archive")
            if str(row.get("publisher_id", "")) != str(artifact.get("publisher_id", "")):
                raise ValueError("publisher_does_not_match_artifact")
            if str(row.get("sha256", "")).lower() != str(artifact.get("sha256", "")).lower():
                raise ValueError("assertion_hash_does_not_match_artifact")
            if event_id not in artifact.get("event_ids", []):
                raise ValueError("artifact_does_not_cover_event")
            available = _dt(row.get("available_at"), "available_at")
            if available > cutoff:
                raise ValueError("assertion_after_decision_cutoff")
            effective = _dt(row.get("effective_at"), "effective_at")
            if effective < available:
                raise ValueError("effective_at_precedes_available_at")
            grouped[event_id].append({**row, "available_at_parsed": available, "effective_at_parsed": effective})
        except ValueError as exc:
            errors.append({"index": index, "reason": str(exc)})
    results = []
    for event_id in sorted(set(required_event_ids)):
        rows = grouped.get(event_id, [])
        publishers = {str(x.get("publisher_id", "")) for x in rows}
        primary = any(x.get("source_tier") == "primary_nepse_or_cdsc" for x in rows)
        # Compare normalized event facts only; disagreements are surfaced, never averaged.
        facts = {(str(x.get("symbol_or_security_id", "")), str(x.get("event_type", "")),
                  str(x.get("announced_at", "")), str(x.get("effective_at", "")),
                  str(x.get("ex_date", "")), str(x.get("status", "")),
                  str(x.get("factor", "")), str(x.get("factor_method", ""))) for x in rows}
        conflict = len(facts) > 1
        ready = len(publishers) >= 2 and primary and not conflict and not errors
        results.append({"event_id": event_id, "assertion_count": len(rows), "distinct_publishers": len(publishers),
                        "primary_evidence_present": primary, "conflict": conflict,
                        "status": "REVIEW_READY" if ready else "BLOCKED",
                        "blockers": (["two_distinct_publishers_required"] if len(publishers) < 2 else [])
                                    + (["primary_evidence_required"] if not primary else [])
                                    + (["source_assertion_conflict"] if conflict else [])})
    missing = sorted(set(required_event_ids) - set(grouped))
    if errors:
        for result in results:
            result["status"] = "BLOCKED"
    return {"status": "REVIEW_READY" if results and all(x["status"] == "REVIEW_READY" for x in results) and not errors else "BLOCKED",
            "events": results, "missing_event_ids": missing, "errors": errors,
            "historical_admission_allowed": False, "price_adjustment_admission_allowed": False}
