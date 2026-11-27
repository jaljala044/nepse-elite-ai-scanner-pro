"""Point-in-time eligibility gate for historical security segments."""
from __future__ import annotations
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_ALLOWED_SESSION_STATES = {"traded", "no_trade_verified"}

def _date(value):
    try: return date.fromisoformat(str(value))
    except (TypeError, ValueError): return None

def _timestamp(value):
    try: parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError): return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None

def _positive_decimal(value):
    try: number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError): return None
    return number if number.is_finite() and number > 0 else None

def evaluate_historical_segment(*, segment, expected_sessions, session_statuses,
                                records, required_sessions, available_warmup_sessions,
                                decision_cutoff):
    """Fail-closed lifecycle, completeness, provenance and point-in-time check."""
    reasons = []
    segment = segment if isinstance(segment, dict) else {}
    statuses = session_statuses if isinstance(session_statuses, dict) else {}
    rows = records if isinstance(records, (list, tuple)) else []
    cutoff = _timestamp(decision_cutoff)
    if cutoff is None: reasons.append("decision_cutoff_not_timezone_aware")

    if not segment.get("symbol") or not segment.get("security_id"):
        reasons.append("instrument_identity_missing")
    if segment.get("identity_verified") is not True:
        reasons.append("instrument_identity_not_verified")
    if segment.get("boundary_reviewed") is not True:
        reasons.append("instrument_lifecycle_boundary_not_reviewed")
    if segment.get("suspension_overlap") is not False:
        reasons.append("suspension_overlap_unknown_or_present")
    if segment.get("merger_or_successor_boundary") is not False:
        reasons.append("merger_or_successor_boundary_unknown_or_crossed")
    basis = segment.get("adjustment_basis")
    if basis not in {"raw", "split_adjusted", "total_return_adjusted"}:
        reasons.append("adjustment_basis_missing_or_unsupported")

    start, end_raw = _date(segment.get("effective_from")), segment.get("effective_to")
    end = _date(end_raw) if end_raw is not None else None
    if start is None: reasons.append("effective_from_invalid")
    if end_raw is not None and end is None: reasons.append("effective_to_invalid")
    if start is not None and end is not None and end < start:
        reasons.append("invalid_effective_interval")

    try:
        min_warmup = int(segment.get("minimum_warmup_sessions", 0))
        warmup, required = int(available_warmup_sessions), int(required_sessions)
    except (TypeError, ValueError):
        min_warmup, warmup, required = 1, 0, 1
        reasons.append("session_requirements_invalid")
    if required <= 0:
        reasons.append("required_sessions_invalid")
        required = 1
    if warmup < max(1, min_warmup): reasons.append("insufficient_causal_warmup")

    raw_expected = expected_sessions if isinstance(expected_sessions, (list, tuple)) else []
    expected = []
    for value in raw_expected:
        parsed = _date(value)
        if parsed is None: reasons.append("expected_session_date_invalid:" + str(value))
        else: expected.append(parsed.isoformat())
    if len(expected) != len(set(expected)): reasons.append("duplicate_expected_session")
    if expected != sorted(expected): reasons.append("expected_sessions_not_ascending")
    if len(expected) != required: reasons.append("expected_session_count_mismatch")

    row_map, duplicates = {}, set()
    for row in rows:
        if not isinstance(row, dict):
            reasons.append("malformed_bar_record")
            continue
        parsed = _date(row.get("session_date"))
        if parsed is None:
            reasons.append("bar_session_date_invalid")
            continue
        day = parsed.isoformat()
        if day in row_map:
            duplicates.add(day)
            reasons.append("duplicate_bar:" + day)
        else: row_map[day] = row

    traded_count = no_trade_count = 0
    for day in expected:
        state = statuses.get(day)
        if state not in _ALLOWED_SESSION_STATES:
            reasons.append("session_status_unverified:" + day)
            continue
        if state == "no_trade_verified":
            no_trade_count += 1
            if day in row_map: reasons.append("bar_present_on_verified_no_trade_session:" + day)
            continue
        traded_count += 1
        row = row_map.get(day)
        if row is None:
            reasons.append("missing_bar:" + day)
            continue
        if row.get("symbol") != segment.get("symbol") or str(row.get("security_id")) != str(segment.get("security_id")):
            reasons.append("instrument_identity_mismatch:" + day)
        if (start is not None and day < start.isoformat()) or (end is not None and day > end.isoformat()):
            reasons.append("session_outside_instrument_effective_interval:" + day)
        if row.get("adjustment_basis") != basis: reasons.append("adjustment_basis_mismatch:" + day)
        if row.get("rights_status") != "approved": reasons.append("source_rights_not_approved:" + day)
        digest = row.get("evidence_sha256")
        if not isinstance(digest, str) or not _HASH_RE.fullmatch(digest):
            reasons.append("evidence_hash_missing_or_invalid:" + day)
        available = _timestamp(row.get("available_at"))
        if available is None: reasons.append("available_at_not_timezone_aware:" + day)
        elif cutoff is not None and available > cutoff:
            reasons.append("lookahead_available_after_cutoff:" + day)
        prices = {key: _positive_decimal(row.get(key)) for key in ("open", "high", "low", "close")}
        if any(value is None for value in prices.values()):
            reasons.append("ohlc_invalid:" + day)
        elif prices["high"] < max(prices.values()) or prices["low"] > min(prices.values()):
            reasons.append("ohlc_relationship_invalid:" + day)
        if _positive_decimal(row.get("volume")) is None: reasons.append("volume_invalid:" + day)

    if traded_count < required: reasons.append("insufficient_traded_sessions")
    for day in row_map:
        if day not in set(expected): reasons.append("bar_outside_expected_session_set:" + day)
    reasons = list(dict.fromkeys(reasons))
    eligible = not reasons
    return {
        "symbol": segment.get("symbol"), "security_id": segment.get("security_id"),
        "expected_session_count": len(expected),
        "verified_traded_session_count": traded_count,
        "verified_no_trade_count": no_trade_count,
        "record_count": len(row_map), "duplicate_session_count": len(duplicates),
        "exploratory_replay_eligible": eligible,
        "approved_backtest_eligible": False, "production_promotion_allowed": False,
        "status": "exploratory_only" if eligible else "blocked",
        "reasons": reasons, "decision_cutoff": cutoff.isoformat() if cutoff else None,
        "policy": "point_in_time_no_gap_filling_no_lookahead_no_production_promotion",
    }
