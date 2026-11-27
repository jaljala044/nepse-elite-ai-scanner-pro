"""Hypothetical delayed exit references, not exchange fills."""
from decimal import Decimal
from .scanner_settlement_risk import review_locked_stop

def delayed_exit_reference(*,entry_date,entry_price,stop,rows,sessions,assessment_time,price_bands):
    risk=review_locked_stop(entry_date=entry_date,entry_price=entry_price,stop=stop,rows=rows,sessions=sessions,assessment_time=assessment_time)
    result=dict(risk,exit_reference=None,exit_reference_date=None,locked_sessions=[])
    if not risk.get("subsequent_session_breaches"):
        return dict(result,exit_status="CONFIRMED_SUBSEQUENT_BREACH_REQUIRED")
    by_day={r["date"]:r for r in rows}
    for day in sessions:
        if day<risk["settlement_date"]: continue
        if day not in by_day or day not in price_bands: return dict(result,exit_status="MISSING_EVIDENCE")
        r=by_day[day]; band=price_bands[day]
        o,h,l,c,volume=(Decimal(str(r[k])) for k in ("open","high","low","close","volume"))
        lower,upper=(Decimal(str(band[k])) for k in ("lower","upper"))
        if any(not v.is_finite() for v in (o,h,l,c,volume,lower,upper)) or not 0<lower<=l<=min(o,c)<=max(o,c)<=h<=upper or lower>=upper or volume<0: raise ValueError("invalid_execution_bar")
        if h==l==lower or volume==0:
            result["locked_sessions"].append(day); continue
        return dict(result,exit_status="HYPOTHETICAL_OPEN_REFERENCE",exit_reference=str(o),exit_reference_date=day,
            gross_return=str(o/Decimal(str(entry_price))-1))
    return dict(result,exit_status="NO_ELIGIBLE_REFERENCE")
