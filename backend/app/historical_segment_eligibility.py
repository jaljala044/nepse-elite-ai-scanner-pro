"""Historical replay admission; never authorizes production or approved backtests."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from app.quarantine_guard import is_quarantined, runtime_quarantine_keys

def _day(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("noncanonical date")
    return value

def _timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("timezone required")
    return result

def evaluate_historical_segment(*, segment, expected_sessions, session_statuses,
                                records, required_sessions, available_warmup_sessions,
                                decision_cutoff, blocked_keys=None):
    reasons = []
    try:
        configured = runtime_quarantine_keys()
        blocked_keys = frozenset(blocked_keys or ()) | (configured or frozenset())
    except ValueError:
        reasons.append("runtime_quarantine_ledger_invalid")
    traded = no_trade = 0
    if segment.get("identity_verified") is not True or not segment.get("security_id") or not segment.get("symbol"):
        reasons.append("instrument_identity_not_verified")
    if segment.get("boundary_reviewed") is not True:
        reasons.append("boundary_not_reviewed")
    for field in ("suspension_overlap", "merger_or_successor_boundary"):
        if segment.get(field) is not False:
            reasons.append(field + "_unknown_or_crossed")
    if not segment.get("adjustment_basis"):
        reasons.append("adjustment_basis_missing")
    try:
        start = _day(segment["effective_from"])
        end = _day(segment["effective_to"]) if segment.get("effective_to") is not None else "9999-12-31"
        cutoff = _timestamp(decision_cutoff)
        sessions = [_day(day) for day in expected_sessions]
        if sessions != sorted(set(sessions)) or not sessions or start > end:
            raise ValueError("invalid session calendar")
        minimum = segment["minimum_warmup_sessions"]
        if any(type(n) is not int or n < 0 for n in (minimum, available_warmup_sessions, required_sessions)) or required_sessions == 0:
            raise ValueError("invalid session requirements")
        if available_warmup_sessions < minimum:
            reasons.append("insufficient_causal_warmup")
    except (ValueError, TypeError, KeyError, AttributeError):
        return {"reasons": reasons + ["invalid_segment_contract"], "verified_traded_session_count":0,
                "verified_no_trade_count":0, "exploratory_replay_eligible":False,
                "approved_backtest_eligible":False, "production_promotion_allowed":False}
    by_day = {}
    for row in records:
        day = row.get("session_date")
        if day not in sessions:
            reasons.append("bar_outside_expected_sessions:" + str(day))
            continue
        if day in by_day:
            reasons.append("duplicate_bar:" + day)
        by_day[day] = row
    for day in sessions:
        if not start <= day <= end:
            reasons.append("session_outside_instrument_effective_interval:" + day)
        status = session_statuses.get(day)
        row = by_day.get(day)
        if status == "no_trade_verified":
            no_trade += 1
            if row is not None:
                reasons.append("bar_present_on_verified_no_trade_session:" + day)
            continue
        if status != "traded":
            reasons.append("session_status_unverified:" + day)
            continue
        if row is None:
            reasons.append("missing_bar:" + day)
            continue
        before = len(reasons)
        if is_quarantined(row) or (str(segment["symbol"]).upper(), day) in (blocked_keys or ()):
            reasons.append("quarantined_bar:" + day)
        if row.get("symbol") != segment.get("symbol") or row.get("security_id") != segment.get("security_id"):
            reasons.append("instrument_mismatch:" + day)
        if row.get("adjustment_basis") != segment.get("adjustment_basis"):
            reasons.append("adjustment_basis_mismatch:" + day)
        if row.get("rights_status") != "approved":
            reasons.append("source_rights_not_approved:" + day)
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(row.get("evidence_sha256", ""))):
            reasons.append("evidence_hash_missing_or_invalid:" + day)
        try:
            if _timestamp(row["available_at"]) > cutoff:
                reasons.append("lookahead_available_after_cutoff:" + day)
        except (ValueError, TypeError, KeyError, AttributeError):
            reasons.append("invalid_availability:" + day)
        try:
            o,h,l,c,v = (Decimal(str(row[k])) for k in ("open","high","low","close","volume"))
            if not all(x.is_finite() for x in (o,h,l,c,v)) or min(o,h,l,c) <= 0 or v <= 0 or h < max(o,l,c) or l > min(o,h,c):
                raise ValueError("invalid OHLCV")
        except (InvalidOperation, ValueError, TypeError, KeyError):
            reasons.append("invalid_ohlcv:" + day)
        if len(reasons) == before:
            traded += 1
    if traded < required_sessions:
        reasons.append("insufficient_traded_sessions")
    return {"reasons": reasons, "verified_traded_session_count": traded,
            "verified_no_trade_count": no_trade, "exploratory_replay_eligible": not reasons,
            "approved_backtest_eligible":False, "production_promotion_allowed":False}


def evaluate_runtime_historical_segment(**kwargs):
    """Runtime replay requires server-pinned ledger, never caller-only evidence."""
    try:
        keys = runtime_quarantine_keys(required=True)
    except ValueError:
        return {"reasons":["runtime_quarantine_ledger_missing_or_invalid"],
                "verified_traded_session_count":0, "verified_no_trade_count":0,
                "exploratory_replay_eligible":False, "approved_backtest_eligible":False,
                "production_promotion_allowed":False}
    kwargs["blocked_keys"] = keys | frozenset(kwargs.get("blocked_keys") or ())
    return evaluate_historical_segment(**kwargs)
