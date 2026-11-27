"""Daily-bar settlement risk diagnostics, not an exit fill simulator."""
from decimal import Decimal
from datetime import date
from .execution_constraints import settlement_date
from .unified_portfolio_event_engine import _available
from .corporate_action_trade_plan import _time

def review_locked_stop(*,entry_date,entry_price,stop,rows,sessions,assessment_time):
    entry,stop=Decimal(str(entry_price)),Decimal(str(stop))
    if not entry.is_finite() or not stop.is_finite() or not 0<stop<entry: raise ValueError("invalid_plan")
    days=list(sessions)
    if days!=sorted(set(days)) or entry_date not in days: raise ValueError("invalid_sessions")
    eligible=settlement_date(entry_date,days)
    base=dict(production_eligible=False,exit_fill=None,settlement_date=str(eligible) if eligible else None)
    if eligible is None: return dict(base,status="UNKNOWN")
    by_day={}
    for r in rows:
        _available(r,_time(assessment_time),"bar")
        day=r["date"]
        if day in by_day or day not in days: raise ValueError("invalid_bar_date")
        low,close=Decimal(str(r["low"])),Decimal(str(r["close"]))
        if not low.is_finite() or not close.is_finite() or not 0<low<=close: raise ValueError("invalid_bar")
        by_day[day]=(low,close)
    locked=[d for d in days if entry_date<=d<str(eligible)]
    if any(d not in by_day for d in locked): return dict(base,status="UNKNOWN")
    breaches=[d for d in locked if by_day[d][0]<=stop]
    # Entry-day low may precede the purchase; do not assert a post-entry breach.
    confirmed=[d for d in breaches if d!=entry_date]
    return dict(base,status="LOCKED_STOP_RISK" if breaches else "NO_OBSERVED_LOCKED_BREACH",
        possible_breach_dates=breaches,subsequent_session_breaches=confirmed,
        eligible_session_close=str(by_day[str(eligible)][1]) if str(eligible) in by_day else None,
        limitations=["Entry-day sequence unknown; calendar caller supplied; eligibility does not guarantee execution."])
