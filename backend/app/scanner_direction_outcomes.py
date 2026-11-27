"""Directional outcome research, not execution returns."""
from decimal import Decimal
from .scanner_common_cohort import METHODS
from .unified_portfolio_event_engine import _available
from .corporate_action_trade_plan import _time

def evaluate_directions(cohort,paths,assessment_time):
    cutoff=_time(assessment_time)
    counts={m:dict(correct=0,incorrect=0,withheld=0) for m in METHODS}
    last_end={}
    seen=set()
    for row in sorted(cohort["rows"],key=lambda r:r["key"][2]):
        symbol,horizon,decision=row["key"]; key=tuple(row["key"])
        if key in seen or _time(decision)>cutoff or set(row["reviews"])!=set(METHODS): raise ValueError("invalid_decision_cohort")
        seen.add(key)
        path=paths.get(key)
        valid=False
        if path:
            _available(path,cutoff,"outcome")
            start,end=_time(path["start_time"]),_time(path["end_time"])
            if path["symbol"]!=symbol or path["horizon"]!=horizon or not _time(decision)<start<end<=_time(path["available_at"]): raise ValueError("invalid_outcome_alignment")
            group=(symbol,horizon)
            if group not in last_end or start>last_end[group]:
                a,b=(Decimal(str(path[k])) for k in ("start_close","end_close"))
                if not all(v.is_finite() and v>0 for v in (a,b)): raise ValueError("invalid_close")
                actual="BULLISH" if b>a else "BEARISH" if b<a else "NEUTRAL"
                last_end[group]=end; valid=True
        for m in METHODS:
            d=row["reviews"][m]["direction"]
            if d not in ("BULLISH","BEARISH","NEUTRAL","UNKNOWN"): raise ValueError("invalid_direction")
            bucket="withheld" if not valid or d=="UNKNOWN" else "correct" if d==actual else "incorrect"
            counts[m][bucket]+=1
    for c in counts.values():
        n=c["correct"]+c["incorrect"]
        c["sample_size"]=n
        c["direction_accuracy"]=c["correct"]/n if n>=30 else None
    return dict(metrics=counts,production_eligible=False,winner=None,limitations=["Caller-attested outcome intervals; horizon length and price basis require independent validation. Direction accuracy is not trade win rate."])
