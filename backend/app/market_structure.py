"""Causal market-structure observations from completed daily OHLCV bars."""

from collections.abc import Mapping
from datetime import date, datetime
from math import isfinite

from .scanner import quality_errors


def detect_structure(rows: list[dict], pivot_width: int = 2, equal_tolerance: float = 0.005) -> dict:
    if isinstance(pivot_width, bool) or not isinstance(pivot_width, int) or pivot_width < 1:
        raise ValueError("pivot_width must be a positive integer")
    if not isfinite(equal_tolerance) or not 0 <= equal_tolerance <= 0.05:
        raise ValueError("equal_tolerance must be between 0 and 0.05")
    errors = quality_errors(rows)
    if errors:
        return {"status": "data_quality_failed", "bias": "neutral", "events": [], "limitations": errors}

    bars = sorted(rows, key=lambda row: date.fromisoformat(str(row["date"])))
    days = [date.fromisoformat(str(row["date"])).isoformat() for row in bars]
    events = []
    bias = "neutral"
    levels: dict[str, tuple[float, int, int]] = {}
    broken_levels = set()
    last_opposing: dict[str, int] = {}
    open_zones: dict[str, dict] = {}
    retested_zones = set()

    def emit(kind, day, evidence_dates, **details):
        events.append({
            "type": kind,
            "date": day,
            "evidence_dates": sorted(set(evidence_dates) | {day}),
            **details,
        })

    def create_zone(kind, direction, day, lower, upper, evidence_dates, **details):
        zone_id = f"{kind}:{direction}:{day}"
        bullish = direction == "bullish"
        zone = {
            "zone_id": zone_id,
            "zone_type": kind,
            "direction": direction,
            "lower": lower,
            "upper": upper,
            "formed_date": day,
            "invalidation": {"field": "close", "operator": "<" if bullish else ">",
                             "level": lower if bullish else upper},
        }
        open_zones[zone_id] = zone
        emit(kind, day, evidence_dates, **zone, **details)

    for i, row in enumerate(bars):
        day = days[i]
        opening, high, low, close = (float(row[k]) for k in ("open", "high", "low", "close"))

        # Process only previously known zones. With daily OHLC, invalidation
        # takes precedence over a same-session touch.
        for zone_id, zone in list(open_zones.items()):
            lower, upper = zone["lower"], zone["upper"]
            invalid = close < lower if zone["direction"] == "bullish" else close > upper
            if invalid:
                emit("zone_invalidated", day, [zone["formed_date"]], **zone, observed_close=close)
                del open_zones[zone_id]
                retested_zones.discard(zone_id)
            elif zone_id not in retested_zones and low <= upper and high >= lower:
                emit("zone_retest", day, [zone["formed_date"]], **zone,
                     observed_low=low, observed_high=high)
                retested_zones.add(zone_id)

        # A swing confirmed by the current bar is eligible to break only on
        # subsequent bars.
        for side, direction in (("high", "bullish"), ("low", "bearish")):
            level = levels.get(side)
            if level is None:
                continue
            price, pivot, confirmed = level
            key = (side, pivot)
            if key in broken_levels:
                continue
            bullish = direction == "bullish"
            crosses = close > price if bullish else close < price
            sweeps = high > price and close < price if bullish else low < price and close > price
            references = {
                "pivot_date": days[pivot],
                "pivot_confirmed_date": days[confirmed],
            }
            evidence_dates = list(references.values())
            if crosses:
                kind = "choch" if bias not in ("neutral", direction) else "bos"
                emit(kind, day, evidence_dates, direction=direction, level=price,
                     observed_close=close, **references)
                bias = direction
                broken_levels.add(key)
                origin = last_opposing.get(direction)
                if origin is not None and origin > pivot:
                    origin_row = bars[origin]
                    create_zone(
                        "order_block", direction, day,
                        float(origin_row["low"]), float(origin_row["high"]),
                        [*evidence_dates, days[origin]],
                        origin_date=days[origin], trigger=kind, trigger_level=price, **references,
                    )
            elif sweeps:
                emit("liquidity_sweep", day, evidence_dates, side=side, level=price,
                     observed_close=close, **references)

        if i >= 2:
            left_high, left_low = (float(bars[i - 2][k]) for k in ("high", "low"))
            evidence_dates = days[i - 2:i]
            if low > left_high:
                create_zone("fvg", "bullish", day, left_high, low, evidence_dates)
            elif high < left_low:
                create_zone("fvg", "bearish", day, high, left_low, evidence_dates)

        pivot = i - pivot_width
        if pivot >= pivot_width:
            window = bars[pivot - pivot_width:i + 1]
            for side in ("high", "low"):
                price = float(bars[pivot][side])
                neighbors = [float(bar[side]) for j, bar in enumerate(window) if j != pivot_width]
                if (price > max(neighbors) if side == "high" else price < min(neighbors)):
                    previous = levels.get(side)
                    if previous is not None:
                        old_price, old_pivot, old_confirmed = previous
                        if (side, old_pivot) not in broken_levels and abs(price-old_price)/max(price,old_price) <= equal_tolerance:
                            emit("equal_"+side+"s", day, [days[old_pivot],days[old_confirmed],*days[pivot-pivot_width:i+1]],
                                 lower=min(price,old_price),upper=max(price,old_price),
                                 liquidity_side="buy_side" if side=="high" else "sell_side",
                                 classification="inferred_chart_level")
                    levels[side] = (price, pivot, i)
                    emit(f"swing_{side}", day, days[pivot - pivot_width:i],
                         level=price, pivot_date=days[pivot])

        if close < opening:
            last_opposing["bullish"] = i
        elif close > opening:
            last_opposing["bearish"] = i

    dealing_range = None
    if bars and "high" in levels and "low" in levels:
        hi, hp, hc = levels["high"]
        lo, lp, lc = levels["low"]
        close = float(bars[-1]["close"])
        if hi > lo and ("high",hp) not in broken_levels and ("low",lp) not in broken_levels and lo <= close <= hi:
            mid = (hi+lo)/2
            dealing_range = {"lower":lo,"upper":hi,"equilibrium":mid,
                             "discount":[lo,mid],"premium":[mid,hi],
                             "location":"discount" if close<mid else "premium" if close>mid else "equilibrium",
                             "evidence_dates":sorted({days[hp],days[hc],days[lp],days[lc],days[-1]}),
                             "classification":"inferred_chart_range"}
    return {
        "dealing_range": dealing_range,
        "equal_tolerance": equal_tolerance,
        "status": "screened" if len(bars) >= 2 * pivot_width + 1 else "insufficient_data",
        "bias": bias,
        "events": events,
        "pivot_width": pivot_width,
        "limitations": [
            "Daily OHLCV observations are proxies for chart structure.",
            "Zone touches and invalidations use completed bars. Intraday order is unavailable.",
        ],
    }


def add_event_evidence(structure: dict, reviewed_rows: list[Mapping]) -> None:
    """Attach server-reviewed records and the earliest knowable prefix time."""
    indexed = {}
    latest = None
    for row in sorted(reviewed_rows, key=lambda item: item["date"]):
        timestamp = datetime.fromisoformat(row["available_at"].replace("Z", "+00:00"))
        latest = timestamp if latest is None else max(latest, timestamp)
        indexed[row["date"]] = (row, latest)
    for event in structure["events"]:
        event["available_at"] = indexed[event["date"]][1].isoformat()
        event["evidence"] = [
            {
                "date": day,
                "source_id": indexed[day][0]["source_id"],
                "evidence_id": indexed[day][0]["evidence_id"],
            }
            for day in event["evidence_dates"]
        ]
