"""Retry unresolved fixed-horizon exits without inventing a fill."""
from .execution_constraints import exit_scenario
from datetime import date

def retry_exit(sessions, bars, bands, *, settled_on, deadline, stop, target, pending_stop=False):
    """Caller supplies controls; unavailable sessions preserve pending exit intent."""
    if sessions!=sorted(set(sessions)):
        raise ValueError("invalid session order")
    settled=date.fromisoformat(str(settled_on))
    due=date.fromisoformat(str(deadline))
    attempts=[]
    for day in sessions:
        d=date.fromisoformat(day)
        bar=bars.get(day)
        if d<=settled:
            if bar is not None and float(bar["low"])<=stop:
                pending_stop=True
            continue
        if bar is None or day not in bands:
            attempts.append({"date":day,"status":"missing_evidence"})
            continue
        if pending_stop or d>=due:
            # A previously triggered exit uses the next eligible open, not the old stop.
            band=bands[day]
            op=float(bar["open"])
            if float(bar["volume"])>0 and band["lower"]<op<=band["upper"] and float(bar["low"])>=band["lower"]-1e-8 and float(bar["high"])<=band["upper"]+1e-8:
                return {"status":"closed_scenario","exit_date":day,"price":op,"attempts":attempts,
                        "classification":"hypothetical_not_fill"}
            attempts.append({"date":day,"status":"retry_execution_unverified"})
            continue
        result=exit_scenario(bar,stop=stop,target=target,settled_before_session=True,band=bands[day],eligible=True)
        if result["price"] is not None:
            return {**result,"status":"closed_scenario","exit_date":day,"attempts":attempts}
        if float(bar["low"])<=stop:
            pending_stop=True
        attempts.append({"date":day,"status":result["status"]})
    return {"status":"open_unresolved","price":None,"attempts":attempts,
            "pending_stop":pending_stop,"classification":"hypothetical_not_fill"}
