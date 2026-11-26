"""Causal OHLC zone lifecycle observations; no execution or production signals."""
from .scanner import quality_errors
from .market_structure import detect_structure

def zone_lifecycle(rows, *, eligible=False):
    base = {"status": "unavailable", "zones": [], "production_score": None, "action": "NO TRADE"}
    if not eligible:
        return dict(base, reason="eligibility_unverified")
    errors = quality_errors(rows)
    if errors or not rows:
        return dict(base, reason="invalid_or_empty_history", errors=errors)
    bars = sorted(rows, key=lambda r: str(r["date"]))
    events = detect_structure(bars)["events"]
    by_date = {}
    for event in events:
        if event["type"] in ("fvg", "order_block"):
            by_date.setdefault(event["date"], []).append(event)
    zones = {}
    for bar in bars:
        day = str(bar["date"])
        lo, hi, close = (float(bar[k]) for k in ("low", "high", "close"))
        for z in zones.values():
            if z["state"] == "invalidated":
                continue
            lower, upper = z["lower"], z["upper"]
            bullish = z["direction"] == "bullish"
            invalid = close < lower if bullish else close > upper
            if invalid:
                z["state"] = "invalidated"
                z["invalidated_date"] = day
                z["history"].append({"date": day, "state": "invalidated"})
                continue
            if hi < lower or lo > upper:
                continue
            width = upper - lower
            fraction = (upper - lo if bullish else hi - lower) / width if width > 0 else 1.0
            fraction = max(0.0, min(1.0, fraction))
            z["touch_count"] += 1
            if z["first_touch_date"] is None:
                z["first_touch_date"] = day
            z["last_touch_date"] = day
            z["max_penetration"] = max(z["max_penetration"], fraction)
            state = ("fully_mitigated" if z["max_penetration"] >= 1 else
                     "partially_mitigated" if z["max_penetration"] > 0 else "touched")
            if state != z["state"]:
                z["state"] = state
                z["history"].append({"date": day, "state": state})
        for e in by_date.get(day, []):
            zones[e["zone_id"]] = {
                "zone_id": e["zone_id"], "zone_type": e["type"], "direction": e["direction"],
                "lower": e["lower"], "upper": e["upper"], "formed_date": day,
                "state": "untested", "touch_count": 0, "max_penetration": 0.0,
                "first_touch_date": None, "last_touch_date": None, "invalidated_date": None,
                "history": [{"date": day, "state": "untested"}],
            }
    return dict(base, status="research_only", as_of=str(bars[-1]["date"]),
                zones=list(zones.values()),
                limitations=["Penetration is a directional OHLC proxy, not proof of continuous fills.",
                             "Close invalidation takes precedence over same-bar mitigation.",
                             "Touch count measures observed overlapping bars, not distinct intraday visits."])
