"""Evidence-gated NEPSE market turnover participation component."""
from __future__ import annotations

from datetime import date, datetime, timezone
import math
from statistics import median

MIN_HISTORY_SESSIONS = 21
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


def _positive(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return number


def _valid_digest(value: object) -> bool:
    digest = str(value or "").lower()
    return len(digest) == DIGEST_LENGTH and all(ch in "0123456789abcdef" for ch in digest)


def _bounded_interpolation(value: float, points: tuple[tuple[float, float], ...]) -> float:
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            return y0 + (value - x0) * (y1 - y0) / (x1 - x0)
    raise AssertionError("interpolation range was not covered")


def nepse_market_turnover_component(
    rows: list[dict],
    *,
    session_dates: list[str],
    decision_time: str,
) -> dict:
    """Score turnover participation from 21 exact verified NEPSE sessions.

    The score rewards sustained participation versus a trailing 20-session
    median and change in the recent 5-session average versus the prior 5.
    It is not directional: price trend and breadth must independently confirm
    whether turnover expansion represents accumulation or distribution.
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
            "reason": "market_turnover_history_below_21_sessions",
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
        if row.get("record_type") != "market_summary" or str(row.get("market_code", "")).upper() != "NEPSE":
            continue
        session = str(row.get("session_date", ""))
        if session not in required_set:
            continue
        if row.get("source_validation_status") != "verified" or row.get("finality_status") != "final":
            rejected.append({"session_date": session, "reason": "market_summary_not_verified_final"})
            continue
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip() or not _valid_digest(row.get("source_payload_sha256")):
            rejected.append({"session_date": session, "reason": "invalid_source_provenance"})
            continue
        try:
            available_at = _utc(row.get("available_at"), "available_at")
            turnover = _positive(row.get("total_turnover"), "total_turnover")
        except ValueError as exc:
            rejected.append({"session_date": session, "reason": str(exc)})
            continue
        if available_at > cutoff:
            rejected.append({"session_date": session, "reason": "future_available_at"})
            continue
        if session in admitted:
            raise ValueError(f"duplicate NEPSE market summary session: {session}")
        source_ids.add(source_id.strip())
        admitted[session] = {
            "total_turnover": turnover,
            "source_id": source_id.strip(),
            "source_payload_sha256": str(row["source_payload_sha256"]).lower(),
        }

    missing = [session for session in required if session not in admitted]
    if rejected or missing:
        return {
            "status": "insufficient_evidence",
            "reason": "unverified_or_missing_exact_market_turnover_sessions",
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
            "reason": "market_turnover_source_changed_within_window",
            "score": None,
            "as_of_session": required[-1],
            "source_ids": sorted(source_ids),
        }

    values = [admitted[session]["total_turnover"] for session in required]
    baseline_median = median(values[:-1])
    recent_five_average = sum(values[-5:]) / 5
    prior_five_average = sum(values[-10:-5]) / 5
    latest = values[-1]
    activity_ratio = latest / baseline_median
    trend_ratio = recent_five_average / prior_five_average

    activity_score = _bounded_interpolation(
        activity_ratio,
        ((0.0, 0.0), (0.5, 20.0), (0.8, 45.0), (1.0, 60.0),
         (1.5, 90.0), (2.0, 100.0)),
    )
    trend_score = max(0.0, min(100.0, 50.0 + 50.0 * (trend_ratio - 1.0)))
    score = 0.65 * activity_score + 0.35 * trend_score
    latest_record = admitted[required[-1]]
    warnings = []
    if activity_ratio >= 2.0:
        warnings.append("single_session_turnover_at_least_2x_trailing_median_review_for_climax_or_event_effect")
    if trend_ratio < 0.75:
        warnings.append("recent_five_session_turnover_contracting")
    if trend_ratio >= 1.5:
        warnings.append("recent_five_session_turnover_expanding_sharply_confirm_with_breadth_and_price")

    return {
        "status": "verified",
        "score": round(score, 2),
        "as_of_session": required[-1],
        "source_id": latest_record["source_id"],
        "source_payload_sha256": latest_record["source_payload_sha256"],
        "history_sessions": len(required),
        "metrics": {
            "latest_turnover": round(latest, 2),
            "trailing_20_session_median": round(baseline_median, 2),
            "latest_vs_trailing_median_ratio": round(activity_ratio, 4),
            "recent_5_session_average": round(recent_five_average, 2),
            "prior_5_session_average": round(prior_five_average, 2),
            "recent_vs_prior_5_session_ratio": round(trend_ratio, 4),
            "activity_score": round(activity_score, 2),
            "trend_score": round(trend_score, 2),
        },
        "warnings": warnings,
        "interpretation": "rules_based_turnover_participation_not_directional_and_not_a_probability",
        "limitations": [
            "Requires 21 exact verified final NEPSE market-summary sessions",
            "All sessions in the window must use one source identifier",
            "No missing sessions, stale values or future-available records are imputed",
            "High turnover can accompany distribution; cross-check price trend, breadth and broker evidence",
            "Synthetic tests validate logic only; this component is not a trading signal",
        ],
    }
