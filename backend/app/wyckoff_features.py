"""Point-in-time Wyckoff candidate events from validated OHLCV only.

Events are mechanical candidates, not claims about operator intent or a
confirmed Wyckoff campaign. Each bar is evaluated using prior bars only.
"""
from __future__ import annotations

from datetime import date
import math

MIN_HISTORY = 41
BASE_LOOKBACK = 40
LEVEL_LOOKBACK = 20
VOLUME_LOOKBACK = 20
BREAKOUT_VOLUME_RATIO = 1.5
SWEEP_VOLUME_RATIO = 1.2
RETEST_WINDOW = 10


def _normalise(rows: list[dict]) -> list[dict]:
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    required = ("session_date", "open", "high", "low", "close", "volume")
    seen = set()
    result = []
    for i, row in enumerate(sorted(rows, key=lambda x: str(x.get("session_date", "")))):
        if any(k not in row or row[k] is None for k in required):
            return []
        try:
            day = date.fromisoformat(str(row["session_date"])).isoformat()
            values = {k: float(row[k]) for k in required[1:]}
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
        result.append({"session_date": day, **values})
    return result


def _bar_metrics(current: dict, prior: list[dict]) -> dict:
    avg_volume = sum(x["volume"] for x in prior) / len(prior)
    spread = current["high"] - current["low"]
    clv = (current["close"] - current["low"]) / spread if spread > 0 else None
    return {
        "relative_volume": current["volume"] / avg_volume if avg_volume > 0 else None,
        "close_location_value": clv,
        "spread": spread,
    }


def wyckoff_event_features(rows: list[dict]) -> dict:
    """Return candidate events and a transparent directional evidence score.

    A minimum of 41 valid sessions is required. No future bars are used to
    confirm an event; events remain candidates until a later as-of run.
    """
    bars = _normalise(rows)
    if not bars:
        return {"status": "insufficient_evidence", "reason": "required_ohlcv_fields_missing",
                "score": None, "history_sessions": len(rows) if isinstance(rows, list) else 0,
                "events": [], "regime": "unclassified"}
    if len(bars) < MIN_HISTORY:
        return {"status": "insufficient_evidence", "reason": f"requires_{MIN_HISTORY}_sessions",
                "score": None, "history_sessions": len(bars), "events": [],
                "regime": "unclassified"}

    events = []
    recent_bull_break = None
    recent_bear_break = None
    bull_count = 0
    bear_count = 0
    for i in range(BASE_LOOKBACK, len(bars)):
        current = bars[i]
        prior20 = bars[max(0, i - LEVEL_LOOKBACK):i]
        prior40 = bars[i - BASE_LOOKBACK:i]
        metrics = _bar_metrics(current, prior20)
        relvol = metrics["relative_volume"]
        clv = metrics["close_location_value"]
        support = min(x["low"] for x in prior20)
        resistance = max(x["high"] for x in prior20)
        base_low = min(x["low"] for x in prior40)
        base_high = max(x["high"] for x in prior40)
        width_pct = (base_high / base_low - 1) * 100 if base_low > 0 else None

        def add(name: str, direction: str, level: float, confirmation: str,
                invalidation: str, strength: str = "candidate") -> None:
            nonlocal bull_count, bear_count
            events.append({
                "event": name, "direction": direction, "status": strength,
                "session_date": current["session_date"], "reference_level": round(level, 4),
                "close": current["close"], "relative_volume": round(relvol, 4) if relvol is not None else None,
                "close_location_value": round(clv, 4) if clv is not None else None,
                "confirmation_rule": confirmation, "invalidation_rule": invalidation,
                "evidence": {"prior_20_session_support": round(support, 4),
                             "prior_20_session_resistance": round(resistance, 4),
                             "prior_40_session_range_pct": round(width_pct, 4) if width_pct is not None else None},
            })
            if direction == "bullish":
                bull_count += 1
            elif direction == "bearish":
                bear_count += 1

        # Sweep-and-reclaim / sweep-and-reject candidates.
        if current["low"] < support and current["close"] > support and relvol is not None and relvol >= SWEEP_VOLUME_RATIO and clv is not None and clv >= 0.60:
            add("spring", "bullish", support, "sweeps prior support, closes back above; relative volume >=1.2 and CLV >=0.60",
                "subsequent close below swept support")
        if current["high"] > resistance and current["close"] < resistance and relvol is not None and relvol >= SWEEP_VOLUME_RATIO and clv is not None and clv <= 0.40:
            add("upthrust", "bearish", resistance, "sweeps prior resistance, closes back below; relative volume >=1.2 and CLV <=0.40",
                "subsequent close above swept resistance")

        # Sign-of-strength / sign-of-weakness breakout candidates.
        if current["close"] > resistance and relvol is not None and relvol >= BREAKOUT_VOLUME_RATIO and clv is not None and clv >= 0.70:
            add("sos", "bullish", resistance, "close above prior 20-session high; relative volume >=1.5 and CLV >=0.70",
                "subsequent close back below breakout level")
            add("jump_across_creek", "bullish", resistance, "SOS breakout through prior range resistance",
                "subsequent close back below Creek level")
            recent_bull_break = {"index": i, "level": resistance}
        if current["close"] < support and relvol is not None and relvol >= BREAKOUT_VOLUME_RATIO and clv is not None and clv <= 0.30:
            add("sow", "bearish", support, "close below prior 20-session low; relative volume >=1.5 and CLV <=0.30",
                "subsequent close back above breakdown level")
            recent_bear_break = {"index": i, "level": support}

        # Retests are only considered after an already-observed break.
        if recent_bull_break and 0 < i - recent_bull_break["index"] <= RETEST_WINDOW:
            level = recent_bull_break["level"]
            if current["low"] <= level * 1.01 and current["close"] >= level and relvol is not None and relvol <= 1.0:
                add("lps", "bullish", level, "post-SOS retest holds Creek with relative volume <=1.0",
                    "subsequent close below Creek level")
                add("backup_to_creek", "bullish", level, "post-JAC retest holds Creek with relative volume <=1.0",
                    "subsequent close below Creek level")
                recent_bull_break = None
        if recent_bear_break and 0 < i - recent_bear_break["index"] <= RETEST_WINDOW:
            level = recent_bear_break["level"]
            if current["high"] >= level * 0.99 and current["close"] <= level and relvol is not None and relvol <= 1.0:
                add("lpsy", "bearish", level, "post-SOW rally retest fails support with relative volume <=1.0",
                    "subsequent close above breakdown level")
                recent_bear_break = None

    last = bars[-1]
    window = bars[-BASE_LOOKBACK:]
    range_low = min(x["low"] for x in window)
    range_high = max(x["high"] for x in window)
    range_width = (range_high / range_low - 1) * 100
    up_volume = sum(x["volume"] for x in window if x["close"] >= x["open"])
    down_volume = sum(x["volume"] for x in window if x["close"] < x["open"])
    position = (last["close"] - range_low) / (range_high - range_low) if range_high > range_low else 0.5
    # Regime labels are deliberately qualified candidates, not confirmed phases.
    if range_width <= 25 and position >= 0.60 and up_volume > down_volume * 1.10:
        regime = "accumulation_candidate"
    elif range_width <= 25 and position <= 0.40 and down_volume > up_volume * 1.10:
        regime = "distribution_candidate"
    elif range_width <= 25 and position >= 0.60:
        regime = "re_accumulation_candidate"
    elif range_width <= 25 and position <= 0.40:
        regime = "re_distribution_candidate"
    else:
        regime = "range_or_trend_unclassified"

    # Transparent evidence balance; not a probability and not directly a BUY.
    score = max(0, min(100, 50 + 10 * (bull_count - bear_count)))
    return {
        "status": "observed", "as_of_session": last["session_date"],
        "history_sessions": len(bars), "base_lookback_sessions": BASE_LOOKBACK,
        "regime": regime, "regime_is_candidate": True,
        "range": {"low": round(range_low, 4), "high": round(range_high, 4),
                  "width_pct": round(range_width, 4), "close_position": round(position, 4)},
        "score": score, "bullish_event_count": bull_count, "bearish_event_count": bear_count,
        "events": events[-30:],
        "event_count_total": len(events),
        "score_note": "rules-based event evidence balance; not a probability or standalone trade signal",
        "limitations": ["Regime labels are candidate classifications, not confirmed Wyckoff phases",
                        "LPS/LPSY require a prior detected breakout within the retest window",
                        "Events are not forward-confirmed; re-run at a later as-of time for confirmation"],
    }
