"""Point-in-time Minervini trend-template observations.

Input rows must already be restricted to the requested decision timestamp.
This module calculates a descriptive component only; it never emits trade actions.
"""
from __future__ import annotations

from datetime import date, datetime
from math import isfinite


def _session_date(value):
    if isinstance(value, datetime):
        raise ValueError("session date must not contain a time component")
    if isinstance(value, date):
        return value.isoformat()
    return date.fromisoformat(str(value)).isoformat()


def evaluate_minervini_trend(rows: list[dict]) -> dict:
    """Evaluate eight explicit trend-template checks with disclosed coverage."""
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    ordered = sorted(rows, key=lambda row: _session_date(row["date"]))
    seen = set()
    closes, highs, lows = [], [], []
    for index, row in enumerate(ordered):
        day = _session_date(row["date"])
        if day in seen:
            raise ValueError(f"duplicate session date: {day}")
        seen.add(day)
        try:
            op, high, low, close = (
                float(row[key]) for key in ("open", "high", "low", "close")
            )
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"row {index}: invalid OHLC values") from exc
        if (not all(isfinite(v) for v in (op, high, low, close))
                or min(op, high, low, close) <= 0
                or high < max(op, low, close)
                or low > min(op, high, close)):
            raise ValueError(f"row {index}: OHLC invariant failed")
        closes.append(close)
        highs.append(high)
        lows.append(low)

    n = len(closes)
    checks = {}
    missing = []

    def add(name, value):
        if value is None:
            missing.append(name)
        else:
            checks[name] = bool(value)

    if n >= 50:
        ma50 = sum(closes[-50:]) / 50
        add("price_above_50_dma", closes[-1] > ma50)
    else:
        ma50 = None
        add("price_above_50_dma", None)

    if n >= 150:
        ma150 = sum(closes[-150:]) / 150
        add("price_above_150_dma", closes[-1] > ma150)
    else:
        ma150 = None
        add("price_above_150_dma", None)

    if n >= 200:
        ma200 = sum(closes[-200:]) / 200
        add("price_above_200_dma", closes[-1] > ma200)
        add("ma_alignment_50_gt_150_gt_200",
            ma50 > ma150 > ma200 if ma50 is not None and ma150 is not None else None)
    else:
        ma200 = None
        add("price_above_200_dma", None)
        add("ma_alignment_50_gt_150_gt_200", None)

    if n >= 220:
        prior_ma200 = sum(closes[-220:-20]) / 200
        add("200_dma_rising", ma200 > prior_ma200 if ma200 is not None else None)
    else:
        add("200_dma_rising", None)

    if n >= 252:
        high_52w = max(highs[-252:])
        low_52w = min(lows[-252:])
        add("within_25_percent_of_52w_high", closes[-1] >= high_52w * 0.75)
        add("at_least_30_percent_above_52w_low", closes[-1] >= low_52w * 1.30)
    else:
        high_52w = low_52w = None
        add("within_25_percent_of_52w_high", None)
        add("at_least_30_percent_above_52w_low", None)

    if n >= 40:
        recent_high = max(highs[-20:])
        prior_high = max(highs[-40:-20])
        recent_low = min(lows[-20:])
        prior_low = min(lows[-40:-20])
        add("recent_20s_higher_high_and_higher_low",
            recent_high > prior_high and recent_low > prior_low)
    else:
        add("recent_20s_higher_high_and_higher_low", None)

    coverage = len(checks) / 8
    complete = not missing
    score = round(sum(checks.values()) / 8 * 100, 2) if complete else None
    return {
        "component": "minervini_trend",
        "status": "observed" if complete else "insufficient_evidence",
        "score": score,
        "coverage": round(coverage, 4),
        "checks_passed": sum(checks.values()),
        "checks_available": len(checks),
        "checks_total": 8,
        "checks": checks,
        "missing_checks": missing,
        "observations": n,
        "as_of": _session_date(ordered[-1]["date"]) if ordered else None,
        "moving_averages": {
            "dma_50": round(ma50, 6) if ma50 is not None else None,
            "dma_150": round(ma150, 6) if ma150 is not None else None,
            "dma_200": round(ma200, 6) if ma200 is not None else None,
            "high_52w": high_52w,
            "low_52w": low_52w,
        },
        "interpretation": "descriptive_trend_template_only_not_a_buy_signal",
        "methodology_version": "minervini-template-v1",
    }
