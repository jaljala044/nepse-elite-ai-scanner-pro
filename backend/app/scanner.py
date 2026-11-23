from statistics import mean

def analyze(symbol: str, rows: list[dict]) -> dict:
    rows = sorted(rows, key=lambda x: x["date"])
    base = {"symbol": symbol, "observations": len(rows), "status": "insufficient_data",
            "as_of": str(rows[-1]["date"]) if rows else None,
            "signals": [], "metrics": {}, "limitations": []}
    if len(rows) < 21:
        base["limitations"].append("At least 21 daily observations are required for this basic screen.")
        return base
    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]
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
    base["limitations"].extend([
        "This is a basic OHLCV screen, not proof of accumulation, distribution, manipulation, or institutional activity.",
        "No broker identity, floorsheet, order-book, corporate-action, or verified live-feed data is incorporated."
    ])
    return base
