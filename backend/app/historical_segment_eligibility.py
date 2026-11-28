"""Fail-closed eligibility evaluation for a single historical instrument segment.

This evaluator is a gate/reporting primitive only. It never repairs, fills,
adjusts, or joins OHLCV across security identities or lifecycle boundaries.
"""
from __future__ import annotations

import base64
import hashlib
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from .issue5_quarantine import Quarantine

ARCHIVE_FIELDS = frozenset({"repository", "commit_sha", "source_file", "source_file_sha256", "target_csv_row", "target_date"})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_SESSION_STATES = {
    "traded", "no_trade_verified", "closed_verified",
    "suspended_verified", "unknown",
}
_ALLOWED_RIGHTS = {"approved"}
_ALLOWED_ADJUSTMENT_BASES = {"raw", "verified_adjusted"}


def _iso_date(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must use canonical YYYY-MM-DD")
    return parsed


def _aware_datetime(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _decimal(value):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _valid_ohlcv(row):
    values = {key: _decimal(row.get(key)) for key in ("open", "high", "low", "close", "volume")}
    if any(value is None for value in values.values()):
        return False
    if any(values[key] <= 0 for key in ("open", "high", "low", "close")):
        return False
    # NEPSE traded quantity is expressed in whole shares; fractional quantity
    # is rejected until an explicitly versioned unit rule says otherwise.
    if values["volume"] <= 0 or values["volume"] != values["volume"].to_integral_value():
        return False
    return (values["high"] >= max(values["open"], values["close"], values["low"])
            and values["low"] <= min(values["open"], values["close"], values["high"]))


def _valid_primary_evidence(evidence, cutoff):
    """Validate provenance metadata and recompute the digest from retained raw bytes."""
    if not isinstance(evidence, dict):
        return False
    required_text = ("source_id", "source_record_ref")
    if any(not isinstance(evidence.get(key), str) or not evidence[key].strip()
           for key in required_text):
        return False
    try:
        parsed = urlsplit(evidence.get("source_url", ""))
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or host not in {
            "nepalstock.com", "www.nepalstock.com",
            "nepalstock.com.np", "www.nepalstock.com.np",
        }:
            return False
    except ValueError:
        return False
    digest = str(evidence.get("evidence_sha256") or "").lower()
    payload_digest = str(evidence.get("payload_sha256") or "").lower()
    payload_base64 = evidence.get("payload_base64")
    if not isinstance(payload_base64, str) or not payload_base64:
        return False
    try:
        payload = base64.b64decode(payload_base64, validate=True)
    except (ValueError, TypeError):
        return False
    if base64.b64encode(payload).decode("ascii") != payload_base64:
        return False
    computed_digest = hashlib.sha256(payload).hexdigest()
    if (not _SHA256.fullmatch(digest) or digest != payload_digest
            or digest != computed_digest):
        return False
    if evidence.get("rights_status") != "approved":
        return False
    try:
        available = _aware_datetime(evidence.get("available_at"), "available_at")
        retrieved = _aware_datetime(evidence.get("retrieved_at"), "retrieved_at")
    except ValueError:
        return False
    return available <= cutoff and retrieved >= available


def evaluate_historical_segment(*, segment, expected_sessions, session_statuses,
                                session_evidence=None, records, required_sessions=120,
                                available_warmup_sessions=0, decision_cutoff, archive_guard=None, require_archive_guard=False):
    """Evaluate a point-in-time segment without imputing missing or inactive dates.

    expected_sessions must be a verified exchange-session list, not weekdays
    generated from a schedule. session_statuses must explicitly classify each
    date, and session_evidence must provide a point-in-time, rights-approved,
    hash-addressed source record for every expected date. A verified no-trade
    session is distinct from a missing bar, a closed exchange date, suspension,
    and unknown status. Synthetic fixtures test the contract; they do not
    establish real NEPSE calendar evidence.
    """
    if not isinstance(segment, dict):
        raise ValueError("segment must be a mapping")
    if not isinstance(session_statuses, dict):
        raise ValueError("session_statuses must be a date-to-status mapping")
    if session_evidence is None:
        session_evidence = {}
    if not isinstance(session_evidence, dict):
        raise ValueError("session_evidence must be a date-to-provenance mapping")
    if not isinstance(expected_sessions, (list, tuple)):
        raise ValueError("expected_sessions must be a verified date list")
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    if not isinstance(required_sessions, int) or isinstance(required_sessions, bool) or required_sessions < 1:
        raise ValueError("required_sessions must be a positive integer")
    if not isinstance(available_warmup_sessions, int) or isinstance(available_warmup_sessions, bool) or available_warmup_sessions < 0:
        raise ValueError("available_warmup_sessions must be a non-negative integer")

    cutoff = _aware_datetime(decision_cutoff, "decision_cutoff")
    reasons = []
    expected = []
    for raw_day in expected_sessions:
        expected.append(_iso_date(raw_day, "expected session"))
    if len(expected) != len(set(expected)):
        reasons.append("duplicate_expected_session")
    expected = sorted(set(expected))
    if not expected:
        reasons.append("verified_expected_sessions_required")

    symbol = segment.get("symbol")
    security_id = segment.get("security_id")
    if not isinstance(symbol, str) or not symbol or symbol != symbol.strip().upper():
        reasons.append("segment_symbol_invalid")
    if not isinstance(security_id, str) or not security_id.strip():
        reasons.append("segment_security_id_missing")
    if segment.get("identity_verified") is not True:
        reasons.append("instrument_identity_not_verified")
    if not _valid_primary_evidence(segment.get("identity_evidence"), cutoff):
        reasons.append("instrument_identity_source_evidence_unverified")
    if segment.get("boundary_reviewed") is not True:
        reasons.append("lifecycle_boundary_not_reviewed")
    if not _valid_primary_evidence(segment.get("lifecycle_evidence"), cutoff):
        reasons.append("lifecycle_source_evidence_unverified")
    if segment.get("suspension_overlap") is not False:
        reasons.append("suspension_overlap_or_unknown")
    if segment.get("merger_or_successor_boundary") is not False:
        reasons.append("merger_or_successor_boundary_unknown_or_crossed")

    try:
        effective_from = _iso_date(segment.get("effective_from"), "effective_from")
    except ValueError:
        effective_from = None
        reasons.append("effective_from_unverified")
    effective_to = None
    if segment.get("effective_to") is not None:
        try:
            effective_to = _iso_date(segment.get("effective_to"), "effective_to")
        except ValueError:
            reasons.append("effective_to_invalid")
    if effective_from and effective_to and effective_to < effective_from:
        reasons.append("invalid_effective_interval")

    identity_evidence = segment.get("identity_evidence")
    identity_claims = identity_evidence.get("claims") if isinstance(identity_evidence, dict) else None
    if not isinstance(identity_claims, dict) or any(
        identity_claims.get(key) != expected
        for key, expected in (("symbol", symbol), ("security_id", security_id))
    ):
        reasons.append("instrument_identity_claims_mismatch")

    lifecycle_evidence = segment.get("lifecycle_evidence")
    lifecycle_claims = lifecycle_evidence.get("claims") if isinstance(lifecycle_evidence, dict) else None
    expected_lifecycle_claims = {
        "symbol": symbol,
        "security_id": security_id,
        "effective_from": segment.get("effective_from"),
        "effective_to": segment.get("effective_to"),
        "boundary_reviewed": True,
        "suspension_overlap": False,
        "merger_or_successor_boundary": False,
    }
    if not isinstance(lifecycle_claims, dict) or any(
        lifecycle_claims.get(key) != expected
        for key, expected in expected_lifecycle_claims.items()
    ):
        reasons.append("lifecycle_claims_mismatch")

    adjustment_basis = segment.get("adjustment_basis")
    if adjustment_basis not in _ALLOWED_ADJUSTMENT_BASES:
        reasons.append("adjustment_basis_unverified")
    if adjustment_basis == "verified_adjusted":
        adjustment_evidence = segment.get("adjustment_evidence")
        adjustment_valid = _valid_primary_evidence(adjustment_evidence, cutoff)
        if adjustment_valid:
            factor_version = adjustment_evidence.get("factor_version")
            factor = _decimal(adjustment_evidence.get("factor"))
            effective_date_value = adjustment_evidence.get("effective_date")
            claims = adjustment_evidence.get("claims")
            try:
                factor_effective_date = _iso_date(
                    effective_date_value, "adjustment effective_date"
                )
            except ValueError:
                factor_effective_date = None
            expected_adjustment_claims = {
                "factor": str(factor),
                "factor_version": factor_version,
                "effective_date": effective_date_value,
            }
            adjustment_valid = (
                isinstance(factor_version, str)
                and bool(factor_version.strip())
                and factor is not None
                and factor > 0
                and factor_effective_date is not None
                and factor_effective_date <= cutoff.date()
                and isinstance(claims, dict)
                and all(claims.get(key) == value
                        for key, value in expected_adjustment_claims.items())
            )
        if not adjustment_valid:
            reasons.append("adjustment_factor_evidence_unverified")
    minimum_warmup = segment.get("minimum_warmup_sessions", 0)
    if not isinstance(minimum_warmup, int) or isinstance(minimum_warmup, bool) or minimum_warmup < 0:
        reasons.append("minimum_warmup_sessions_invalid")
        minimum_warmup = 0
    if available_warmup_sessions < minimum_warmup:
        reasons.append("insufficient_causal_warmup")

    normalized_statuses = {}
    for raw_day, state in session_statuses.items():
        try:
            day = _iso_date(raw_day, "session status date")
        except ValueError:
            reasons.append("invalid_session_status_date")
            continue
        if day in normalized_statuses:
            reasons.append(f"duplicate_session_status:{day.isoformat()}")
        normalized_statuses[day] = state

    normalized_evidence = {}
    for raw_day, evidence in session_evidence.items():
        try:
            day = _iso_date(raw_day, "session evidence date")
        except ValueError:
            reasons.append("invalid_session_evidence_date")
            continue
        if day in normalized_evidence:
            reasons.append(f"duplicate_session_evidence:{day.isoformat()}")
        normalized_evidence[day] = evidence

    expected_set = set(expected)
    for extra_day in sorted(set(normalized_statuses) - expected_set):
        reasons.append(f"unexpected_session_status:{extra_day.isoformat()}")
    for extra_day in sorted(set(normalized_evidence) - expected_set):
        reasons.append(f"unexpected_session_evidence:{extra_day.isoformat()}")
    for day in expected:
        if ((effective_from is not None and day < effective_from)
                or (effective_to is not None and day > effective_to)):
            reasons.append(f"expected_session_outside_instrument_effective_interval:{day.isoformat()}")

    by_day = {}
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            reasons.append(f"invalid_record:{index}")
            continue
        try:
            day = _iso_date(row.get("session_date"), "record session_date")
        except ValueError:
            reasons.append(f"invalid_record_session_date:{index}")
            continue
        if day not in expected:
            reasons.append(f"unexpected_bar:{day.isoformat()}")
        if require_archive_guard or archive_guard is not None or ARCHIVE_FIELDS.intersection(row):
            if not isinstance(archive_guard, Quarantine):
                reasons.append(f"archive_quarantine_guard_missing:{day.isoformat()}")
            elif row.get("target_date") != day.isoformat():
                reasons.append(f"archive_quarantine_date_binding_missing_or_mismatch:{day.isoformat()}")
            else:
                disposition = archive_guard.disposition(row)
                if disposition != "not_in_overlay_requires_other_gates":
                    reasons.append(f"archive_quarantine:{disposition}:{day.isoformat()}")
        by_day.setdefault(day, []).append(row)

    verified_traded = 0
    valid_candles = 0
    eligible_candles = 0
    verified_no_trade = 0
    verified_closed = 0
    verified_suspended = 0
    unknown = 0

    for day in expected:
        day_text = day.isoformat()
        state = normalized_statuses.get(day)
        rows = by_day.get(day, [])
        if state not in _ALLOWED_SESSION_STATES:
            reasons.append(f"session_status_unverified:{day_text}")
            unknown += 1
            continue
        evidence = normalized_evidence.get(day)
        evidence_valid = isinstance(evidence, dict)
        if not evidence_valid:
            reasons.append(f"session_evidence_missing:{day_text}")
        else:
            if evidence.get("status") != state:
                reasons.append(f"session_evidence_status_mismatch:{day_text}")
                evidence_valid = False
            if not _valid_primary_evidence(evidence, cutoff):
                evidence_valid = False
                try:
                    if _aware_datetime(evidence.get("available_at"), "session evidence available_at") > cutoff:
                        reasons.append(f"session_evidence_lookahead:{day_text}")
                except ValueError:
                    pass
            if not evidence_valid:
                reasons.append(f"session_evidence_unverified:{day_text}")
        if not evidence_valid:
            # Evaluate row-level rights independently; missing calendar evidence
            # must not hide a known rights violation in the associated candle.
            for row in rows:
                if row.get("rights_status") not in _ALLOWED_RIGHTS:
                    reasons.append(f"source_rights_not_approved:{day_text}")
            unknown += 1
            continue
        if state == "unknown":
            reasons.append(f"session_status_unverified:{day_text}")
            unknown += 1
            if rows:
                reasons.append(f"bar_on_unknown_session:{day_text}")
            continue
        if state == "closed_verified":
            verified_closed += 1
            reasons.append(f"closed_session_in_expected_sessions:{day_text}")
            if rows:
                reasons.append(f"bar_on_closed_session:{day_text}")
            continue
        if state == "suspended_verified":
            verified_suspended += 1
            reasons.append(f"suspended_session_in_segment:{day_text}")
            if rows:
                reasons.append(f"bar_on_suspended_session:{day_text}")
            continue
        if state == "no_trade_verified":
            verified_no_trade += 1
            if rows:
                reasons.append(f"bar_present_on_verified_no_trade_session:{day_text}")
            continue

        verified_traded += 1
        if not rows:
            reasons.append(f"missing_bar:{day_text}")
            continue
        if len(rows) > 1:
            reasons.append(f"duplicate_bar:{day_text}")
            continue
        row = rows[0]
        candle_reason_start = len(reasons)
        if _valid_ohlcv(row):
            valid_candles += 1
        if row.get("symbol") != symbol or row.get("security_id") != security_id:
            reasons.append(f"bar_identity_mismatch:{day_text}")
        if effective_from and day < effective_from or effective_to and day > effective_to:
            reasons.append(f"session_outside_instrument_effective_interval:{day_text}")
        if not _valid_ohlcv(row):
            reasons.append(f"invalid_ohlcv:{day_text}")
        if row.get("adjustment_basis") != adjustment_basis:
            reasons.append(f"adjustment_basis_mismatch:{day_text}")
        if row.get("rights_status") not in _ALLOWED_RIGHTS:
            reasons.append(f"source_rights_not_approved:{day_text}")
        source_evidence = row.get("source_evidence")
        if not _valid_primary_evidence(source_evidence, cutoff):
            reasons.append(f"bar_source_evidence_unverified:{day_text}")
        try:
            row_available_at = _aware_datetime(row.get("available_at"), "bar available_at")
            if row_available_at > cutoff:
                reasons.append(f"lookahead_available_after_cutoff:{day_text}")
            if isinstance(source_evidence, dict):
                source_available_at = _aware_datetime(
                    source_evidence.get("available_at"), "source evidence available_at"
                )
                if row_available_at != source_available_at:
                    reasons.append(f"bar_available_at_source_mismatch:{day_text}")
        except ValueError:
            reasons.append(f"available_at_unverified:{day_text}")
        digest = str(row.get("evidence_sha256") or "").lower()
        source_evidence = row.get("source_evidence")
        source_digest = (
            str(source_evidence.get("evidence_sha256") or "").lower()
            if isinstance(source_evidence, dict) else ""
        )
        payload_digest = (
            str(source_evidence.get("payload_sha256") or "").lower()
            if isinstance(source_evidence, dict) else ""
        )
        if not _SHA256.fullmatch(digest):
            reasons.append(f"evidence_hash_missing_or_invalid:{day_text}")
        elif digest != source_digest or digest != payload_digest:
            reasons.append(f"evidence_hash_binding_mismatch:{day_text}")

        if len(reasons) == candle_reason_start and day <= cutoff.date():
            eligible_candles += 1
        elif day > cutoff.date():
            reasons.append(f"future_session:{day.isoformat()}")

    if eligible_candles < required_sessions:
        reasons.append("insufficient_traded_sessions")

    reasons = sorted(set(reasons))
    eligible = not reasons
    return {
        "symbol": symbol,
        "security_id": security_id,
        "expected_session_count": len(expected),
        "verified_traded_session_count": verified_traded,
        "valid_ohlcv_candle_count": valid_candles,
        "eligible_ohlcv_candle_count": eligible_candles,
        "verified_no_trade_count": verified_no_trade,
        "verified_closed_session_count": verified_closed,
        "verified_suspended_session_count": verified_suspended,
        "unknown_session_count": unknown,
        "required_traded_sessions": required_sessions,
        "available_warmup_sessions": available_warmup_sessions,
        "minimum_warmup_sessions": minimum_warmup,
        "exploratory_replay_eligible": eligible,
        "approved_backtest_eligible": False,
        "production_promotion_allowed": False,
        "reasons": reasons,
        "policy": "verified_sessions_only_no_imputation_no_cross_identity_splice_no_ohlcv_adjustment",
    }


def evaluate_archive_historical_segment(*, archive_guard=None, **kwargs):
    """Archive entry point: absence of the quarantine guard always fails closed."""
    kwargs.setdefault("session_evidence", {})
    return evaluate_historical_segment(
        archive_guard=archive_guard, require_archive_guard=True, **kwargs
    )
