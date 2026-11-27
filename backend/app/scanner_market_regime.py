"""Uncalibrated descriptive market and sector research."""
from decimal import Decimal
from .scanner_historical_evidence import validate_history

def regime(*,rows,sessions,decision_time,calendar_evidence):
    checked=validate_history(rows,sessions,"NEPSE",decision_time,calendar_evidence)
    base=dict(regime="UNKNOWN",health_score=None,production_eligible=False)
    if not checked.get("rows") or len(rows)<61: return base
    ordered=sorted(rows,key=lambda r:r["date"])
    c=[Decimal(str(r["close"])) for r in ordered]
    if any(not x.is_finite() or x<=0 for x in c): raise ValueError("invalid_close")
    r20=c[-1]/c[-21]-1; r60=c[-1]/c[-61]-1
    sma=sum(c[-20:])/20
    label="MARKUP_PROXY" if r20>0 and r60>0 and c[-1]>sma else "MARKDOWN_PROXY" if r20<0 and r60<0 and c[-1]<sma else "CORRECTION_PROXY" if r60>0 and r20<0 else "MIXED"
    return dict(base,regime=label,return20=float(r20),return60=float(r60),limitations=["Index trend only; breadth, turnover and accumulation/distribution evidence not established."])

def rotation_proxy(sector_closes,index_closes):
    if len(sector_closes)!=len(index_closes) or len(index_closes)<41: return dict(status="UNKNOWN",quadrant=None)
    s,b=([Decimal(str(v)) for v in seq] for seq in (sector_closes,index_closes))
    if any(not x.is_finite() or x<=0 for x in s+b): raise ValueError("invalid_close")
    rs=[x/y for x,y in zip(s,b)]
    current=rs[-1]/rs[-21]-1; previous=rs[-21]/rs[-41]-1
    momentum=current-previous
    quadrant="LEADING" if current>0 and momentum>0 else "WEAKENING" if current>0 else "IMPROVING" if momentum>0 else "LAGGING"
    return dict(status="RESEARCH",quadrant=quadrant,relative_return=float(current),relative_momentum=float(momentum),production_eligible=False,limitations=["Aligned caller supplied closes; not proprietary RRG RS-Ratio or RS-Momentum."])
