"""Fail-closed, segment-level historical replay eligibility audit.

This is an evidence gate, not a data repairer or backtest approval system.
All dates/sessions and lifecycle facts are caller-supplied verified evidence.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BAR_FIELDS = ("open", "high", "low", "close", "volume")

def _iso_day(value: str, field: str) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO date") from exc

def _available_at(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("available_at must be an ISO timestamp with timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("available_at must include a timezone")
    return parsed

def evaluate_historical_segment(*, segment: dict, expected_sessions: list[str],
                                session_statuses: dict[str, str], records: list[dict],
                                required_sessions: int = 120,
                                available_warmup_sessions: int = 0,
                                decision_cutoff: str) -> dict:
    """Audit a segment; never repairs rows or approves production promotion.

    Every expected date must be labelled traded or no_trade_verified. A traded
    session requires exactly one complete bar; a verified no-trade session none.
    """
    reasons: list[str] = []
    sessions = sorted({_iso_day(x, "expected session") for x in expected_sessions})
    if len(sessions) != len(expected_sessions) or not sessions:
        raise ValueError("expected_sessions must be non-empty and unique")
    if required_sessions < 1 or available_warmup_sessions < 0:
        raise ValueError("session and available warmup counts are invalid")
    cutoff = _available_at(decision_cutoff)
    symbol = str(segment.get("symbol", "")).strip().upper()
    security_id = str(segment.get("security_id", "")).strip()
    start = _iso_day(segment.get("effective_from"), "effective_from")
    end = _iso_day(segment["effective_to"], "effective_to") if segment.get("effective_to") else None
    if not symbol or not security_id:
        reasons.append("stable_instrument_identity_missing")
    if segment.get("identity_verified") is not True:
        reasons.append("instrument_identity_not_verified")
    if end and end < start:
        raise ValueError("effective_to precedes effective_from")
    if segment.get("boundary_reviewed") is not True:
        reasons.append("lifecycle_boundaries_not_reviewed")
    if segment.get("suspension_overlap") is not False:
        reasons.append("suspension_status_unknown_or_overlapping")
    if segment.get("merger_or_successor_boundary") is not False:
        reasons.append("merger_or_successor_boundary_unknown_or_crossed")
    basis = str(segment.get("adjustment_basis", "")).strip()
    if not basis:
        reasons.append("adjustment_basis_missing")
    if len(sessions) < required_sessions:
        reasons.append("insufficient_verified_sessions")
    if set(session_statuses) - set(sessions):
        reasons.append("unexpected_session_status_dates")
    for day in sessions:
        if day < start or (end and day > end):
            reasons.append(f"session_outside_instrument_effective_interval:{day}")
    required_warmup_sessions = int(segment.get("minimum_warmup_sessions", 0))
    if available_warmup_sessions < required_warmup_sessions:
        reasons.append("insufficient_causal_warmup")
    counts: dict[str, list[dict]] = {day: [] for day in sessions}
    for index, row in enumerate(records):
        day = _iso_day(row.get("session_date"), f"record[{index}].session_date")
        if day not in counts:
            reasons.append(f"unexpected_record_date:{day}")
            continue
        counts[day].append(row)
    no_trade_count = 0
    traded_count = 0
    for day in sessions:
        status = session_statuses.get(day)
        rows = counts[day]
        if status not in ("traded", "no_trade_verified"):
            reasons.append(f"session_status_unverified:{day}")
            continue
        if status == "no_trade_verified":
            no_trade_count += 1
            if rows:
                reasons.append(f"bar_present_on_verified_no_trade_session:{day}")
            continue
        traded_count += 1
        if len(rows) != 1:
            reason = "missing_bar" if not rows else "duplicate_bar"
            reasons.append(f"{reason}:{day}")
            continue
        row = rows[0]
        if str(row.get("symbol", "")).strip().upper() != symbol or str(row.get("security_id", "")) != security_id:
            reasons.append(f"instrument_identity_mismatch:{day}")
        if day < start or (end and day > end):
            reasons.append(f"outside_instrument_effective_interval:{day}")
        if row.get("adjustment_basis") != basis:
            reasons.append(f"adjustment_basis_conflict:{day}")
        if row.get("rights_status") != "approved":
            reasons.append(f"source_rights_not_approved:{day}")
        if not _SHA256.fullmatch(str(row.get("evidence_sha256", ""))):
            reasons.append(f"evidence_hash_missing_or_invalid:{day}")
        try:
            if _available_at(row.get("available_at")) > cutoff:
                reasons.append(f"lookahead_available_after_cutoff:{day}")
        except ValueError:
            reasons.append(f"availability_timestamp_invalid:{day}")
        try:
            values = {field: Decimal(str(row[field])) for field in _BAR_FIELDS}
            if any(not value.is_finite() for value in values.values()):
                raise ValueError
            if values["volume"] <= 0 or min(values[k] for k in ("open", "high", "low", "close")) <= 0:
                raise ValueError
            if values["high"] < max(values["open"], values["close"], values["low"]):
                raise ValueError
            if values["low"] > min(values["open"], values["close"], values["high"]):
                raise ValueError
        except (KeyError, TypeError, InvalidOperation, ValueError):
            reasons.append(f"invalid_or_incomplete_ohlcv:{day}")
    if traded_count < required_sessions:
        reasons.append("insufficient_traded_sessions")
    reasons = sorted(set(reasons))
    return {
        "symbol": symbol, "security_id": security_id,
        "segment_start": start, "segment_end": end,
        "verified_session_count": len(sessions), "verified_traded_session_count": traded_count,
        "verified_no_trade_count": no_trade_count,
        "required_session_count": required_sessions,
        "required_warmup_sessions": required_warmup_sessions,
        "available_warmup_sessions": available_warmup_sessions,
        "exploratory_replay_eligible": not reasons,
        "approved_backtest_eligible": False, "production_promotion_allowed": False,
        "reasons": reasons,
        "policy": "fail_closed_no_imputation_no_history_splicing_no_automatic_promotion",
    }
