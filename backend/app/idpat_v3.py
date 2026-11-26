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


def evaluate_provisional(rows, *, eligible=False, volume_threshold=1.5, weights=(25,25,25,25)):
    """Experimental rule score, not original IDPAT V3 or probability of profit."""
    from math import isfinite
    if not isfinite(volume_threshold) or volume_threshold <= 0 or len(weights) != 4 or any(not isfinite(w) or w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("invalid provisional configuration")
    base = {"method": "nepse_provisional_v1", "score": None, "signals": [],
            "limitations": ["Experimental thresholds; not original IDPAT V3.0, not backtested.",
                            "Daily OHLCV proxies; no institutional-flow inference."]}
    if not eligible:
        return dict(base, status="eligibility_unverified")
    result = research_features(rows)
    if result["status"] != "research_features_ready":
        return dict(base, status=result["status"])
    bars = sorted(rows,key=lambda r:str(r["date"]))
    f = result["features"]
    prior = bars[-21:-1]
    resistance = max(float(r["high"]) for r in prior)
    support = min(float(r["low"]) for r in prior)
    rv = f["relative_volume20"]
    checks = {"trend": f["close"] > f["sma20"],
              "momentum": f["return20_pct"] > 0,
              "volume": rv is not None and rv >= volume_threshold,
              "range_breakout": f["close"] > resistance}
    components = [{"rule": name,"passed": passed,"weight": w,
                   "points": w if passed else 0} for (name,passed),w in zip(checks.items(),weights)]
    sweep = float(bars[-1]["low"]) < support and f["close"] > support
    return dict(base,status="research_scored",as_of=result["as_of"],
                score=round(100*sum(x["points"] for x in components)/sum(weights),2),
                components=components,features=f,
                signals=[k for k,v in checks.items() if v],
                context={"prior20_high":resistance,"prior20_low":support,
                         "range_low_sweep_proxy":sweep,
                         "invalidation_reference":support},
                configuration={"volume_threshold":volume_threshold,"weights":list(weights)})
