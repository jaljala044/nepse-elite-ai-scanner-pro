"""Minervini-style trend template from validated, point-in-time OHLCV rows.

Rows must already be Stage-1 validated and filtered as-of the decision time.
No historical price adjustment or session interpolation is performed.
"""
from __future__ import annotations

from datetime import date
import math


def _validated_rows(rows: list[dict], required: tuple[str, ...]) -> list[dict]:
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    ordered = sorted(rows, key=lambda row: str(row.get("session_date", "")))
    dates = []
    for i, row in enumerate(ordered):
        try:
            session = date.fromisoformat(str(row["session_date"]))
            values = {key: float(row[key]) for key in required}
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"row {i}: invalid session_date or OHLCV field") from exc
        if any(not math.isfinite(v) or v <= 0 for v in values.values()):
            raise ValueError(f"row {i}: OHLC values must be finite and positive")
        if "high" in values and "low" in values and values["high"] < values["low"]:
            raise ValueError(f"row {i}: high is below low")
        dates.append(session.isoformat())
    if len(dates) != len(set(dates)):
        raise ValueError("duplicate session_date rows are not allowed")
    return ordered


def minervini_trend_template(rows: list[dict]) -> dict:
    """Return a seven-condition trend-template score; require 252 sessions."""
    ordered = _validated_rows(rows, ("close", "high", "low"))
    if len(ordered) < 252:
        return {
            "status": "insufficient_evidence",
            "reason": "requires_252_valid_trading_sessions_for_52_week_context",
            "history_sessions": len(ordered),
            "score": None,
            "checks": {},
        }

    closes = [float(r["close"]) for r in ordered]
    highs = [float(r["high"]) for r in ordered]
    lows = [float(r["low"]) for r in ordered]
    close = closes[-1]

    def sma(end: int, period: int) -> float:
        return sum(closes[end - period:end]) / period

    ma50 = sma(len(closes), 50)
    ma150 = sma(len(closes), 150)
    ma200 = sma(len(closes), 200)
    ma200_20_sessions_ago = sma(len(closes) - 20, 200)
    high_52w = max(highs[-252:])
    prior_highs = max(highs[-40:-20])
    recent_highs = max(highs[-20:])
    prior_lows = min(lows[-40:-20])
    recent_lows = min(lows[-20:])

    checks = {
        "price_above_50dma": close > ma50,
        "price_above_150dma": close > ma150,
        "price_above_200dma": close > ma200,
        "ma50_above_ma150_above_ma200": ma50 > ma150 > ma200,
        "ma200_rising_vs_20_sessions_ago": ma200 > ma200_20_sessions_ago,
        "within_25pct_of_52_week_high": close >= high_52w * 0.75,
        "higher_high_and_higher_low_vs_prior_20_sessions": (
            recent_highs > prior_highs and recent_lows > prior_lows
        ),
    }
    passed = sum(checks.values())
    return {
        "status": "observed",
        "score": round(passed / len(checks) * 100, 2),
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "as_of_session": ordered[-1]["session_date"],
        "close": close,
        "sma_50": round(ma50, 4),
        "sma_150": round(ma150, 4),
        "sma_200": round(ma200, 4),
        "sma_200_20_sessions_ago": round(ma200_20_sessions_ago, 4),
        "high_52_week": high_52w,
        "distance_from_52_week_high_pct": round((close / high_52w - 1) * 100, 2),
        "history_sessions": len(ordered),
        "interpretation": "trend_template_observation_not_a_standalone_buy_signal",
    }
