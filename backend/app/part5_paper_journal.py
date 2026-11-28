"""Content-addressed paper trade journal envelopes; persistence is separate."""
import hashlib
import json
from .point_in_time import _aware
from .signal_tracking import verify_signal, HORIZONS

def freeze_paper_outcome(signal, trade, *, observed_at):
    if not verify_signal(signal):
        raise ValueError("invalid frozen signal")
    original=signal["record"]
    if original.get("classification")!="research_only" or original.get("action")!="NO TRADE":
        raise ValueError("research-only source required")
    observed=_aware(observed_at)
    if observed<_aware(original["decision_time"]):
        raise ValueError("outcome predates signal")
    if trade.get("horizon")!=original["horizon"] or trade.get("horizon") not in HORIZONS:
        raise ValueError("horizon mismatch")
    if trade.get("status") not in ("closed_scenario","open_unresolved"):
        raise ValueError("invalid paper status")
    if trade.get("status")=="closed_scenario":
        from math import isfinite
        pnl=trade.get("net_pnl")
        if isinstance(pnl,bool) or not isinstance(pnl,(int,float)) or not isfinite(pnl):
            raise ValueError("invalid hypothetical PnL")
    record={"signal_id":signal["signal_id"],"symbol":original["symbol"],
            "methodology":original["methodology"],"observed_at":observed.isoformat(),
            "trade":trade,"classification":"hypothetical_paper_trade",
            "production_eligible":False}
    encoded=json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False)
    return {"paper_id":hashlib.sha256(encoded.encode()).hexdigest(),"record":json.loads(encoded)}

def verify_paper_outcome(envelope):
    try:
        encoded=json.dumps(envelope["record"],sort_keys=True,separators=(",",":"),allow_nan=False)
        return hashlib.sha256(encoded.encode()).hexdigest()==envelope["paper_id"]
    except (KeyError,TypeError,ValueError):
        return False
