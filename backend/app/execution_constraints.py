"""Conservative ordinary-equity daily-bar exit scenarios, never confirmed fills."""
from datetime import date
from math import isfinite

def settlement_date(trade_day, verified_settlement_days):
    day=date.fromisoformat(str(trade_day))
    if day<date(2021,1,24) or verified_settlement_days is None:
        return None
    days=sorted({date.fromisoformat(str(d)) for d in verified_settlement_days if date.fromisoformat(str(d))>day})
    return days[1] if len(days)>=2 else None

def price_band(day, *, previous_close=None, preopen_reference=None, ordinary_session=False):
    day=date.fromisoformat(str(day))
    if not ordinary_session or not date(2021,1,24)<=day<=date(2026,11,26):
        return None
    revised=day>=date(2026,4,20)
    reference=preopen_reference if revised else previous_close
    if not isinstance(reference,(int,float)) or isinstance(reference,bool) or not isfinite(reference) or reference<=0:
        return None
    rate=.15 if revised else .10
    return {"lower":reference*(1-rate),"upper":reference*(1+rate),
            "reference":"preopen" if revised else "previous_close","rate":rate,
            "classification":"unrounded_reference"}

def exit_scenario(bar, *, stop, target, settled_before_session=False, band=None, eligible=False):
    result={"status":"unavailable","price":None,"classification":"hypothetical_not_fill"}
    if not eligible or not settled_before_session or band is None:
        return result
    values=[bar.get(k) for k in ("open","high","low","close","volume")]+[stop,target,band.get("lower"),band.get("upper")]
    if any(not isinstance(x,(int,float)) or isinstance(x,bool) or not isfinite(x) for x in values):
        return result
    o,h,l,c,v,s,t,blo,bhi=values
    if not (0<blo<=bhi and 0<l<=min(o,c)<=max(o,c)<=h and 0<s<t and v>0):
        return result
    if l<blo-1e-8 or h>bhi+1e-8:
        return dict(result,status="band_or_reference_mismatch")
    if l<=blo+1e-8 and l<=s:
        return dict(result,status="limit_down_execution_unverified")
    if o<=s:
        return dict(result,status="stop_gap_scenario",price=o)
    if o>=t:
        return dict(result,status="target_open_scenario",price=t)
    if l<=s:
        return dict(result,status="ambiguous_stop_first" if h>=t else "stop_scenario",price=s)
    if h>=t:
        return dict(result,status="target_scenario",price=t)
    return dict(result,status="no_exit")
