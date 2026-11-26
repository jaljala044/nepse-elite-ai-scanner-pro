from statistics import mean
from math import isfinite
from datetime import date, datetime

def quality_errors(rows: list[dict]) -> list[str]:
    """Structural validation only; does not certify provenance or session eligibility."""
    errors = []
    seen = set()
    for i, row in enumerate(rows):
        try:
            d = row["date"]
            if isinstance(d, datetime):
                raise ValueError("expected session date")
            if not isinstance(d, date):
                d = date.fromisoformat(d)
            if d in seen:
                errors.append(f"duplicate_date:{d}")
            seen.add(d)
            o, h, l, c, v = (float(row[k]) for k in ("open", "high", "low", "close", "volume"))
            if not all(isfinite(x) for x in (o, h, l, c, v)) or min(o,h,l,c) <= 0 or v < 0 or not v.is_integer() or h < max(o,l,c) or l > min(o,h,c):
                errors.append(f"invalid_ohlcv:{i}")
        except (KeyError, ValueError, TypeError, OverflowError):
            errors.append(f"malformed_row:{i}")
    return errors


def analyze(symbol: str, rows: list[dict]) -> dict:
    errors = quality_errors(rows)
    if errors:
        return {"symbol": symbol, "observations": len(rows), "status": "data_quality_failed", "as_of": None, "signals": [], "metrics": {}, "limitations": errors}
    rows = sorted(rows, key=lambda x: str(x["date"]))
    base = {"symbol": symbol, "observations": len(rows), "status": "insufficient_data",
            "as_of": str(rows[-1]["date"]) if rows else None,
            "signals": [], "metrics": {}, "limitations": []}
    if len(rows) < 21:
        base["limitations"].append("At least 21 daily observations are required for this basic screen.")
        return base
    closes = [float(r["close"]) for r in rows]
    vols = [float(r["volume"]) for r in rows]
    last = rows[-1]
    sma20 = mean(closes[-20:])
    avgvol20 = mean(vols[-20:])
    change20 = (closes[-1] / closes[-21] - 1) * 100 if closes[-21] else None
    base["metrics"] = {"close": closes[-1], "sma20": round(sma20, 4),
                       "change_20_sessions_pct": round(change20, 2),
                       "volume_vs_20sma": round(vols[-1] / avgvol20, 2) if avgvol20 else None}
    if closes[-1] > sma20:
        base["signals"].append("close_above_sma20")
    else:
        base["signals"].append("close_below_sma20")
    if avgvol20 and vols[-1] > 1.5 * avgvol20:
        base["signals"].append("volume_expansion_vs_20sma")
    base["status"] = "screened"
    base["limitations"].append("Structural checks only; session, source and point-in-time eligibility are not certified.")
    base["limitations"].extend([
        "This is a basic OHLCV screen, not proof of accumulation, distribution, manipulation, or institutional activity.",
        "No broker identity, floorsheet, order-book, corporate-action, or verified live-feed data is incorporated."
    ])
    return base
