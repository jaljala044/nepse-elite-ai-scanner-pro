"""Point-in-time eligibility and as-of snapshot primitives."""
from __future__ import annotations

from datetime import datetime, timezone


def _aware(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamps must be nonblank ISO-8601 strings")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamps must be valid ISO-8601 values") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def eligible_as_of(record: dict, decision_time: str) -> bool:
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    cutoff = _aware(decision_time)
    available = record.get("available_at")
    if available is None or available == "":
        return False
    return _aware(available) <= cutoff


def build_as_of_snapshot(records: list[dict], decision_time: str) -> dict:
    """Select only records knowable by decision_time; preserve excluded count."""
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    cutoff = _aware(decision_time)
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("records must contain objects")
    selected = []
    missing_available_indexes = []
    future_excluded_count = 0
    for index, record in enumerate(records):
        available = record.get("available_at")
        if available is None or available == "":
            missing_available_indexes.append(index)
            continue
        if _aware(available) <= cutoff:
            selected.append(record)
        else:
            future_excluded_count += 1
    for index, record in enumerate(records):
        record_id = record.get("record_id")
        if record_id is not None and (not isinstance(record_id, str) or not record_id.strip()):
            raise ValueError(f"record {index}: record_id must be a nonblank string when supplied")
    selected.sort(key=lambda r: (_aware(r["available_at"]), r.get("record_id", "")))
    max_available = max(
        (_aware(r["available_at"]) for r in selected), default=None
    )
    if max_available and max_available > cutoff:
        raise AssertionError("point-in-time leakage detected")
    return {
        "decision_time": cutoff.isoformat().replace("+00:00", "Z"),
        "records": selected,
        "included_count": len(selected),
        "excluded_count": len(records) - len(selected),
        "missing_available_at_count": len(missing_available_indexes),
        "missing_available_at_record_indexes": missing_available_indexes,
        "future_excluded_count": future_excluded_count,
        "max_input_available_at": (
            max_available.isoformat().replace("+00:00", "Z") if max_available else None
        ),
        "point_in_time_eligible": all(
            _aware(r["available_at"]) <= cutoff for r in selected
        ),
    }
