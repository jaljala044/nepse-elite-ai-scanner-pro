"""Research-only ICT-style dealing ranges; not authenticated IPDA or order-book liquidity."""
from .scanner import quality_errors
from .market_structure import detect_structure

LOOKBACKS = (20, 40, 60)

def ipda_ranges(rows, *, eligible=False):
    result = {"status": "unavailable", "windows": {}, "production_score": None,
              "action": "NO TRADE", "method": "ipda_style_research_v1"}
    if not eligible:
        return dict(result, reason="eligibility_unverified")
    errors = quality_errors(rows)
    if errors or not rows:
        return dict(result, reason="invalid_or_empty_history", errors=errors)
    bars = sorted(rows, key=lambda r: str(r["date"]))
    events = detect_structure(bars)["events"]
    active = {}
    for event in events:
        key = event.get("zone_id")
        if event["type"] in ("fvg", "order_block") and key:
            active[key] = dict(event, lifecycle="untested")
        elif event["type"] == "zone_invalidated":
            active.pop(key, None)
        elif event["type"] == "zone_retest" and key in active:
            active[key]["lifecycle"] = "touched"
    close = float(bars[-1]["close"])
    for n in LOOKBACKS:
        if len(bars) < n:
            result["windows"][str(n)] = {"status": "insufficient_history", "required": n}
            continue
        window = bars[-n:]
        start = str(window[0]["date"])
        low = min(float(r["low"]) for r in window)
        high = max(float(r["high"]) for r in window)
        mid = (low + high) / 2
        result["windows"][str(n)] = {
            "status": "observed", "start": start, "end": str(window[-1]["date"]),
            "observations": n, "low": low, "high": high, "equilibrium": mid,
            "location": "discount" if close < mid else "premium" if close > mid else "equilibrium",
            "zones": [z for z in active.values() if z["date"] >= start],
            "liquidity_candidates": [e for e in events if e["date"] >= start and e["type"] in
                                     ("equal_highs", "equal_lows", "liquidity_sweep", "swing_high", "swing_low")],
        }
    return dict(result, status="research_only", as_of=str(bars[-1]["date"]),
                limitations=["Observed bars, not certified contiguous exchange sessions.",
                             "Chart levels are inferred, not verified orders.",
                             "Zone touch does not establish full mitigation.",
                             "No predictive calibration or production recommendation."])
