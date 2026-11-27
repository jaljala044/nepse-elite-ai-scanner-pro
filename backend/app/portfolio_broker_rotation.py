"""Descriptive rotation using existing append-only broker memory."""
from collections import defaultdict
from decimal import Decimal
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _day
from .corporate_action_risk import _amount

def compare_stored_sector_flow(*, store, broker_entity_id, previous_sessions,
                               current_sessions, sector_by_security, assessment_time):
    now = _time(assessment_time)
    old = [_day(d,"session") for d in previous_sessions]
    new = [_day(d,"session") for d in current_sessions]
    if not old or not new or len(old)!=len(new) or old!=sorted(set(old)) or new!=sorted(set(new)) or old[-1]>=new[0] or new[-1]>now.date():
        raise ValueError("invalid_comparison_windows")
    if not sector_by_security or not all(sector_by_security.values()):
        raise ValueError("security_sector_mapping_required")
    totals=defaultdict(lambda:[Decimal(0),Decimal(0)])
    seen=0
    expected=len(sector_by_security)*(len(old)+len(new))
    for security,sector in sorted(sector_by_security.items()):
        rows=store.get_as_of(security_id=security,broker_entity_id=broker_entity_id,
                             as_of_date=new[-1].isoformat(),available_by=now)
        daily={}
        for row in rows:
            snap=row.get("snapshot",row)
            if snap.get("window")!="daily": continue
            day=_day(snap["as_of_date"],"session")
            if day not in old+new: continue
            if day in daily: raise ValueError("ambiguous_daily_snapshot")
            daily[day]=snap
        for day,snap in daily.items():
            buy,sell=_amount(snap["buy_amount"],"buy"),_amount(snap["sell_amount"],"sell")
            pair=totals[(sector,0 if day in old else 1)]
            pair[0]+=buy
            pair[1]+=sell
            seen+=1
    if seen!=expected:
        return dict(status="UNKNOWN",coverage=seen/expected,sectors=[],execution_eligible=False)
    sectors=[]
    for sector in sorted(set(sector_by_security.values())):
        a,b=totals[(sector,0)],totals[(sector,1)]
        x=(a[0]-a[1])/sum(a) if sum(a) else None
        y=(b[0]-b[1])/sum(b) if sum(b) else None
        sectors.append(dict(sector=sector,previous_net=float(a[0]-a[1]),current_net=float(b[0]-b[1]),
                            imbalance_change=None if x is None or y is None else float(y-x)))
    return dict(status="RESEARCH_ONLY",coverage=1,sectors=sectors,execution_eligible=False,
                limitations=["Flow changes do not establish actual capital transfers.",
                             "Caller-defined universe and calendar; no independent completeness proof."])
