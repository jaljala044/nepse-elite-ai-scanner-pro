"""Evidence-gated NEPSE index trend component for market-health scoring.

The adapter calculates a descriptive 0-100 trend score only from exact,
verified, final, point-in-time index sessions. It never upgrades third-party
or provisional records to verified status.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import math

MIN_HISTORY_SESSIONS = 220
DIGEST_LENGTH = 64


def _timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonblank ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _valid_digest(value: object) -> bool:
    digest = str(value or "").lower()
    return len(digest) == DIGEST_LENGTH and all(
        character in "0123456789abcdef" for character in digest
    )


def _number(row: dict, key: str, session: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{session}: invalid {key}") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{session}: {key} must be finite and positive")
    return value


def nepse_index_trend_component(
    rows: list[dict],
    *,
    session_dates: list[str],
    decision_time: str,
) -> dict:
    """Return the market-health trend component; insufficient data => null score.

    session_dates must be the independently verified, ordered NEPSE exchange
    sessions for the requested window. At least 220 consecutive supplied
    sessions are required: 200-day averages plus a 20-session slope comparison.
    """
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("rows must be a list of objects")
    if not isinstance(session_dates, list):
        raise ValueError("session_dates must be a list")
    cutoff = _timestamp(decision_time, "decision_time")

    dates = []
    for value in session_dates:
        try:
            parsed = date.fromisoformat(str(value)).isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError("session_dates must contain ISO calendar dates") from exc
        if parsed != value:
            raise ValueError("session_dates must use canonical YYYY-MM-DD dates")
        dates.append(parsed)
    if not dates or dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("session_dates must be nonempty, unique and ascending")

    if len(dates) < MIN_HISTORY_SESSIONS:
        return {
            "status": "insufficient_evidence",
            "reason": "index_history_below_220_verified_sessions",
            "score": None,
            "as_of_session": dates[-1] if dates else None,
            "history_sessions": len(dates),
            "required_sessions": MIN_HISTORY_SESSIONS,
            "source_id": None,
            "source_payload_sha256": None,
            "metrics": {},
        }

    required_dates = dates[-MIN_HISTORY_SESSIONS:]
    required_set = set(required_dates)
    admitted = {}
    rejected = []
    for index, row in enumerate(rows):
        if row.get("record_type") != "index_ohlcv" or str(row.get("index_code", "")).upper() != "NEPSE":
            continue
        raw_session = str(row.get("session_date", ""))
        if raw_session not in required_set:
            continue
        if row.get("source_validation_status") != "verified" or row.get("finality_status") != "final":
            rejected.append({"session_date": raw_session, "reason": "index_row_not_verified_final"})
            continue
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip() or not _valid_digest(row.get("source_payload_sha256")):
            rejected.append({"session_date": raw_session, "reason": "invalid_source_provenance"})
            continue
        try:
            available_at = _timestamp(row.get("available_at"), "available_at")
        except ValueError:
            rejected.append({"session_date": raw_session, "reason": "invalid_available_at"})
            continue
        if available_at > cutoff:
            rejected.append({"session_date": raw_session, "reason": "future_available_at"})
            continue
        try:
            opening = _number(row, "open", raw_session)
            high = _number(row, "high", raw_session)
            low = _number(row, "low", raw_session)
            close = _number(row, "close", raw_session)
        except ValueError:
            rejected.append({"session_date": raw_session, "reason": "invalid_ohlc"})
            continue
        if low > min(opening, close) or high < max(opening, close) or high < low:
            rejected.append({"session_date": raw_session, "reason": "invalid_ohlc_range"})
            continue
        if raw_session in admitted:
            raise ValueError(f"duplicate NEPSE index session: {raw_session}")
        admitted[raw_session] = {
            "close": close, "source_id": source_id.strip(),
            "source_payload_sha256": str(row["source_payload_sha256"]).lower(),
        }

    missing = [session for session in required_dates if session not in admitted]
    if rejected or missing:
        return {
            "status": "insufficient_evidence",
            "reason": "unverified_or_missing_exact_index_sessions",
            "score": None,
            "as_of_session": required_dates[-1],
            "history_sessions": len(admitted),
            "required_sessions": MIN_HISTORY_SESSIONS,
            "missing_sessions": missing,
            "rejected_rows": rejected,
            "source_id": None,
            "source_payload_sha256": None,
            "metrics": {},
        }

    closes = [admitted[session]["close"] for session in required_dates]
    current = closes[-1]
    sma20 = sum(closes[-20:]) / 20
    sma50 = sum(closes[-50:]) / 50
    sma200 = sum(closes[-200:]) / 200
    prior_sma200 = sum(closes[-220:-20]) / 200
    return_21 = (current / closes[-22] - 1) * 100
    return_63 = (current / closes[-64] - 1) * 100

    checks = {
        "close_above_sma20": current > sma20,
        "sma20_above_sma50": sma20 > sma50,
        "sma50_above_sma200": sma50 > sma200,
        "sma200_rising_over_20_sessions": sma200 > prior_sma200,
        "positive_21_session_return": return_21 > 0,
        "positive_63_session_return": return_63 > 0,
    }
    weights = {
        "close_above_sma20": 15,
        "sma20_above_sma50": 20,
        "sma50_above_sma200": 25,
        "sma200_rising_over_20_sessions": 20,
        "positive_21_session_return": 10,
        "positive_63_session_return": 10,
    }
    score = sum(weights[name] for name, passed in checks.items() if passed)
    latest = admitted[required_dates[-1]]
    return {
        "status": "verified",
        "reason": None,
        "score": float(score),
        "as_of_session": required_dates[-1],
        "history_sessions": len(required_dates),
        "source_id": latest["source_id"],
        "source_payload_sha256": latest["source_payload_sha256"],
        "metrics": {
            "close": round(current, 4),
            "sma20": round(sma20, 4),
            "sma50": round(sma50, 4),
            "sma200": round(sma200, 4),
            "prior_sma200_20_sessions_ago": round(prior_sma200, 4),
            "return_21_session_pct": round(return_21, 4),
            "return_63_session_pct": round(return_63, 4),
            "checks": checks,
            "check_weights": weights,
        },
        "interpretation": "rules_based_index_trend_strength_not_a_probability",
        "limitations": [
            "Requires an independently verified NEPSE session calendar",
            "Requires verified final exchange index OHLCV with point-in-time availability",
            "No forward-fill, interpolation, third-party auto-promotion or session substitution",
            "The score is a market-health input, not a standalone trading signal",
        ],
    }
