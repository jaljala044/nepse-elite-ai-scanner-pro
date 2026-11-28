"""Read-only bridge from repository-reviewed evidence to continuity preflight."""
from datetime import date, timedelta
from .scanner_eligibility import load_reviewed_rows
from .session_calendar import load_calendar
from .historical_continuity import review_segment

def assess_manifest_segment(symbol, start, end, *, reviewed_path, calendar_path,
                            lifecycle, minimum_bars=120, warmup=0):
    """Lifecycle is a separate trusted historical evidence map, not a current roster.
    Canonical rows must already be accepted by the existing manifest loader.
    Missing price basis remains missing; do not infer it from a review flag.
    """
    reviewed = load_reviewed_rows(reviewed_path)
    calendar = {}
    for day, entry in load_calendar(calendar_path).items():
        if entry["scope"] != "all_securities":
            continue
        status = entry["status"]
        if status == "verified_exceptional_closed":
            status = "verified_closed"
        calendar[day.isoformat()] = {
            "status": status,
            "evidence_id": entry["raw_evidence_sha256"],
        }
    rows = [dict(entry) for (ticker, day), entry in reviewed.items()
            if ticker == symbol and start <= day <= end]
    result = review_segment(symbol, start, end, calendar, lifecycle, rows,
                            minimum_bars=minimum_bars, warmup=warmup)
    result["manifest_rows_in_segment"] = len(rows)
    result["calendar_evidence_days_in_segment"] = sum(
        start <= day <= end for day in calendar)
    return result
