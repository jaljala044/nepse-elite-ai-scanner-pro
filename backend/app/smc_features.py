"""Point-in-time Smart Money Concepts observations from validated OHLC bars.

Pivot points are only emitted after the right-hand confirmation bars have
closed. All event timestamps refer to the confirmation/current bar, never a
future bar. Outputs are structural observations, not trade instructions.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import date
import math

PIVOT_WING = 2
MIN_DAILY_HISTORY = 10


def _validate(rows: list[dict]) -> list[dict]:
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    ordered = sorted(rows, key=lambda row: str(row.get("session_date", "")))
    seen = set()
    result = []
    for i, row in enumerate(ordered):
        try:
            day = date.fromisoformat(str(row["session_date"])).isoformat()
            values = {key: float(row[key]) for key in ("open", "high", "low", "close")}
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"row {i}: invalid session_date or OHLC field") from exc
        if day in seen:
            raise ValueError(f"duplicate session_date: {day}")
        seen.add(day)
        if any(not math.isfinite(value) or value <= 0 for value in values.values()):
            raise ValueError(f"row {i}: OHLC values must be finite and positive")
        if values["high"] < max(values["open"], values["close"], values["low"]):
            raise ValueError(f"row {i}: inconsistent high")
        if values["low"] > min(values["open"], values["close"], values["high"]):
            raise ValueError(f"row {i}: inconsistent low")
        result.append({"session_date": day, **values})
    return result


def _aggregate(rows: list[dict], period: str) -> list[dict]:
    buckets: OrderedDict[str, list[dict]] = OrderedDict()
    for row in rows:
        parsed = date.fromisoformat(row["session_date"])
        key = f"{parsed.isocalendar().year}-W{parsed.isocalendar().week:02d}" if period == "weekly" else parsed.strftime("%Y-%m")
        buckets.setdefault(key, []).append(row)
    # Exclude the most recent calendar bucket: it may still be forming.
    completed = list(buckets.items())[:-1]
    output = []
    for _, group in completed:
        output.append({
            "session_date": group[-1]["session_date"],
            "open": group[0]["open"],
            "high": max(x["high"] for x in group),
            "low": min(x["low"] for x in group),
            "close": group[-1]["close"],
        })
    return output


def _structure(bars: list[dict], timeframe: str) -> dict:
    if len(bars) < MIN_DAILY_HISTORY:
        return {"status": "insufficient_evidence", "reason": "requires_10_bars",
                "bars": len(bars), "events": [], "score": None}
    events = []
    swings_high = []
    swings_low = []
    bias = "neutral"
    last_high = None
    last_low = None
    previous_close = None
    for i, bar in enumerate(bars):
        # A pivot at i-wing is confirmed only after its right-hand bars exist.
        pivot_index = i - PIVOT_WING
        if pivot_index >= PIVOT_WING:
            window = bars[pivot_index-PIVOT_WING:pivot_index+PIVOT_WING+1]
            pivot = bars[pivot_index]
            if pivot["high"] == max(x["high"] for x in window) and sum(x["high"] == pivot["high"] for x in window) == 1:
                last_high = {"price": pivot["high"], "pivot_session": pivot["session_date"],
                             "confirmed_session": bar["session_date"]}
                swings_high.append(last_high)
            if pivot["low"] == min(x["low"] for x in window) and sum(x["low"] == pivot["low"] for x in window) == 1:
                last_low = {"price": pivot["low"], "pivot_session": pivot["session_date"],
                            "confirmed_session": bar["session_date"]}
                swings_low.append(last_low)

        if previous_close is not None and last_high and previous_close <= last_high["price"] < bar["close"]:
            kind = "bos" if bias in ("bullish", "neutral") else "choch"
            events.append({"event": kind, "direction": "bullish", "timeframe": timeframe,
                           "session_date": bar["session_date"], "level": round(last_high["price"], 4),
                           "pivot_session": last_high["pivot_session"],
                           "confirmation": "close crossed above latest confirmed swing high"})
            bias = "bullish"
        if previous_close is not None and last_low and previous_close >= last_low["price"] > bar["close"]:
            kind = "bos" if bias in ("bearish", "neutral") else "choch"
            events.append({"event": kind, "direction": "bearish", "timeframe": timeframe,
                           "session_date": bar["session_date"], "level": round(last_low["price"], 4),
                           "pivot_session": last_low["pivot_session"],
                           "confirmation": "close crossed below latest confirmed swing low"})
            bias = "bearish"
        previous_close = bar["close"]

    # Current dealing range from the latest confirmed swing high/low pair.
    dealing_range = None
    location = "unavailable"
    if last_high and last_low and last_high["price"] > last_low["price"]:
        low, high = last_low["price"], last_high["price"]
        midpoint = (low + high) / 2
        close = bars[-1]["close"]
        location = "discount" if close < midpoint else "premium" if close > midpoint else "equilibrium"
        dealing_range = {"low": round(low, 4), "high": round(high, 4),
                         "equilibrium": round(midpoint, 4), "close_location": location}

    return {"status": "observed", "bars": len(bars), "as_of_session": bars[-1]["session_date"],
            "structure_bias": bias, "latest_confirmed_swing_high": last_high,
            "latest_confirmed_swing_low": last_low, "dealing_range": dealing_range,
            "events": events[-20:], "score": None,
            "score_note": "SMC directional score withheld pending calibrated confluence mapping"}


def smc_features(rows: list[dict]) -> dict:
    bars = _validate(rows)
    if len(bars) < MIN_DAILY_HISTORY:
        return {"status": "insufficient_evidence", "reason": "requires_10_valid_ohlc_sessions",
                "history_sessions": len(bars), "timeframes": {}, "fvg": [], "liquidity_sweeps": [],
                "score": None}
    daily = _structure(bars, "daily")

    # Fair Value Gaps: three-bar imbalance; track mitigation through current as-of bar.
    gaps = []
    for i in range(2, len(bars)):
        first, middle, current = bars[i-2], bars[i-1], bars[i]
        if current["low"] > first["high"]:
            low, high, direction = first["high"], current["low"], "bullish"
        elif current["high"] < first["low"]:
            low, high, direction = current["high"], first["low"], "bearish"
        else:
            continue
        mitigated = any(
            later["low"] <= high and later["high"] >= low
            for later in bars[i+1:]
        )
        gaps.append({"direction": direction, "formed_session": current["session_date"],
                     "lower": round(low, 4), "upper": round(high, 4),
                     "status": "mitigated" if mitigated else "open",
                     "mitigation_rule": "subsequent bar range overlaps the gap"})
    gaps = gaps[-20:]

    # Liquidity sweeps use only previously confirmed pivot levels.
    sweeps = []
    for i in range(PIVOT_WING * 2 + 1, len(bars)):
        history = bars[:i]
        pivot_highs = []
        pivot_lows = []
        for p in range(PIVOT_WING, len(history) - PIVOT_WING):
            window = history[p-PIVOT_WING:p+PIVOT_WING+1]
            if history[p]["high"] == max(x["high"] for x in window) and sum(x["high"] == history[p]["high"] for x in window) == 1:
                pivot_highs.append(history[p]["high"])
            if history[p]["low"] == min(x["low"] for x in window) and sum(x["low"] == history[p]["low"] for x in window) == 1:
                pivot_lows.append(history[p]["low"])
        bar = bars[i]
        if pivot_highs and bar["high"] > pivot_highs[-1] and bar["close"] < pivot_highs[-1]:
            sweeps.append({"event": "buy_side_liquidity_sweep", "session_date": bar["session_date"],
                           "level": round(pivot_highs[-1], 4), "status": "candidate",
                           "invalidation": "subsequent close above swept level"})
        if pivot_lows and bar["low"] < pivot_lows[-1] and bar["close"] > pivot_lows[-1]:
            sweeps.append({"event": "sell_side_liquidity_sweep", "session_date": bar["session_date"],
                           "level": round(pivot_lows[-1], 4), "status": "candidate",
                           "invalidation": "subsequent close below swept level"})

    bullish_structure = sum(1 for event in daily["events"] if event["direction"] == "bullish")
    bearish_structure = sum(1 for event in daily["events"] if event["direction"] == "bearish")
    bullish_sweeps = sum(1 for event in sweeps if event["event"] == "sell_side_liquidity_sweep")
    bearish_sweeps = sum(1 for event in sweeps if event["event"] == "buy_side_liquidity_sweep")
    bullish_gaps = sum(1 for gap in gaps if gap["direction"] == "bullish" and gap["status"] == "open")
    bearish_gaps = sum(1 for gap in gaps if gap["direction"] == "bearish" and gap["status"] == "open")
    # Explicit uncalibrated evidence heuristic; not a probability or trade signal.
    directional_balance = (bullish_structure - bearish_structure) * 8 + (bullish_sweeps - bearish_sweeps) * 5 + (bullish_gaps - bearish_gaps) * 2
    evidence_score = max(0, min(100, 50 + directional_balance))
    weekly_bars = _aggregate(bars, "weekly")
    monthly_bars = _aggregate(bars, "monthly")
    return {
        "status": "observed", "as_of_session": bars[-1]["session_date"],
        "history_sessions": len(bars),
        "timeframes": {
            "daily": daily,
            "weekly": {**_structure(weekly_bars, "weekly"),
                       "period_note": "latest calendar week excluded as potentially incomplete"},
            "monthly": {**_structure(monthly_bars, "monthly"),
                        "period_note": "latest calendar month excluded as potentially incomplete"},
        },
        "fvg": gaps, "liquidity_sweeps": sweeps[-20:],
        "premium_discount": daily.get("dealing_range"),
        "score": evidence_score,
        "score_note": "uncalibrated directional evidence heuristic from daily structure, liquidity sweeps and open FVG; not a probability or standalone signal",
        "evidence_counts": {"bullish_structure": bullish_structure, "bearish_structure": bearish_structure,
                            "bullish_sweeps": bullish_sweeps, "bearish_sweeps": bearish_sweeps,
                            "bullish_open_fvg": bullish_gaps, "bearish_open_fvg": bearish_gaps},
        "limitations": [
            "Pivots require two right-hand bars and are timestamped only when confirmed",
            "Weekly and monthly analysis excludes the latest calendar bucket to avoid partial-period confirmation",
            "FVG and liquidity sweep labels are mechanical candidates, not proof of institutional orders",
            "No broker footprint, order book, or execution data is inferred",
        ],
    }
