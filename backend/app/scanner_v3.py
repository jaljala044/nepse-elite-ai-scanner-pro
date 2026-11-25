"""V3 descriptive OHLCV research features.

This module is deliberately separate from the legacy scanner. It emits
measurable observations, not buy/sell instructions or claims of institutional
intent. Input rows are never silently repaired.
"""
from __future__ import annotations

from datetime import date
from math import isfinite
from statistics import mean
from typing import Any


REQUIRED_FIELDS = ("date", "open", "high", "low", "close", "volume")


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise ValueError("date must be a date object or ISO date string")


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _wilder(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    current = mean(values[:period])
    for value in values[period:]:
        current = ((current * (period - 1)) + value) / period
    return current


def _rsi(closes: list[float], period: int = 14) -> float | None:
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    if len(changes) < period:
        return None
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gain = _wilder(gains, period)
    avg_loss = _wilder(losses, period)
    if avg_gain is None or avg_loss is None:
        return None
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    if avg_gain == 0:
        return 0.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def _atr(rows: list[dict[str, Any]], period: int = 14) -> float | None:
    if len(rows) < period + 1:
        return None
    true_ranges = []
    for index in range(1, len(rows)):
        bar = rows[index]
        previous_close = rows[index - 1]["close"]
        true_ranges.append(max(
            bar["high"] - bar["low"],
            abs(bar["high"] - previous_close),
            abs(bar["low"] - previous_close),
        ))
    return _wilder(true_ranges, period)


def analyze_v3(symbol: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate and describe a single symbol's chronologically ordered daily bars."""
    base: dict[str, Any] = {
        "engine": "v3",
        "symbol": str(symbol).strip().upper(),
        "status": "insufficient_data",
        "as_of": None,
        "observations": len(observations),
        "metrics": {},
        "evidence": [],
        "limitations": [
            "Descriptive research output only; not a buy/sell recommendation or guaranteed prediction.",
            "OHLCV alone cannot establish broker intent, manipulation, accumulation, or distribution.",
            "Corporate-action adjustment, source provenance, and exchange-calendar completeness must be validated upstream.",
        ],
        "data_quality_errors": [],
    }
    if not base["symbol"]:
        base["status"] = "data_quality_error"
        base["data_quality_errors"].append("symbol is empty")
        return base

    normalized: list[dict[str, Any]] = []
    for index, source in enumerate(observations):
        if not isinstance(source, dict):
            base["data_quality_errors"].append(f"row {index}: observation must be an object")
            continue
        missing = [field for field in REQUIRED_FIELDS if field not in source]
        if missing:
            base["data_quality_errors"].append(f"row {index}: missing fields {', '.join(missing)}")
            continue
        try:
            row = {
                "date": _as_date(source["date"]),
                "open": _number(source["open"], "open"),
                "high": _number(source["high"], "high"),
                "low": _number(source["low"], "low"),
                "close": _number(source["close"], "close"),
                "volume": _number(source["volume"], "volume"),
            }
        except (ValueError, TypeError) as exc:
            base["data_quality_errors"].append(f"row {index}: {exc}")
            continue
        if min(row["open"], row["high"], row["low"], row["close"]) <= 0 or row["volume"] < 0:
            base["data_quality_errors"].append(f"row {index}: prices must be positive and volume non-negative")
            continue
        if row["high"] < max(row["open"], row["close"], row["low"]):
            base["data_quality_errors"].append(f"row {index}: high is below another OHLC value")
            continue
        if row["low"] > min(row["open"], row["close"], row["high"]):
            base["data_quality_errors"].append(f"row {index}: low is above another OHLC value")
            continue
        normalized.append(row)

    if base["data_quality_errors"]:
        base["status"] = "data_quality_error"
        return base

    normalized.sort(key=lambda row: row["date"])
    dates = [row["date"] for row in normalized]
    if len(set(dates)) != len(dates):
        base["status"] = "data_quality_error"
        base["data_quality_errors"].append("duplicate session dates detected")
        return base
    if not normalized:
        return base

    base["as_of"] = dates[-1].isoformat()
    if len(normalized) < 50:
        base["limitations"].append("At least 50 daily observations are required for the initial SMA50 and 20-session return features.")
        return base

    closes = [row["close"] for row in normalized]
    volumes = [row["volume"] for row in normalized]
    sma20 = mean(closes[-20:])
    sma50 = mean(closes[-50:])
    average_volume20 = mean(volumes[-20:])
    return20 = ((closes[-1] / closes[-21]) - 1.0) * 100.0
    rsi14 = _rsi(closes, 14)
    atr14 = _atr(normalized, 14)
    volume_ratio20 = (volumes[-1] / average_volume20) if average_volume20 > 0 else None

    base["metrics"] = {
        "close": round(closes[-1], 6),
        "sma20": round(sma20, 6),
        "sma50": round(sma50, 6),
        "return_20_sessions_pct": round(return20, 4),
        "rsi14": round(rsi14, 4) if rsi14 is not None else None,
        "atr14": round(atr14, 6) if atr14 is not None else None,
        "atr14_pct_of_close": round((atr14 / closes[-1]) * 100.0, 4) if atr14 is not None else None,
        "volume_ratio20": round(volume_ratio20, 4) if volume_ratio20 is not None else None,
    }

    if closes[-1] > sma20 > sma50:
        base["evidence"].append("close_above_sma20_and_sma50_with_sma20_above_sma50")
    elif closes[-1] < sma20 < sma50:
        base["evidence"].append("close_below_sma20_and_sma50_with_sma20_below_sma50")
    else:
        base["evidence"].append("mixed_sma_alignment")
    if return20 > 0:
        base["evidence"].append("positive_20_session_return")
    elif return20 < 0:
        base["evidence"].append("negative_20_session_return")
    else:
        base["evidence"].append("flat_20_session_return")
    if volume_ratio20 is not None and volume_ratio20 >= 1.5:
        base["evidence"].append("volume_expansion_1_5x_20_session_average")
    if rsi14 is not None:
        base["evidence"].append("rsi14_above_70" if rsi14 > 70 else "rsi14_below_30" if rsi14 < 30 else "rsi14_between_30_and_70")

    base["status"] = "ready"
    return base
