"""Experimental daily-bar breakout guard; no manipulation inference."""
from decimal import Decimal
from .scanner_historical_evidence import validate_history
from .execution_backtest import _d

def breakout_guard(*,symbol,rows,sessions,decision_time,calendar_evidence):
    checked=validate_history(rows,sessions,symbol,decision_time,calendar_evidence)
    base=dict(status="UNKNOWN",action="NO_TRADE",production_eligible=False)
    bars=checked["rows"]
    if len(bars)<23: return base
    values=[]
    for r in bars:
        o,h,l,c,v=(_d(r[k],k) for k in ("open","high","low","close","volume"))
        if not 0<l<=min(o,c)<=max(o,c)<=h or v<0: raise ValueError("invalid_bar")
        if r.get("price_basis")!="corporate_action_reviewed" or not r.get("basis_id"): return base
        values.append((o,h,l,c,v))
    if len({r["basis_id"] for r in bars})!=1: return base
    prior=values[-23:-3]
    resistance=max(r[1] for r in prior)
    avg=sum(r[4] for r in prior)/20
    if avg<=0: return base
    recent=values[-3:]
    breakout=next((i for i,r in enumerate(recent) if r[3]>resistance),None)
    rejection=any(r[1]>resistance and r[3]<resistance for r in recent)
    failed=breakout is not None and any(r[3]<resistance for r in recent[breakout+1:])
    ratio=recent[breakout][4]/avg if breakout is not None else None
    status="FAILED_BREAKOUT" if failed else "REJECTION_WARNING" if rejection else "NO_BREAKOUT" if breakout is None else "WEAK_VOLUME" if ratio<Decimal("1.5") else "RETEST_WATCH"
    return dict(base,status=status,resistance=str(resistance),breakout_volume_ratio=float(ratio) if ratio is not None else None,source_ids=[r["source_id"] for r in bars[-23:]],limitations=["Fixed prior twenty-session range; no intraday sequence, broker confirmation or calibrated probability."])
