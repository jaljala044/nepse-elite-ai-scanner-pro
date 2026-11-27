"""Caller-attested historical evidence gate; not an exchange data certification."""
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available

def validate_history(rows,sessions,symbol,decision_time,calendar_evidence):
    cutoff=_time(decision_time)
    _available(calendar_evidence,cutoff,"calendar")
    if not sessions or list(sessions)!=sorted(set(sessions)) or calendar_evidence.get("sessions")!=list(sessions):
        raise ValueError("calendar_mismatch")
    if any(d>cutoff.date().isoformat() for d in sessions): raise ValueError("future_session")
    by_day={}
    for r in rows:
        _available(r,cutoff,"bar")
        d=r["date"]
        if r["symbol"]!=symbol or d in by_day or d not in sessions: raise ValueError("invalid_history_identity")
        if _time(r["observed_at"])>_time(r["available_at"]): raise ValueError("invalid_observation_time")
        by_day[d]=r
    missing=[d for d in sessions if d not in by_day]
    return dict(status="UNKNOWN" if missing else "COMPLETE_CALLER_ATTESTED",missing_sessions=missing,
        rows=[] if missing else [by_day[d] for d in sessions],production_eligible=False)
