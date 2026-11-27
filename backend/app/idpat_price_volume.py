"""IDPAT-1 point-in-time price/volume and candle-context research engine.

This is a partial research component, not a complete IDPAT score or trading signal.
It consumes caller-supplied, already verified OHLCV evidence and never fetches data.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


class IDPATError(ValueError):
    """Invalid or temporally inconsistent IDPAT input."""


def _decimal(value, field: str, *, signed: bool = False) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise IDPATError(f"invalid_{field}") from None
    if not result.is_finite() or (not signed and result < 0):
        raise IDPATError(f"invalid_{field}")
    return result


def _timestamp(value, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise IDPATError(f"invalid_{field}") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise IDPATError(f"{field}_must_be_timezone_aware")
    return result


def _withheld(symbol: str | None, reason: str, coverage: str | None = None) -> dict:
    return {
        "symbol": symbol, "schema_version": "idpat-1.0.0",
        "status": "withheld", "action": "NO_TRADE",
        "overall_score": None, "data_quality": "LOW_CONFIDENCE",
        "coverage": coverage, "reason": reason, "probability": None,
    }


def analyze_idpat_price_volume(
    snapshot: dict, *, as_of_date: str, as_of_timestamp: str,
    min_coverage: Decimal = Decimal("0.95"),
) -> dict:
    """Analyze OHLCV bars as of a cutoff; output descriptive features only.

    Required evidence shape:
      snapshot = {symbol, price_volume: {status, source_id, coverage,
        available_at, bars: [{date, open, high, low, close, volume}, ...]}}
    Bars must be ascending, unique, and no later than the requested cutoff.
    """
    if not isinstance(snapshot, dict):
        raise IDPATError("snapshot_required")
    symbol = snapshot.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        raise IDPATError("invalid_symbol")
    try:
        cutoff_day = date.fromisoformat(as_of_date)
    except (TypeError, ValueError):
        raise IDPATError("invalid_as_of_date") from None
    cutoff_time = _timestamp(as_of_timestamp, "as_of_timestamp")
    threshold = _decimal(min_coverage, "min_coverage")
    if threshold <= 0 or threshold > 1:
        raise IDPATError("invalid_min_coverage")

    evidence = snapshot.get("price_volume")
    if not isinstance(evidence, dict):
        return _withheld(symbol, "price_volume_evidence_missing")
    if evidence.get("status") != "verified":
        return _withheld(symbol, "price_volume_evidence_not_verified")
    source_id = evidence.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise IDPATError("source_id_required")
    coverage = _decimal(evidence.get("coverage"), "coverage")
    if coverage > 1:
        raise IDPATError("coverage_above_one")
    if coverage < threshold:
        return _withheld(symbol, "coverage_below_threshold", str(coverage))
    available = _timestamp(evidence.get("available_at"), "evidence_available_at")
    if available > cutoff_time:
        return _withheld(symbol, "evidence_not_available_as_of_cutoff", str(coverage))

    bars = evidence.get("bars")
    if not isinstance(bars, list) or len(bars) < 21:
        return _withheld(symbol, "at_least_21_valid_bars_required", str(coverage))
    parsed = []
    previous_day = None
    for index, bar in enumerate(bars):
        if not isinstance(bar, dict):
            raise IDPATError("bar_must_be_mapping")
        try:
            day = date.fromisoformat(bar.get("date"))
        except (TypeError, ValueError):
            raise IDPATError("invalid_bar_date") from None
        if day > cutoff_day:
            return _withheld(symbol, "bar_after_cutoff", str(coverage))
        if previous_day is not None and day <= previous_day:
            raise IDPATError("bars_must_be_unique_and_ascending")
        previous_day = day
        values = {key: _decimal(bar.get(key), f"bar_{key}") for key in
                  ("open", "high", "low", "close", "volume")}
        if min(values[k] for k in ("open", "high", "low", "close")) <= 0:
            raise IDPATError("ohlc_prices_must_be_positive")
        if values["high"] < max(values["open"], values["close"], values["low"]):
            raise IDPATError("invalid_bar_high")
        if values["low"] > min(values["open"], values["close"], values["high"]):
            raise IDPATError("invalid_bar_low")
        parsed.append({"date": day.isoformat(), **values})

    last = parsed[-1]
    prior20 = parsed[-21:-1]
    avg_volume = sum(x["volume"] for x in prior20) / Decimal(20)
    volume_ratio = last["volume"] / avg_volume if avg_volume else None
    prior_high = max(x["high"] for x in prior20)
    prior_low = min(x["low"] for x in prior20)
    range20 = prior_high - prior_low
    close_position = ((last["close"] - prior_low) / range20) if range20 else None

    body = abs(last["close"] - last["open"])
    candle_range = last["high"] - last["low"]
    lower_wick = min(last["open"], last["close"]) - last["low"]
    upper_wick = last["high"] - max(last["open"], last["close"])
    bullish_rejection = (
        candle_range > 0 and last["close"] > last["open"]
        and lower_wick >= max(body * 2, candle_range * Decimal("0.35"))
        and (last["high"] - last["close"]) / candle_range <= Decimal("0.35")
    )
    bearish_rejection = (
        candle_range > 0 and last["close"] < last["open"]
        and upper_wick >= max(body * 2, candle_range * Decimal("0.35"))
        and (last["close"] - last["low"]) / candle_range <= Decimal("0.35")
    )
    penetration = last["high"] > prior_high
    breakout_confirmed = (
        last["close"] > prior_high and volume_ratio is not None
        and volume_ratio >= Decimal("1.5")
    )
    failed_breakout_warning = penetration and last["close"] <= prior_high
    breakdown_confirmed = (
        last["close"] < prior_low and volume_ratio is not None
        and volume_ratio >= Decimal("1.5")
    )

    # Transparent sub-scores only. They are not combined into a full IDPAT score.
    pv_points = 0
    if volume_ratio is not None and volume_ratio >= Decimal("1.5"):
        pv_points += 40
    elif volume_ratio is not None and volume_ratio >= Decimal("1.2"):
        pv_points += 25
    if close_position is not None and close_position >= Decimal("0.75"):
        pv_points += 30
    elif close_position is not None and close_position >= Decimal("0.5"):
        pv_points += 15
    if breakout_confirmed:
        pv_points += 30
    elif breakdown_confirmed:
        pv_points += 30

    candle_points = 50 if bullish_rejection else 0
    if bearish_rejection:
        candle_points = 0
    if body > 0 and candle_range > 0 and body / candle_range >= Decimal("0.7"):
        candle_points = max(candle_points, 35 if last["close"] > last["open"] else 0)

    return {
        "symbol": symbol, "schema_version": "idpat-1.0.0",
        "status": "partial_research_only", "action": "NO_TRADE",
        "overall_score": None, "data_quality": "MEDIUM_CONFIDENCE",
        "coverage": str(coverage), "as_of_date": last["date"],
        "available_at": available.isoformat(), "source_ids": [source_id],
        "components": {
            "price_volume_score_partial": pv_points,
            "candlestick_context_score_partial": candle_points,
        },
        "signals": {
            "volume_vs_prior_20_sessions": str(volume_ratio) if volume_ratio is not None else None,
            "close_position_in_prior_20_session_range": str(close_position) if close_position is not None else None,
            "prior_20_session_high": str(prior_high),
            "prior_20_session_low": str(prior_low),
            "bullish_rejection_candle": bullish_rejection,
            "bearish_rejection_candle": bearish_rejection,
            "breakout_confirmed_by_close_and_volume": breakout_confirmed,
            "failed_breakout_warning": failed_breakout_warning,
            "breakdown_confirmed_by_close_and_volume": breakdown_confirmed,
        },
        "limitations": [
            "IDPAT-1 is partial: no overall IDPAT score is emitted.",
            "OHLCV patterns do not identify actual institutional orders or beneficial ownership.",
            "Opening-range, intraday, broker-flow, order-book, multi-timeframe and risk-plan modules are not implemented here.",
            "Breakout and breakdown flags are descriptive and are not BUY/SELL instructions.",
            "No probabilities, backtest claims, entry, stop or targets are generated.",
        ],
    }
