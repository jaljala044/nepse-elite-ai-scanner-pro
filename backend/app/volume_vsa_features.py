"""Descriptive volume/spread analysis from validated OHLCV observations.

This is a transparent rules-based VSA feature set, not a standalone trade signal.
"""
from __future__ import annotations

from datetime import date
import math


def volume_vsa_features(rows: list[dict], lookback: int = 20) -> dict:
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 5:
        raise ValueError("lookback must be an integer >= 5")
    ordered = sorted(rows, key=lambda row: str(row.get("session_date", "")))
    seen = set()
    normalized = []
    required = ("session_date", "open", "high", "low", "close", "volume")
    for i, row in enumerate(ordered):
        if any(key not in row or row[key] is None for key in required):
            return {
                "status": "insufficient_evidence",
                "reason": "required_ohlcv_fields_missing",
                "score": None,
                "history_sessions": len(rows),
            }
        try:
            day = date.fromisoformat(str(row["session_date"])).isoformat()
            values = {key: float(row[key]) for key in required[1:]}
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"row {i}: invalid date or OHLCV value") from exc
        if day in seen:
            raise ValueError(f"duplicate session_date: {day}")
        seen.add(day)
        if any(not math.isfinite(v) for v in values.values()):
            raise ValueError(f"row {i}: non-finite OHLCV value")
        if any(values[k] <= 0 for k in ("open", "high", "low", "close")) or values["volume"] < 0:
            raise ValueError(f"row {i}: prices must be positive and volume non-negative")
        if values["high"] < max(values["open"], values["close"], values["low"]):
            raise ValueError(f"row {i}: inconsistent high")
        if values["low"] > min(values["open"], values["close"], values["high"]):
            raise ValueError(f"row {i}: inconsistent low")
        normalized.append({"session_date": day, **values})

    if len(normalized) < lookback + 1:
        return {
            "status": "insufficient_evidence",
            "reason": f"requires_{lookback + 1}_sessions",
            "score": None,
            "history_sessions": len(normalized),
        }

    current = normalized[-1]
    prior = normalized[-lookback - 1:-1]
    avg_volume = sum(x["volume"] for x in prior) / lookback
    avg_spread = sum(x["high"] - x["low"] for x in prior) / lookback
    spread = current["high"] - current["low"]
    relative_volume = current["volume"] / avg_volume if avg_volume > 0 else None
    relative_spread = spread / avg_spread if avg_spread > 0 else None
    close_location = (
        (current["close"] - current["low"]) / spread if spread > 0 else None
    )
    prior_high = max(x["high"] for x in prior)
    prior_low = min(x["low"] for x in prior)
    previous_close = normalized[-2]["close"]
    price_change_pct = (current["close"] / previous_close - 1) * 100

    expansion = relative_volume is not None and relative_volume >= 1.5
    dry_up = relative_volume is not None and relative_volume <= 0.7
    wide_spread = relative_spread is not None and relative_spread >= 1.5
    narrow_spread = relative_spread is not None and relative_spread <= 0.7
    breakout = current["close"] > prior_high
    breakdown = current["close"] < prior_low
    strong_close = close_location is not None and close_location >= 0.70
    weak_close = close_location is not None and close_location <= 0.30

    # Each observable condition contributes transparently; absence of a metric
    # does not receive a neutral point.
    checks = {
        "volume_expansion": expansion,
        "volume_dry_up": dry_up,
        "wide_spread": wide_spread,
        "narrow_spread": narrow_spread,
        "close_near_high": strong_close,
        "close_near_low": weak_close,
        "close_breakout": breakout,
        "close_breakdown": breakdown,
    }
    bullish = (expansion and strong_close) or (breakout and expansion)
    bearish = (expansion and weak_close) or (breakdown and expansion)
    if bullish and not bearish:
        interpretation = "demand_response_observed"
    elif bearish and not bullish:
        interpretation = "supply_response_observed"
    elif dry_up and narrow_spread:
        interpretation = "low_activity_or_supply_dry_up_requires_context"
    else:
        interpretation = "mixed_or_non_confirming_volume_evidence"

    # Scoring is a descriptive balance of directional evidence, not a forecast.
    directional = (
        int(expansion and strong_close)
        + int(breakout and expansion)
        + int(dry_up and narrow_spread)
        - int(expansion and weak_close)
        - int(breakdown and expansion)
    )
    score = max(0, min(100, 50 + directional * 10))
    return {
        "status": "observed",
        "score": score,
        "as_of_session": current["session_date"],
        "history_sessions": len(normalized),
        "lookback_sessions": lookback,
        "volume": current["volume"],
        "average_prior_volume": round(avg_volume, 4),
        "relative_volume": round(relative_volume, 4) if relative_volume is not None else None,
        "spread": round(spread, 4),
        "average_prior_spread": round(avg_spread, 4),
        "relative_spread": round(relative_spread, 4) if relative_spread is not None else None,
        "close_location_value": round(close_location, 4) if close_location is not None else None,
        "price_change_pct": round(price_change_pct, 4),
        "prior_lookback_high": prior_high,
        "prior_lookback_low": prior_low,
        "checks": checks,
        "interpretation": interpretation,
        "signal": "not_a_standalone_buy_or_sell_signal",
    }
