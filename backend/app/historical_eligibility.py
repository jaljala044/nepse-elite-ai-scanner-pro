"""Lifecycle-aware, fail-closed historical segment eligibility manifest.

This module classifies supplied observations against an explicitly verified
session calendar and effective-dated instrument lifecycle. It never fills,
repairs, splices, or promotes OHLCV. A passing manifest is a review gate, not
independent approval for production backtests.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OHLCV = ("open", "high", "low", "close", "volume")


def _day(value: Any, field: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_iso_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field}_must_be_iso_date") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{field}_must_be_iso_date")
    return parsed


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"invalid_{field}") from None
    if not result.is_finite():
        raise ValueError(f"non_finite_{field}")
    return result


def _lifecycle_state(day: date, lifecycle: dict) -> str:
    listing = _day(lifecycle["listing_date"], "listing_date")
    delisting = (_day(lifecycle["delisting_date"], "delisting_date")
                 if lifecycle.get("delisting_date") else None)
    if day < listing:
        return "not_listed"
    if delisting and day >= delisting:
        return "delisted"
    for period in lifecycle.get("suspensions", []):
        start = _day(period["start"], "suspension_start")
        end = _day(period["end"], "suspension_end")
        if end < start:
            raise ValueError("invalid_suspension_range")
        if start <= day <= end:
            return "suspended"
    merger = lifecycle.get("merger_effective_date")
    if merger and day >= _day(merger, "merger_effective_date"):
        return "merger_boundary"
    return "active"


def build_lifecycle_eligibility_manifest(
    records: list[dict],
    *,
    symbol: str,
    verified_sessions: list[str],
    lifecycle: dict,
    required_warmup_sessions: int,
    verified_closed_dates: list[str] | None = None,
    minimum_sessions: int = 120,
    available_as_of: str,
) -> dict:
    """Classify one instrument's verified-session history without imputations.

    Each session must have exactly one explicit record with status 'traded' or
    'no_trade', unless lifecycle proves it was not listed, suspended, delisted,
    or beyond a merger boundary. Missing observations remain missing. Trade rows
    require complete raw OHLCV, one adjustment basis, rights and evidence hashes.
    """
    if not isinstance(symbol, str) or not symbol.strip() or symbol != symbol.strip():
        raise ValueError("invalid_symbol")
    if type(required_warmup_sessions) is not int or required_warmup_sessions < 0:
        raise ValueError("invalid_required_warmup_sessions")
    if type(minimum_sessions) is not int or minimum_sessions < 1:
        raise ValueError("invalid_minimum_sessions")
    cutoff = datetime.fromisoformat(available_as_of.replace("Z", "+00:00"))
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("available_as_of_must_be_timezone_aware")

    sessions = [_day(item, "verified_session") for item in verified_sessions]
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError("verified_sessions_must_be_unique_and_chronological")
    closed_sessions = [_day(item, "verified_closed_date")
                       for item in (verified_closed_dates or [])]
    if closed_sessions != sorted(set(closed_sessions)):
        raise ValueError("verified_closed_dates_must_be_unique_and_chronological")
    if set(sessions) & set(closed_sessions):
        raise ValueError("open_and_closed_calendar_dates_overlap")
    by_day: dict[date, list[dict]] = defaultdict(list)
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise ValueError(f"invalid_record_{index}")
        day = _day(row.get("session_date"), "session_date")
        by_day[day].append(row)

    open_set, closed_set = set(sessions), set(closed_sessions)
    closed_observation_dates = sorted(day.isoformat() for day in by_day if day in closed_set)
    unknown_calendar_dates = sorted(
        day.isoformat() for day in by_day if day not in open_set and day not in closed_set
    )
    rows = []
    adjustment_bases = set()
    data_hashes = set()
    classified_active = 0
    traded_count = 0
    no_trade_count = 0
    blockers = []

    for day in sessions:
        day_text = day.isoformat()
        state = _lifecycle_state(day, lifecycle)
        observations = by_day.get(day, [])
        reasons = []
        status = state
        if state in {"not_listed", "suspended", "delisted", "merger_boundary"}:
            if observations:
                reasons.append("observation_conflicts_with_lifecycle")
                status = "lifecycle_conflict"
        elif len(observations) == 0:
            status = "missing"
            reasons.append("expected_session_has_no_classified_observation")
        elif len(observations) > 1:
            status = "duplicate"
            reasons.append("multiple_rows_for_instrument_session")
        else:
            row = observations[0]
            declared_status = row.get("observation_status")
            if declared_status == "no_trade":
                status = "no_trade"
                no_trade_count += 1
                if row.get("ohlcv") not in (None, {}, ""):
                    reasons.append("no_trade_must_not_contain_imputed_ohlcv")
                    status = "invalid_no_trade_record"
                if not row.get("evidence_id") or not _sha256(row.get("source_sha256")):
                    reasons.append("no_trade_evidence_or_source_hash_missing")
                else:
                    data_hashes.add(row["source_sha256"])
                try:
                    available = datetime.fromisoformat(str(row.get("available_at", "")).replace("Z", "+00:00"))
                    if available.tzinfo is None or available.utcoffset() is None:
                        raise ValueError
                    if available > cutoff:
                        reasons.append("lookahead_available_after_cutoff")
                except ValueError:
                    reasons.append("available_at_missing_or_invalid")
            elif declared_status == "traded":
                status = "traded"
                values = row.get("ohlcv")
                if not isinstance(values, dict) or set(values) != set(_OHLCV):
                    reasons.append("incomplete_or_noncanonical_ohlcv_fields")
                else:
                    try:
                        o, h, l, c, v = (_decimal(values[k], k) for k in _OHLCV)
                        if min(o, h, l, c) <= 0 or v < 0 or v != v.to_integral_value():
                            reasons.append("ohlcv_domain_violation")
                        if h < max(o, l, c) or l > min(o, h, c):
                            reasons.append("invalid_ohlc_geometry")
                    except ValueError as exc:
                        reasons.append(str(exc))
                basis = row.get("adjustment_basis")
                if basis not in {"raw_unadjusted", "split_adjusted", "total_return_adjusted"}:
                    reasons.append("unknown_adjustment_basis")
                else:
                    adjustment_bases.add(basis)
                if row.get("rights_status") != "approved":
                    reasons.append("source_rights_not_approved")
                if not _sha256(row.get("source_sha256")) or not row.get("evidence_id"):
                    reasons.append("source_evidence_hash_or_id_missing")
                else:
                    data_hashes.add(row["source_sha256"])
                try:
                    available = datetime.fromisoformat(str(row.get("available_at", "")).replace("Z", "+00:00"))
                    if available.tzinfo is None or available.utcoffset() is None:
                        raise ValueError
                    if available > cutoff:
                        reasons.append("lookahead_available_after_cutoff")
                except ValueError:
                    reasons.append("available_at_missing_or_invalid")
                if not reasons:
                    traded_count += 1
            else:
                status = "unknown"
                reasons.append("observation_status_not_explicit")
        if state == "active" and status in {"traded", "no_trade"} and not reasons:
            classified_active += 1
        if reasons:
            blockers.extend({"session_date": day_text, "reason": item} for item in reasons)
        rows.append({"session_date": day_text, "lifecycle_state": state,
                     "classification": status, "reasons": reasons})

    if len(sessions) < minimum_sessions:
        blockers.append({"reason": "insufficient_verified_session_count",
                         "observed": len(sessions), "required": minimum_sessions})
    if classified_active < required_warmup_sessions:
        blockers.append({"reason": "insufficient_classified_causal_warmup",
                         "observed": classified_active, "required": required_warmup_sessions})
    if len(adjustment_bases) > 1:
        blockers.append({"reason": "mixed_adjustment_basis_within_segment",
                         "adjustment_bases": sorted(adjustment_bases)})
    if closed_observation_dates:
        blockers.append({"reason": "source_observation_on_verified_closed_date",
                         "dates": closed_observation_dates})
    if unknown_calendar_dates:
        blockers.append({"reason": "source_row_date_not_in_verified_calendar",
                         "dates": unknown_calendar_dates})

    manifest = {
        "schema_version": "1.0",
        "symbol": symbol,
        "segment_start": sessions[0].isoformat(),
        "segment_end": sessions[-1].isoformat(),
        "verified_session_count": len(sessions),
        "verified_closed_date_count": len(closed_sessions),
        "closed_date_observation_conflicts": closed_observation_dates,
        "unknown_calendar_dates": unknown_calendar_dates,
        "classified_active_session_count": classified_active,
        "traded_session_count": traded_count,
        "explicit_no_trade_session_count": no_trade_count,
        "required_warmup_sessions": required_warmup_sessions,
        "minimum_sessions": minimum_sessions,
        "adjustment_bases": sorted(adjustment_bases),
        "source_sha256_set": sorted(data_hashes),
        "rows": rows,
        "blockers": blockers,
        "review_status": "REVIEW_REQUIRED" if blockers else "ELIGIBLE_FOR_INDEPENDENT_REVIEW",
        "exploratory_replay_allowed": not blockers,
        "approved_backtest": False,
        "canonical_promotion_allowed": False,
        "raw_source_modified": False,
        "history_spliced": False,
        "limitations": [
            "Eligibility is scoped to this supplied instrument segment and session calendar.",
            "Lifecycle events and source rights must be independently evidenced.",
            "No OHLCV values are inferred, repaired, forward-filled, or imputed.",
            "A clean manifest is not independent validation or production approval.",
        ],
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return manifest
