"""Point-in-time source completeness and data-quality gate.

This is a research diagnostic adapter. It consumes independently reviewed
calendar and source-policy inputs; it does not certify publishers, populate
the calendar, repair canonical OHLCV, or authorize trading recommendations.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import re
from typing import Any

_SHA = re.compile(r"^[0-9a-f]{64}$")
CANDIDATE_ADAPTERS = (
    {"source_id": "sharesansar", "name": "ShareSansar", "status": "candidate_unreviewed"},
    {"source_id": "chukul", "name": "Chukul", "status": "candidate_unreviewed"},
    {"source_id": "sharehub_nepal", "name": "ShareHub Nepal", "status": "candidate_unreviewed"},
    {"source_id": "punji", "name": "Punji", "status": "candidate_unreviewed"},
    {"source_id": "merolagani", "name": "Merolagani", "status": "candidate_unreviewed"},
    {"source_id": "nepsealpha", "name": "NepseAlpha", "status": "candidate_unreviewed"},
    {"source_id": "chartnepali", "name": "ChartNepali", "status": "candidate_unreviewed"},
    {"source_id": "bullhouse_investment", "name": "Bullhouse Investment", "status": "candidate_unreviewed"},
)


def _instant(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_timezone_aware_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_invalid_iso_timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_timezone_aware_required")
    return parsed.astimezone(timezone.utc)


def _day(value: Any, field: str) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}_invalid_iso_date") from exc


def _digest(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA.fullmatch(value.lower()))


def validate_calendar_sessions(rows: list[dict], *, decision_time: str) -> dict:
    """Accept only reviewed, source-linked open sessions available by cutoff."""
    cutoff = _instant(decision_time, "decision_time")
    sessions, rejected = {}, []
    for index, row in enumerate(rows):
        try:
            day = _day(row.get("date"), "calendar_date")
            available = _instant(row.get("available_at"), "calendar_available_at")
            if available > cutoff:
                raise ValueError("calendar_evidence_not_available_at_cutoff")
            if row.get("status") != "confirmed_open":
                raise ValueError("calendar_session_not_confirmed_open")
            if row.get("review_status") != "reviewed":
                raise ValueError("calendar_review_not_complete")
            if not str(row.get("source_id") or "").strip() or not _digest(row.get("source_payload_sha256")):
                raise ValueError("calendar_source_lineage_missing")
            if day in sessions:
                raise ValueError("duplicate_calendar_session")
            sessions[day] = {**row, "date": day, "available_at": available.isoformat()}
        except (ValueError, TypeError, AttributeError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    return {
        "sessions": sessions, "accepted_session_count": len(sessions),
        "rejected": rejected, "status": "verified_input" if sessions and not rejected else "incomplete",
        "calendar_population_allowed": False,
    }


def validate_capture_policy(policy: dict) -> dict:
    """Validate explicit per-source/dataset expectations; never infer daily cadence."""
    if not isinstance(policy, dict):
        raise ValueError("capture_policy_must_be_object")
    source_id = str(policy.get("source_id") or "").strip()
    dataset = str(policy.get("dataset") or "").strip()
    sessions = policy.get("expected_sessions")
    max_age = policy.get("max_age_hours")
    if not source_id or not dataset:
        raise ValueError("capture_policy_source_and_dataset_required")
    if policy.get("review_status") != "reviewed" or not str(policy.get("reviewer_id") or "").strip():
        raise ValueError("capture_policy_requires_reviewed_reviewer")
    if not isinstance(sessions, list):
        raise ValueError("expected_sessions_must_be_explicit_list")
    normalized = [_day(item, "expected_session") for item in sessions]
    if len(normalized) != len(set(normalized)):
        raise ValueError("duplicate_expected_session")
    if isinstance(max_age, bool) or not isinstance(max_age, (int, float)) or max_age <= 0:
        raise ValueError("max_age_hours_must_be_positive")
    return {**policy, "source_id": source_id, "dataset": dataset,
            "expected_sessions": sorted(normalized)}


def _capture_index(captures: list[dict], cutoff: datetime) -> tuple[dict, list]:
    index, rejected = {}, []
    for n, capture in enumerate(captures):
        try:
            source = str(capture.get("source_id") or "").strip()
            dataset = str(capture.get("dataset") or "").strip()
            day = _day(capture.get("session_date"), "capture_session")
            available = _instant(capture.get("available_at"), "capture_available_at")
            captured = _instant(capture.get("captured_at"), "capture_captured_at")
            if not source or not dataset or not _digest(capture.get("payload_sha256")):
                raise ValueError("capture_source_dataset_or_payload_hash_missing")
            if captured > available:
                raise ValueError("capture_available_before_capture")
            if available > cutoff:
                rejected.append({"index": n, "reason": "capture_not_available_at_cutoff"})
                continue
            key = (source, dataset, day)
            if key in index:
                raise ValueError("duplicate_source_dataset_session_capture")
            index[key] = {**capture, "available_at": available, "captured_at": captured}
        except (ValueError, TypeError, AttributeError) as exc:
            rejected.append({"index": n, "reason": str(exc)})
    return index, rejected


def _outage_covers(events: list[dict], source_id: str, day: str, cutoff: datetime) -> bool:
    opened = None
    relevant = []
    for event in events:
        if event.get("source_id") != source_id or event.get("event_type") not in {"outage_started", "outage_resolved", "source_suspended", "source_recovered"}:
            continue
        try:
            when = _instant(event.get("available_at"), "outage_available_at")
            effective = _day(event.get("effective_date"), "outage_effective_date")
        except ValueError:
            continue
        if when <= cutoff and effective <= day:
            relevant.append((effective, when, event.get("event_type")))
    for _, _, typ in sorted(relevant):
        if typ in {"outage_started", "source_suspended"}:
            opened = True
        elif typ in {"outage_resolved", "source_recovered"}:
            opened = False
    return opened is True


def assess_source_capture_completeness(
    policies: list[dict], captures: list[dict], calendar: dict,
    *, decision_time: str, reliability_events: list[dict] | None = None,
) -> dict:
    """Differentiate observed capture, delayed/missing capture and declared outage."""
    cutoff = _instant(decision_time, "decision_time")
    session_map = calendar.get("sessions", {}) if isinstance(calendar, dict) else {}
    capture_map, rejected = _capture_index(captures, cutoff)
    rows = []
    for raw_policy in policies:
        policy = validate_capture_policy(raw_policy)
        for day in policy["expected_sessions"]:
            if day not in session_map:
                rows.append({"source_id": policy["source_id"], "dataset": policy["dataset"],
                             "session_date": day, "status": "calendar_unverified"})
                continue
            key = (policy["source_id"], policy["dataset"], day)
            capture = capture_map.get(key)
            if capture:
                age = cutoff - capture["available_at"]
                max_age = timedelta(hours=float(policy["max_age_hours"]))
                status = "captured_fresh" if age <= max_age else "captured_stale"
                rows.append({"source_id": policy["source_id"], "dataset": policy["dataset"],
                             "session_date": day, "status": status,
                             "payload_sha256": capture["payload_sha256"],
                             "available_at": capture["available_at"].isoformat()})
            elif _outage_covers(reliability_events or [], policy["source_id"], day, cutoff):
                status = "declared_outage"
                rows.append({"source_id": policy["source_id"], "dataset": policy["dataset"],
                             "session_date": day, "status": status})
            else:
                rows.append({"source_id": policy["source_id"], "dataset": policy["dataset"],
                             "session_date": day, "status": "missing_or_delayed"})
    counts = {name: sum(row["status"] == name for row in rows) for name in
              ("captured_fresh", "captured_stale", "missing_or_delayed", "declared_outage", "calendar_unverified")}
    return {"rows": rows, "counts": counts, "rejected_captures": rejected,
            "status": "complete" if rows and all(r["status"] == "captured_fresh" for r in rows) else "incomplete",
            "coverage_inference_from_weekdays": False}


def resolve_record_corrections(records: list[dict], *, decision_time: str) -> dict:
    """Keep every version; select only the latest eligible, explicitly linked version."""
    cutoff = _instant(decision_time, "decision_time")
    by_id, rejected = {}, []
    for index, record in enumerate(records):
        rid = str(record.get("record_id") or "").strip()
        if not rid or rid in by_id:
            raise ValueError("record_ids_must_be_present_and_unique")
        available = _instant(record.get("available_at"), "record_available_at")
        if available <= cutoff:
            by_id[rid] = {**record, "available_at": available}
        else:
            rejected.append({"record_id": rid, "reason": "not_available_at_cutoff"})
    superseded, children, invalid = set(), {}, set()
    for rid, record in by_id.items():
        prior = record.get("supersedes_record_id")
        if prior:
            if prior not in by_id:
                rejected.append({"record_id": rid, "reason": "superseded_record_missing_at_cutoff"})
                invalid.add(rid)
                continue
            if prior == rid or prior in children:
                raise ValueError("invalid_or_forked_correction_chain")
            children[prior] = rid
            superseded.add(prior)
    for rid in by_id:
        seen, cursor = set(), rid
        while cursor in children:
            if cursor in seen:
                raise ValueError("correction_cycle_detected")
            seen.add(cursor)
            cursor = children[cursor]
    # A correction with a missing predecessor is not an eligible active record.
    # Propagate that invalidity through every descendant in its correction chain.
    for rid in tuple(invalid):
        cursor = rid
        while cursor in children:
            cursor = children[cursor]
            invalid.add(cursor)
    active = [record for rid, record in by_id.items()
              if rid not in superseded and rid not in invalid]
    return {"all_versions": list(by_id.values()), "active_versions": active,
            "superseded_record_ids": sorted(superseded), "rejected": rejected,
            "correction_history_preserved": True, "canonical_correction_applied": False}


def reconcile_source_observations(observations: list[dict]) -> dict:
    """Compare source values while retaining disagreement; no majority promotion."""
    groups = {}
    for row in observations:
        key = (str(row.get("dataset") or ""), str(row.get("symbol") or "").upper(),
               _day(row.get("session_date"), "observation_session"))
        source = str(row.get("source_id") or "").strip()
        if not source or "value" not in row:
            raise ValueError("observation_source_and_value_required")
        groups.setdefault(key, []).append(row)
    results = []
    for (dataset, symbol, day), rows in sorted(groups.items()):
        sources = {row["source_id"] for row in rows}
        values = {str(row["value"]) for row in rows}
        status = "single_source_only" if len(sources) == 1 else (
            "sources_agree" if len(values) == 1 else "conflicting_sources")
        results.append({"dataset": dataset, "symbol": symbol, "session_date": day,
                        "source_count": len(sources), "distinct_value_count": len(values),
                        "status": status, "observations": rows,
                        "canonical_value": None})
    return {"results": results, "conflict_count": sum(r["status"] == "conflicting_sources" for r in results),
            "promotion_allowed": False, "policy": "retain_all_source_values_no_majority_rule"}


def build_data_quality_report(
    *, calendar: dict, completeness: dict, reconciliation: dict,
    record_corrections: dict | None = None,
) -> dict:
    """Conservative evidence coverage classification; missing inputs never score neutral."""
    reasons = []
    if calendar.get("status") != "verified_input":
        reasons.append("calendar_evidence_incomplete")
    if completeness.get("status") != "complete":
        reasons.append("source_capture_completeness_incomplete")
    if reconciliation.get("conflict_count", 0):
        reasons.append("cross_source_conflicts_unresolved")
    if not reconciliation.get("results"):
        reasons.append("cross_source_observations_missing")
    if record_corrections is None:
        reasons.append("correction_history_not_supplied")
    quality = "HIGH" if not reasons else "LOW"
    return {"data_quality": quality, "confidence": "HIGH" if quality == "HIGH" else "LOW",
            "reasons": reasons, "calendar_session_count": calendar.get("accepted_session_count", 0),
            "capture_counts": completeness.get("counts", {}),
            "cross_source_conflict_count": reconciliation.get("conflict_count"),
            "source_adapter_candidates": list(CANDIDATE_ADAPTERS),
            "ohlcv_admission_allowed": False, "floorsheet_admission_allowed": False,
            "scanner_recommendations_enabled": False,
            "note": "Research diagnostic only; even HIGH describes input coverage, not exchange certification or canonical approval."}


def gate_market_record(record: dict, *, dataset: str, quality_report: dict) -> dict:
    """Annotate OHLCV/floorsheet rows without allowing this adapter to promote them."""
    if dataset not in {"ohlcv", "floorsheet"}:
        raise ValueError("dataset_must_be_ohlcv_or_floorsheet")
    reasons = []
    if quality_report.get("data_quality") != "HIGH":
        reasons.append("source_data_quality_not_high")
    if record.get("source_id") not in {row["source_id"] for row in CANDIDATE_ADAPTERS}:
        # Unknown is not necessarily untrustworthy, but cannot pass this diagnostic gate.
        reasons.append("source_adapter_not_catalogued")
    if not _digest(record.get("source_payload_sha256")):
        reasons.append("record_payload_hash_missing")
    return {**record, "dataset": dataset,
            "quality_status": "LOW" if reasons else "HIGH",
            "quality_reasons": reasons,
            "eligible_for_research_review": not reasons,
            "production_admission_allowed": False,
            "recommendation_authorization": False}
