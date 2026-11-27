"""Experimental project rules; no original IDPAT or executable signal claim."""
from decimal import Decimal
from .idpat_behavior_research import review_behavior
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available

def review_confluence(rows,assessment_time,broker=None):
    current=review_behavior(rows,assessment_time)
    if current["status"]=="UNKNOWN": return current
    history=[]
    for i in range(max(21,len(rows)-4),len(rows)+1):
        history.append(review_behavior(rows[:i],rows[i-1]["available_at"])["events"])
    lower=sum("LOWER_REJECTION_HIGH_VOLUME_PROXY" in e for e in history)
    upper=sum("UPPER_REJECTION_HIGH_VOLUME_PROXY" in e for e in history)
    phase="MIXED" if lower>=2 and upper>=2 else "DEMAND_WATCH" if lower>=2 else "SUPPLY_WATCH" if upper>=2 else "UNCONFIRMED"
    flow="UNKNOWN"
    if broker is not None:
        _available(broker,_time(assessment_time),"broker")
        if broker.get("symbol")!=rows[-1].get("symbol") or not broker.get("symbol"): raise ValueError("broker_symbol_mismatch")
        if _time(broker["observed_at"])>_time(broker["available_at"]): raise ValueError("invalid_broker_time")
        buy,sell=(Decimal(str(broker[k])) for k in ("buy_turnover","sell_turnover"))
        if any(not x.is_finite() or x<0 for x in (buy,sell)): raise ValueError("invalid_flow")
        if buy+sell>0:
            imbalance=(buy-sell)/(buy+sell)
            flow="BUYING" if imbalance>=Decimal(".2") else "SELLING" if imbalance<=Decimal("-.2") else "MIXED"
    entry=Decimal(str(rows[-1]["close"]))
    stop=Decimal(current["levels"]["support"])
    target=Decimal(current["levels"]["resistance"])
    plan=None
    if phase=="DEMAND_WATCH" and flow=="BUYING" and stop<entry<target and (target-entry)/(entry-stop)>=2:
        plan=dict(entry=str(entry),stop=str(stop),target=str(target),reward_risk=str((target-entry)/(entry-stop)),execution_eligible=False)
    return dict(phase_proxy=phase,lower_rejections=lower,upper_rejections=upper,broker_flow=flow,plan=plan,
        exit_review=phase=="SUPPLY_WATCH" and flow=="SELLING",action="NO_TRADE",production_eligible=False,
        limitations=["Repeated rejection is not confirmed accumulation; broker freshness and cohort coverage not established."])
