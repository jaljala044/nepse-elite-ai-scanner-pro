"""Evidence-gated, point-in-time NEPSE market breadth adapter."""
from __future__ import annotations

from datetime import date, datetime, timezone
import math

MIN_HISTORY_SESSIONS = 200
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


def _digest(value: object) -> bool:
    text = str(value or "").lower()
    return len(text) == DIGEST_LENGTH and all(ch in "0123456789abcdef" for ch in text)


def market_breadth_component(
    rows: list[dict],
    *,
    expected_symbols: list[str],
    universe_provenance: dict,
    session_dates: list[str],
    decision_time: str,
    minimum_symbol_coverage: float = 0.80,
) -> dict:
    """Compute breadth only from exact verified final OHLCV sessions.

    expected_symbols must be the point-in-time eligible mature-equity cohort
    supplied by a separately validated universe/lifecycle snapshot. The caller
    supplies a canonical independently verified exchange-session calendar.
    """
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("rows must be a list of objects")
    if not isinstance(expected_symbols, list) or not expected_symbols:
        return {"status": "insufficient_evidence", "reason": "expected_universe_missing", "score": None}
    symbols = [str(item).strip().upper() for item in expected_symbols]
    if any(not item for item in symbols) or len(symbols) != len(set(symbols)):
        raise ValueError("expected_symbols must be unique nonblank symbols")
    if not isinstance(universe_provenance, dict) or (
        universe_provenance.get("status") != "verified"
        or not isinstance(universe_provenance.get("source_id"), str)
        or not universe_provenance["source_id"].strip()
        or not _digest(universe_provenance.get("source_payload_sha256"))
    ):
        return {"status": "insufficient_evidence", "reason": "universe_provenance_unverified", "score": None}

    cutoff = _utc(decision_time, "decision_time")
    if not isinstance(session_dates, list):
        raise ValueError("session_dates must be a list")
    calendar = []
    for item in session_dates:
        try:
            parsed = date.fromisoformat(str(item)).isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError("session_dates must contain ISO calendar dates") from exc
        if parsed != item:
            raise ValueError("session_dates must use YYYY-MM-DD")
        calendar.append(parsed)
    if len(calendar) != len(set(calendar)) or calendar != sorted(calendar):
        raise ValueError("session_dates must be unique and ascending")
    if len(calendar) < MIN_HISTORY_SESSIONS:
        return {"status": "insufficient_evidence", "reason": "canonical_calendar_below_200_sessions",
                "score": None, "history_sessions": len(calendar)}
    if universe_provenance.get("as_of_session") != calendar[-1]:
        return {"status": "insufficient_evidence", "reason": "universe_snapshot_session_mismatch", "score": None}
    if isinstance(minimum_symbol_coverage, bool) or not isinstance(minimum_symbol_coverage, (int, float)) or not 0 < minimum_symbol_coverage <= 1:
        raise ValueError("minimum_symbol_coverage must be in (0, 1]")

    required_dates = calendar[-MIN_HISTORY_SESSIONS:]
    required_set = set(required_dates)
    expected = set(symbols)
    grouped = {symbol: {} for symbol in symbols}
    rejected = []
    unexpected = set()
    for index, row in enumerate(rows):
        symbol = str(row.get("symbol", "")).strip().upper()
        session = str(row.get("session_date", ""))
        if symbol not in expected:
            if symbol:
                unexpected.add(symbol)
            continue
        if session not in required_set:
            continue
        if row.get("record_type") != "ohlcv" or row.get("source_validation_status") != "verified" or row.get("finality_status") != "final":
            rejected.append({"symbol": symbol, "session_date": session, "reason": "row_not_verified_final_ohlcv"})
            continue
        if not isinstance(row.get("source_id"), str) or not row["source_id"].strip() or not _digest(row.get("source_payload_sha256")):
            rejected.append({"symbol": symbol, "session_date": session, "reason": "invalid_source_provenance"})
            continue
        try:
            available = _utc(row.get("available_at"), "available_at")
            close = _positive(row.get("close"), "close")
            high = _positive(row.get("high"), "high")
            low = _positive(row.get("low"), "low")
        except ValueError as exc:
            rejected.append({"symbol": symbol, "session_date": session, "reason": str(exc)})
            continue
        if available > cutoff:
            rejected.append({"symbol": symbol, "session_date": session, "reason": "future_available_at"})
            continue
        if low > close or high < close or high < low:
            rejected.append({"symbol": symbol, "session_date": session, "reason": "invalid_ohlc_range"})
            continue
        if session in grouped[symbol]:
            raise ValueError(f"duplicate OHLCV session: {symbol} {session}")
        grouped[symbol][session] = {"close": close, "high": high, "low": low}

    per_symbol = {}
    for symbol in symbols:
        series = grouped[symbol]
        if any(day not in series for day in required_dates):
            continue
        closes = [series[day]["close"] for day in required_dates]
        current = closes[-1]
        prior = closes[-2]
        sma50 = sum(closes[-50:]) / 50
        sma200 = sum(closes[-200:]) / 200
        per_symbol[symbol] = {
            "advance": current > prior,
            "decline": current < prior,
            "unchanged": current == prior,
            "above_sma50": current > sma50,
            "above_sma200": current > sma200,
            "new_20_session_high": current >= max(closes[-20:]),
            "new_20_session_low": current <= min(closes[-20:]),
        }

    observed = len(per_symbol)
    coverage = observed / len(symbols)
    counts = {key: sum(1 for item in per_symbol.values() if item[key]) for key in (
        "advance", "decline", "unchanged", "above_sma50", "above_sma200",
        "new_20_session_high", "new_20_session_low",
    )}
    if coverage < minimum_symbol_coverage:
        return {
            "status": "insufficient_evidence", "reason": "mature_universe_symbol_coverage_below_threshold",
            "score": None, "as_of_session": required_dates[-1], "expected_symbols": len(symbols),
            "observed_symbols": observed, "coverage_pct": round(coverage * 100, 2),
            "missing_symbols": sorted(expected - set(per_symbol)), "rejected_rows": rejected,
            "unexpected_symbols": sorted(unexpected), "counts": counts,
        }

    adv = counts["advance"]
    dec = counts["decline"]
    adv_decline_balance = (adv / (adv + dec) * 100) if adv + dec else 50.0
    above50 = counts["above_sma50"] / observed * 100
    above200 = counts["above_sma200"] / observed * 100
    high_low = counts["new_20_session_high"] / max(
        1, counts["new_20_session_high"] + counts["new_20_session_low"]
    ) * 100 if counts["new_20_session_high"] + counts["new_20_session_low"] else 50.0
    score = 0.30 * adv_decline_balance + 0.25 * above50 + 0.25 * above200 + 0.20 * high_low
    return {
        "status": "verified", "score": round(score, 2), "as_of_session": required_dates[-1],
        "source_id": universe_provenance["source_id"],
        "source_payload_sha256": str(universe_provenance["source_payload_sha256"]).lower(),
        "expected_symbols": len(symbols), "observed_symbols": observed,
        "coverage_pct": round(coverage * 100, 2), "counts": counts,
        "metrics": {
            "advance_decline_ratio": round(adv / dec, 4) if dec else None,
            "adv_decline_balance_pct": round(adv_decline_balance, 2),
            "pct_above_sma50": round(above50, 2),
            "pct_above_sma200": round(above200, 2),
            "20_session_high_low_balance_pct": round(high_low, 2),
        },
        "rejected_row_count": len(rejected), "rejected_rows": rejected,
        "unexpected_symbols": sorted(unexpected),
        "interpretation": "rules_based_cross_sectional_market_breadth_not_a_probability",
        "limitations": [
            "Expected symbols must be a validated mature-equity cohort active on the as-of session",
            "Requires exact 200-session verified OHLCV for each included security",
            "No missing sessions, securities or values are imputed",
            "20-session high/low counts are not 52-week highs/lows",
            "Score is descriptive market context, not a standalone trading signal",
        ],
    }
