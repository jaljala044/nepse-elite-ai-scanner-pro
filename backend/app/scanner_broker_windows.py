"""Fixed session-count research windows, not calendar-year or ownership claims."""
from decimal import Decimal
from .unified_portfolio_event_engine import _available
from .corporate_action_trade_plan import _time
WINDOWS={"1D":1,"1W":5,"1M":21,"3M":63,"6M":126,"1Y":252,"2Y":504}
def broker_windows(*,symbol,records,sessions,cohort,calendar_evidence,decision_time):
    cutoff=_time(decision_time)
    _available(calendar_evidence,cutoff,"calendar")
    if not sessions or sessions!=sorted(set(sessions)) or calendar_evidence["sessions"]!=sessions or sessions[-1]>cutoff.date().isoformat(): raise ValueError("invalid_calendar")
    if not cohort or any(type(i) is not int or i<=0 for i in cohort) or len(set(cohort))!=len(cohort): raise ValueError("invalid_cohort")
    by={}
    for r in records:
        _available(r,cutoff,"broker_day")
        day=r["session"]
        if day not in sessions or day in by or r["symbol"]!=symbol or sorted(r["broker_ids"])!=sorted(cohort): raise ValueError("invalid_broker_identity")
        if _time(r["available_at"]).date().isoformat()<day: raise ValueError("premature_daily_record")
        if r["coverage_complete"] is not True: continue
        b,s=(Decimal(str(r[k])) for k in ("buy_turnover","sell_turnover"))
        if any(not x.is_finite() or x<0 for x in (b,s)): raise ValueError("invalid_turnover")
        by[day]=(b,s,r["source_id"])
    result={}
    for name,n in WINDOWS.items():
        days=sessions[-n:]; missing=[d for d in days if d not in by]
        item=dict(required_sessions=n,covered_sessions=len(days)-len(missing),missing_sessions=missing,direction="UNKNOWN",imbalance=None)
        if len(days)==n and not missing:
            b=sum(by[d][0] for d in days); s=sum(by[d][1] for d in days)
            if b+s:
                ratio=(b-s)/(b+s)
                item.update(buy_turnover=str(b),sell_turnover=str(s),net_turnover=str(b-s),imbalance=float(ratio),direction="BUY_DOMINANT" if ratio>=Decimal(".2") else "SELL_DOMINANT" if ratio<=Decimal("-.2") else "NEUTRAL",source_ids=sorted({by[d][2] for d in days}))
        result[name]=item
    return dict(symbol=symbol,windows=result,production_eligible=False,limitations=["Fixed session-count approximations; caller-attested calendar and cohort; no ownership inference."])
