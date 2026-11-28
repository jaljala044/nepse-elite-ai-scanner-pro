"""Steps 120-129: evidence capture admission and BENH/predecessor research status."""
from __future__ import annotations
from datetime import date
from typing import Any

def validate_close_only_capture(payload: dict[str, Any]) -> dict[str, Any]:
    records = payload.get("records", [])
    errors = []
    if payload.get("symbol") != "BENH":
        errors.append("unexpected_symbol")
    if not payload.get("source_url") or not payload.get("raw_excerpt_sha256"):
        errors.append("missing_source_provenance_or_hash")
    if payload.get("data_scope") != "daily_close_only":
        errors.append("unexpected_data_scope")
    seen = set()
    for i, row in enumerate(records):
        try:
            day = date.fromisoformat(row["session_date"])
            close = float(row["close"])
            if row.get("symbol") != "BENH" or close <= 0:
                raise ValueError("invalid_symbol_or_close")
            if day.isoformat() in seen:
                raise ValueError("duplicate_session")
            seen.add(day.isoformat())
            if row.get("field_coverage") != ["close"]:
                raise ValueError("field_coverage_mismatch")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"row_{i}:{exc}")
    expected_count = payload.get("record_count")
    if expected_count != len(records):
        errors.append("record_count_mismatch")
    return {"status": "RESEARCH_ONLY_CLOSE_SERIES" if records and not errors else "REJECTED",
            "accepted_records": len(records) if not errors else 0,
            "errors": errors, "ohlcv_eligible": False,
            "floorsheet_eligible": False, "production_admission_allowed": False}

def detect_expected_date_gaps(*, observed_dates: list[str], expected_dates: list[str]) -> list[str]:
    observed = set(observed_dates)
    return [date.fromisoformat(d).isoformat() for d in expected_dates if date.fromisoformat(d).isoformat() not in observed]

def classify_benh_history_coverage(*, listing_date: str, scheduled_first_trade_date: str,
                                  first_observed_close_date: str, observed_sessions: int,
                                  floorsheet_coverage_verified: bool) -> dict[str, Any]:
    listing = date.fromisoformat(listing_date)
    scheduled = date.fromisoformat(scheduled_first_trade_date)
    observed = date.fromisoformat(first_observed_close_date)
    errors = []
    if scheduled < listing:
        errors.append("scheduled_trade_precedes_listing")
    if observed < scheduled:
        errors.append("observed_close_precedes_scheduled_trade")
    if observed > scheduled:
        errors.append("scheduled_first_trade_session_missing_from_close_capture")
    if observed_sessions <= 0:
        errors.append("no_observed_sessions")
    return {"symbol": "BENH", "listing_date": listing.isoformat(),
            "scheduled_first_trade_date": scheduled.isoformat(),
            "first_observed_close_date": observed.isoformat(),
            "observed_close_sessions": observed_sessions,
            "floorsheet_coverage_verified": bool(floorsheet_coverage_verified),
            "status": "PARTIAL_EVIDENCE" if errors or not floorsheet_coverage_verified else "REVIEW_REQUIRED",
            "errors": errors, "first_trade_date_verified": False,
            "ohlcv_history_complete": False, "production_admission_allowed": False}

def assess_predecessor_lineage(*, predecessor: str, successor: str | None,
                               event_date: str | None, evidence_refs: list[str],
                               primary_evidence_acquired: bool,
                               evidence_summary: str | None = None) -> dict[str, Any]:
    allowed = {"BPW", "JALPA", "KLBSL", "MKLB"}
    code = predecessor.strip().upper()
    if code not in allowed:
        return {"predecessor": code, "status": "OUT_OF_SCOPE", "production_identity_approved": False}
    if event_date:
        try:
            date.fromisoformat(event_date)
        except ValueError:
            return {"predecessor": code, "status": "BLOCKED", "errors": ["invalid_event_date"],
                    "production_identity_approved": False}
    if not successor or not evidence_refs:
        status = "UNRESOLVED"
    elif primary_evidence_acquired:
        status = "PRIMARY_EVIDENCE_REVIEW"
    else:
        status = "SECONDARY_CANDIDATE"
    return {"predecessor": code, "successor": successor, "event_date": event_date,
            "evidence_refs": evidence_refs, "primary_evidence_acquired": primary_evidence_acquired,
            "evidence_summary": evidence_summary, "status": status,
            "production_identity_approved": False}

def build_acquisition_readiness() -> dict[str, Any]:
    return {
      "sharehub": {"status":"ACCESS_REQUIRED","reason":"Published historical price-history API requires a Data API account/licence, allow-listed server IP and enabled price-history service."},
      "chukul": {"status":"FETCH_BLOCKED","reason":"Public chart/floorsheet pages returned empty rendered content in this capture."},
      "sharesansar": {"status":"PARTIAL_CAPTURE","reason":"Company profile and dated listing/trading articles are readable; historical OHLCV tab and historical floorsheet rows were not extracted."},
      "floorsheet_archive": {"status":"NOT_ACQUIRED","reason":"Only current/dynamic floorsheet page surfaced; no BENH historical archive or verified coverage bounds acquired."},
      "production_admission_allowed": False
    }
