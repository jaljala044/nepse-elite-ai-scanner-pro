"""Evidence-gated NEPSE index realized-volatility risk component."""
from __future__ import annotations

from datetime import date, datetime, timezone
import math
from statistics import stdev

MIN_HISTORY_SESSIONS = 271
VOLATILITY_WINDOW = 20
ANNUALIZATION_SESSIONS = 252
DIGEST_LENGTH = 64


def _utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonblank ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _positive(row: dict, key: str, session: str) -> float:
    value = row.get(key)
    if isinstance(value, bool):
        raise ValueError(f"{session}: {key} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{session}: invalid {key}") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{session}: {key} must be finite and positive")
    return number


def _valid_digest(value: object) -> bool:
    digest = str(value or "").lower()
    return len(digest) == DIGEST_LENGTH and all(ch in "0123456789abcdef" for ch in digest)


def nepse_index_volatility_component(
    rows: list[dict],
    *,
    session_dates: list[str],
    decision_time: str,
) -> dict:
    """Calculate 20-session annualized realized volatility and inverse risk rank.

    Requires 271 exact, verified final index sessions: 270 close-to-close
    returns produce 251 rolling 20-session volatility observations. The latest
    observation is ranked against the preceding 250 observations. Lower
    relative volatility yields a higher stability score; this is not a
    directional forecast or a claim that low volatility predicts returns.
    """
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("rows must be a list of objects")
    if not isinstance(session_dates, list):
        raise ValueError("session_dates must be a list")
    cutoff = _utc(decision_time, "decision_time")

    dates = []
    for value in session_dates:
        try:
            parsed = date.fromisoformat(str(value)).isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError("session_dates must contain ISO calendar dates") from exc
        if parsed != value:
            raise ValueError("session_dates must use YYYY-MM-DD")
        dates.append(parsed)
    if not dates or dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("session_dates must be nonempty, unique and ascending")
    if len(dates) < MIN_HISTORY_SESSIONS:
        return {
            "status": "insufficient_evidence",
            "reason": "index_volatility_history_below_271_sessions",
            "score": None,
            "history_sessions": len(dates),
            "required_sessions": MIN_HISTORY_SESSIONS,
            "as_of_session": dates[-1] if dates else None,
        }

    required = dates[-MIN_HISTORY_SESSIONS:]
    required_set = set(required)
    admitted = {}
    rejected = []
    source_ids = set()
    for row in rows:
        if row.get("record_type") != "index_ohlcv" or str(row.get("index_code", "")).upper() != "NEPSE":
            continue
        session = str(row.get("session_date", ""))
        if session not in required_set:
            continue
        if row.get("source_validation_status") != "verified" or row.get("finality_status") != "final":
            rejected.append({"session_date": session, "reason": "index_row_not_verified_final"})
            continue
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip() or not _valid_digest(row.get("source_payload_sha256")):
            rejected.append({"session_date": session, "reason": "invalid_source_provenance"})
            continue
        try:
            available_at = _utc(row.get("available_at"), "available_at")
            opening = _positive(row, "open", session)
            high = _positive(row, "high", session)
            low = _positive(row, "low", session)
            close = _positive(row, "close", session)
        except ValueError as exc:
            rejected.append({"session_date": session, "reason": str(exc)})
            continue
        if available_at > cutoff:
            rejected.append({"session_date": session, "reason": "future_available_at"})
            continue
        if low > min(opening, close) or high < max(opening, close) or high < low:
            rejected.append({"session_date": session, "reason": "invalid_ohlc_range"})
            continue
        if session in admitted:
            raise ValueError(f"duplicate NEPSE index session: {session}")
        source_ids.add(source_id.strip())
        admitted[session] = {
            "close": close,
            "source_id": source_id.strip(),
            "source_payload_sha256": str(row["source_payload_sha256"]).lower(),
        }

    missing = [session for session in required if session not in admitted]
    if rejected or missing:
        return {
            "status": "insufficient_evidence",
            "reason": "unverified_or_missing_exact_index_volatility_sessions",
            "score": None,
            "as_of_session": required[-1],
            "history_sessions": len(admitted),
            "required_sessions": MIN_HISTORY_SESSIONS,
            "missing_sessions": missing,
            "rejected_rows": rejected,
        }
    if len(source_ids) != 1:
        return {
            "status": "insufficient_evidence",
            "reason": "index_volatility_source_changed_within_window",
            "score": None,
            "as_of_session": required[-1],
            "source_ids": sorted(source_ids),
        }

    closes = [admitted[session]["close"] for session in required]
    returns = [math.log(closes[index] / closes[index - 1]) for index in range(1, len(closes))]
    rolling = [
        stdev(returns[index - VOLATILITY_WINDOW:index]) * math.sqrt(ANNUALIZATION_SESSIONS) * 100
        for index in range(VOLATILITY_WINDOW, len(returns) + 1)
    ]
    current = rolling[-1]
    history = rolling[:-1]
    less = sum(value < current for value in history)
    equal = sum(value == current for value in history)
    percentile = (less + 0.5 * equal) / len(history) * 100
    score = 100.0 - percentile
    warnings = []
    if percentile >= 90:
        warnings.append("realized_volatility_in_top_decile_of_rolling_history")
    elif percentile <= 10:
        warnings.append("realized_volatility_in_bottom_decile_compression_watch_for_regime_expansion")

    latest = admitted[required[-1]]
    return {
        "status": "verified",
        "score": round(score, 2),
        "as_of_session": required[-1],
        "source_id": latest["source_id"],
        "source_payload_sha256": latest["source_payload_sha256"],
        "history_sessions": len(required),
        "metrics": {
            "realized_volatility_20_session_annualized_pct": round(current, 4),
            "historical_volatility_percentile": round(percentile, 2),
            "historical_observations": len(history),
            "return_observations": len(returns),
            "volatility_window_sessions": VOLATILITY_WINDOW,
            "annualization_sessions": ANNUALIZATION_SESSIONS,
        },
        "warnings": warnings,
        "interpretation": "inverse_historical_realized_volatility_rank_stability_descriptor_not_a_probability",
        "limitations": [
            "Requires 271 exact verified final NEPSE index sessions and one consistent source",
            "Annualization assumes 252 trading sessions per year",
            "Score ranks current 20-session realized volatility against prior rolling observations",
            "Low volatility is not a directional bullish signal and may precede expansion",
            "Synthetic tests validate calculations only; no live volatility score is claimed",
        ],
    }
