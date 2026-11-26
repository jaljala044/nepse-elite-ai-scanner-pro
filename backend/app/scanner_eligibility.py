"""Eligibility checks over server-reviewed evidence, never upload assertions."""
from datetime import date, datetime
from .scanner import quality_errors
from .point_in_time import eligible_as_of

APPROVED_SOURCES = {"sharehub", "chukul", "sharesansar", "nepsealpha", "nepse"}
OPEN = {"verified_open", "verified_exceptional_open"}

def assess(symbol, rows, decision_time, reviewed):
    errors = quality_errors(rows)
    if not rows:
        errors.append("no_rows")
    if errors:
        return errors
    for row in rows:
        day = str(row["date"])
        record = reviewed.get((symbol, day), {})
        if record.get("instrument_type") != "equity" or record.get("security_status") != "active":
            errors.append(day+":equity_eligibility_unverified")
        if record.get("session_status") not in OPEN:
            errors.append(day+":session_unverified")
        if record.get("source_id") not in APPROVED_SOURCES or not record.get("evidence_id"):
            errors.append(day+":source_unverified")
        if any(record.get(k) != row.get(k) for k in ("open","high","low","close","volume")):
            errors.append(day+":reviewed_values_mismatch")
        try:
            if not eligible_as_of(record, decision_time):
                errors.append(day+":availability_unverified_or_future")
        except (ValueError, TypeError, AttributeError):
            errors.append(day+":invalid_availability")
    return errors

# Populated only by a future trusted canonical evidence loader.
REVIEWED_ROWS = {}
