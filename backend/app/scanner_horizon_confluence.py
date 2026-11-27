"""Research horizon alignment, no executable recommendation."""
from .scanner_common_cohort import METHODS
HORIZONS=("T+2","swing","positional","investment")

def horizon_confluence(reviews):
    if set(reviews)!=set(HORIZONS): raise ValueError("four_horizons_required")
    if any(set(reviews[h])!=set(METHODS) for h in HORIZONS): raise ValueError("six_methods_required")
    result={}
    for method in METHODS:
        directions={h:reviews[h][method]["direction"] for h in HORIZONS}
        if any(v not in ("BULLISH","BEARISH","NEUTRAL","UNKNOWN") for v in directions.values()): raise ValueError("invalid_direction")
        gates={}
        for i,h in enumerate(HORIZONS):
            relevant=[directions[k] for k in HORIZONS[i:]]
            status="CONFLICT" if "BULLISH" in relevant and "BEARISH" in relevant else "UNKNOWN" if "UNKNOWN" in relevant else "ALIGNED" if len(set(relevant))==1 else "MIXED"
            gates[h]=dict(status=status,bullish_alignment=status=="ALIGNED" and directions[h]=="BULLISH",action="NO_TRADE")
        result[method]=dict(directions=directions,gates=gates)
    return dict(methods=result,production_eligible=False,score=None,limitations=["Horizon labels are not independent timeframe bars; no calibrated probabilities."])
