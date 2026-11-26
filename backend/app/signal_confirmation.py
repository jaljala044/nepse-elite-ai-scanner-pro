"""Conservative signal confirmation primitives (research-only, no orders)."""
from __future__ import annotations
from datetime import date, datetime
from math import isfinite
from statistics import mean



def _signal_input_errors(rows):
    """Validate only fields consumed by this classifier; NEPSE history has no open."""
    errors = []
    seen = set()
    if not isinstance(rows, list):
        return ["rows_not_a_list"]
    for index, row in enumerate(rows):
        try:
            raw_date = row["date"]
            if isinstance(raw_date, datetime):
                raise ValueError("datetime_not_session_date")
            session_date = raw_date if isinstance(raw_date, date) else date.fromisoformat(str(raw_date))
            if session_date in seen:
                errors.append(f"duplicate_date:{session_date}")
            seen.add(session_date)
            high, low, close, volume = (float(row[key]) for key in ("high", "low", "close", "volume"))
            if not all(isfinite(value) for value in (high, low, close, volume)):
                raise ValueError("non_finite_signal_input")
            if volume < 0 or not volume.is_integer():
                errors.append(f"invalid_signal_volume:{index}")
            elif volume > 0:
                if min(high, low, close) <= 0:
                    errors.append(f"invalid_signal_prices:{index}")
                if high < max(low, close) or low > min(high, close):
                    errors.append(f"invalid_signal_range:{index}")
        except (KeyError, ValueError, TypeError, OverflowError):
            errors.append(f"malformed_signal_row:{index}")
    return errors

def confirm_signal(rows, *, eligible=False, min_observations=55,
                   breakout_lookback=20, volume_multiple=1.5):
    """Classify daily OHLCV setup. A confirmation is not a trade recommendation."""
    base = {
        "engine": "signal_confirmation_v1", "status": "unknown",
        "classification": "UNKNOWN",
        "as_of": None, "observations": len(rows) if isinstance(rows, list) else 0,
        "features": {}, "checks": {},
        "limitations": [
            "Research-only technical pattern; not a BUY, SELL, HOLD or NO TRADE decision.",
            "Thresholds are transparent defaults and have not been validated by out-of-sample backtesting.",
            "No intraday, order-book, broker-flow, sector or market-regime evidence is included.",
        ],
    }
    if not eligible:
        base["limitations"].append("Server-reviewed source, session and point-in-time eligibility was not supplied.")
        return base
    if not isinstance(rows, list) or not rows or _signal_input_errors(rows):
        base["limitations"].append("Required high/low/close/volume input is empty or failed structural validation.")
        return base
    valid_volume_multiple = (
        isinstance(volume_multiple, (int, float))
        and not isinstance(volume_multiple, bool)
        and isfinite(float(volume_multiple))
        and volume_multiple > 0
    )
    if (not isinstance(min_observations, int) or isinstance(min_observations, bool) or min_observations < 51
            or not isinstance(breakout_lookback, int) or isinstance(breakout_lookback, bool) or breakout_lookback < 5
            or not valid_volume_multiple):
        raise ValueError("invalid signal confirmation configuration")
    source_rows_received = len(rows)
    ordered = sorted(
        (row for row in rows if float(row["volume"]) > 0),
        key=lambda row: str(row["date"]),
    )
    base["observations"] = len(ordered)
    base["source_rows_received"] = source_rows_received
    base["zero_volume_rows_excluded"] = source_rows_received - len(ordered)
    required = max(min_observations, breakout_lookback + 1, 51)
    if len(ordered) < required:
        base["status"] = "insufficient_data"
        base["limitations"].append(f"At least {required} daily observations are required.")
        return base
    closes = [float(row["close"]) for row in ordered]
    volumes = [float(row["volume"]) for row in ordered]
    last = ordered[-1]
    prior = ordered[-(breakout_lookback + 1):-1]
    prior_high = max(float(row["high"]) for row in prior)
    prior_low = min(float(row["low"]) for row in prior)
    sma20, sma50 = mean(closes[-20:]), mean(closes[-50:])
    prior_volume = mean(volumes[-21:-1])
    relative_volume = volumes[-1] / prior_volume if prior_volume > 0 else None
    candle_range = float(last["high"]) - float(last["low"])
    close_location = ((float(last["close"]) - float(last["low"])) / candle_range
                      if candle_range > 0 else None)
    checks = {
        "breakout_above_prior_high": closes[-1] > prior_high,
        "breakdown_below_prior_low": closes[-1] < prior_low,
        "close_above_sma20": closes[-1] > sma20,
        "close_above_sma50": closes[-1] > sma50,
        "close_below_sma20": closes[-1] < sma20,
        "close_below_sma50": closes[-1] < sma50,
        "sma20_above_sma50": sma20 > sma50,
        "sma20_below_sma50": sma20 < sma50,
        "volume_expansion": relative_volume is not None and relative_volume >= volume_multiple,
        "strong_close": close_location is not None and close_location >= 0.75,
        "weak_close": close_location is not None and close_location <= 0.25,
    }
    bullish = all(checks[k] for k in (
        "breakout_above_prior_high", "close_above_sma20", "close_above_sma50",
        "sma20_above_sma50", "volume_expansion", "strong_close"))
    bearish = all(checks[k] for k in (
        "breakdown_below_prior_low", "close_below_sma20", "close_below_sma50",
        "sma20_below_sma50", "volume_expansion", "weak_close"))
    classification = "bullish_confirmation" if bullish else (
        "bearish_warning" if bearish else "no_confirmation")
    return {
        **base, "status": "research_confirmed" if bullish or bearish else "research_evaluated",
        "classification": classification, "as_of": str(last["date"]),
        "features": {
            "close": closes[-1], "prior_lookback_high": prior_high,
            "prior_lookback_low": prior_low, "sma20": round(sma20, 6),
            "sma50": round(sma50, 6),
            "relative_volume20": round(relative_volume, 6) if relative_volume is not None else None,
            "close_location_in_candle": round(close_location, 6) if close_location is not None else None,
            "breakout_lookback": breakout_lookback,
            "volume_multiple_threshold": volume_multiple,
        },
        "checks": checks,
    }
