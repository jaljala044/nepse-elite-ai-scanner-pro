"""Causal daily OHLC market-structure observations; not order-book evidence."""
from .scanner import quality_errors


def detect_structure(rows, pivot_width=2):
    if isinstance(pivot_width, bool) or not isinstance(pivot_width, int) or pivot_width < 1:
        raise ValueError("pivot_width must be a positive integer")
    errors = quality_errors(rows)
    if errors:
        return {"status": "data_quality_failed", "bias": "neutral", "events": [], "limitations": errors}
    bars = sorted(rows, key=lambda r: str(r["date"]))
    events = []
    bias = "neutral"
    levels = {"high": None, "low": None}
    broken = set()
    def emit(kind, i, **details):
        events.append({"type": kind, "date": str(bars[i]["date"]), **details})
    for i, row in enumerate(bars):
        h, l, c = (float(row[k]) for k in ("high", "low", "close"))
        # Evaluate existing levels before confirming any new pivot.
        for side, direction in (("high", "bullish"), ("low", "bearish")):
            level = levels[side]
            if level is None:
                continue
            price, pivot = level
            key = (side, pivot)
            if key in broken:
                continue
            crosses = c > price if side == "high" else c < price
            sweeps = h > price and c < price if side == "high" else l < price and c > price
            if crosses:
                kind = "choch" if bias not in ("neutral", direction) else "bos"
                emit(kind, i, direction=direction, level=price, pivot_date=str(bars[pivot]["date"]))
                bias = direction
                broken.add(key)
            elif sweeps:
                emit("liquidity_sweep", i, side=side, level=price, pivot_date=str(bars[pivot]["date"]))
        if i >= 2:
            left = bars[i-2]
            if l > float(left["high"]):
                emit("fvg", i, direction="bullish", lower=float(left["high"]), upper=l)
            if h < float(left["low"]):
                emit("fvg", i, direction="bearish", lower=h, upper=float(left["low"]))
        p = i - pivot_width
        if p >= pivot_width:
            window = bars[p-pivot_width:i+1]
            for side in ("high", "low"):
                price = float(bars[p][side])
                others = [float(x[side]) for j,x in enumerate(window) if j != pivot_width]
                if (price > max(others) if side == "high" else price < min(others)):
                    levels[side] = (price, p)
                    emit("swing_"+side, i, level=price, pivot_date=str(bars[p]["date"]))
    return {"status": "screened" if len(bars) >= 2*pivot_width+1 else "insufficient_data",
            "bias": bias, "events": events, "pivot_width": pivot_width,
            "limitations": ["Daily OHLC proxies only; no institutional flow or actual liquidity inference.",
                            "Calendar, corporate-action, provenance and point-in-time eligibility require separate validation."]}
