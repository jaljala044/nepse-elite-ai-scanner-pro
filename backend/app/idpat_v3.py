"""IDPAT V3 integration foundation; not a verified implementation of proprietary rules."""
from statistics import mean
from .scanner import quality_errors

def research_features(rows):
    """Transparent daily OHLCV descriptors; no IDPAT score or recommendation."""
    errors = quality_errors(rows)
    if errors:
        return {"status": "data_quality_failed", "features": {}, "errors": errors}
    bars = sorted(rows, key=lambda r: str(r["date"]))
    if len(bars) < 21:
        return {"status": "insufficient_data", "features": {}, "errors": []}
    closes = [float(r["close"]) for r in bars]
    volumes = [float(r["volume"]) for r in bars]
    prior_volume = mean(volumes[-21:-1])
    sma = mean(closes[-20:])
    return {"status": "research_features_ready", "errors": [],
            "as_of": str(bars[-1]["date"]),
            "features": {"close": closes[-1], "sma20": sma,
                         "return20_pct": 100*(closes[-1]/closes[-21]-1),
                         "relative_volume20": volumes[-1]/prior_volume if prior_volume else None,
                         "close_vs_sma20_pct": 100*(closes[-1]/sma-1)}}

def evaluate_idpat_v3(rows, *, eligible=False):
    """Do not assign IDPAT labels until the original versioned specification is verified."""
    if not eligible:
        return {"status": "eligibility_unverified", "score": None, "signals": []}
    result = research_features(rows)
    return {"status": "specification_unverified" if result["status"] == "research_features_ready" else result["status"],
            "score": None, "signals": [], "research_features": result,
            "limitations": ["Original IDPAT V3.0 thresholds, rules and weights are not yet verified."]}
