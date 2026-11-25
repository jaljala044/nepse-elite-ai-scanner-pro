"""Point-in-time eligibility and as-of snapshot primitives."""
from __future__ import annotations

from datetime import datetime, timezone


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def eligible_as_of(record: dict, decision_time: str) -> bool:
    available = record.get("available_at")
    if not available:
        return False
    return _aware(available) <= _aware(decision_time)


def build_as_of_snapshot(records: list[dict], decision_time: str) -> dict:
    """Select only records knowable by decision_time; preserve excluded count."""
    cutoff = _aware(decision_time)
    selected = []
    missing_available_indexes = []
    future_excluded_count = 0
    for index, record in enumerate(records):
        available = record.get("available_at")
        if not available:
            missing_available_indexes.append(index)
            continue
        if _aware(available) <= cutoff:
            selected.append(record)
        else:
            future_excluded_count += 1
    selected.sort(key=lambda r: (r.get("available_at", ""), r.get("record_id", "")))
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
