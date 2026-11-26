"""Experimental SMC confluence; not a validated production rating."""
from math import isfinite

WEIGHTS = {"structure":25,"sweep":20,"zone":20,"alignment":15,"position":10,"volume":10}

def evaluate_confluence(structure, timeframes, *, eligible=False):
    result = {"method":"smc_experimental_v1","score":None,"coverage":0,
              "production_score":None,"components":{},"action":"NO TRADE"}
    if not eligible or structure.get("status")!="screened" or timeframes.get("status")!="research_only":
        return dict(result,status="unavailable")
    direction = timeframes.get("daily_bias")
    if direction not in ("bullish","bearish"):
        return dict(result,status="direction_unavailable")
    recent = timeframes.get("t_plus_2",{}).get("recent_events",[])
    events = structure.get("events",[])
    active = {}
    for event in events:
        key = event.get("zone_id")
        if event["type"] in ("order_block","fvg") and key:
            active[key] = event
        elif event["type"]=="zone_invalidated":
            active.pop(key,None)
    rv = timeframes.get("t_plus_2",{}).get("relative_volume")
    location = (structure.get("dealing_range") or {}).get("location")
    alignment = timeframes.get("alignment")
    values = {
        "structure": any(e["type"] in ("bos","choch") and e.get("direction")==direction for e in recent),
        "sweep": any(e["type"]=="liquidity_sweep" and e.get("side")==("low" if direction=="bullish" else "high") for e in recent),
        "zone": any(e.get("direction")==direction and e.get("zone_id") in active for e in recent if e["type"]=="zone_retest"),
        "alignment": alignment=="aligned" if alignment in ("aligned","conflicting") else None,
        "position": location==("discount" if direction=="bullish" else "premium") if location in ("discount","premium","equilibrium") else None,
        "volume": rv>=1.5 if isinstance(rv,(int,float)) and isfinite(rv) and rv>=0 else None,
    }
    result["components"] = {k:{"weight":w,"met":values[k]} for k,w in WEIGHTS.items()}
    result["coverage"] = sum(w for k,w in WEIGHTS.items() if values[k] is not None)
    result["direction"] = direction
    result["missing"] = [k for k,v in values.items() if v is None]
    result["status"] = "incomplete" if result["missing"] else "experimental_only"
    if not result["missing"]:
        result["score"] = sum(w for k,w in WEIGHTS.items() if values[k])
    return result
