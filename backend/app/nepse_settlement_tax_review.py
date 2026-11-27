"""Research-only settlement and tax scenario; no statutory rates assumed."""
from decimal import Decimal
from datetime import date
from .unified_portfolio_event_engine import _available
from .corporate_action_trade_plan import _time

def review_settlement_tax(*,trade_date,settlement_date,sessions,calendar_evidence,tax_schedule,assessment_time,net_proceeds,allocated_cost,investor_category):
    now=_time(assessment_time)
    _available(calendar_evidence,now,"calendar")
    _available(tax_schedule,now,"tax_schedule")
    days=[date.fromisoformat(d) for d in sessions]
    trade=date.fromisoformat(trade_date)
    settle=date.fromisoformat(settlement_date)
    if days!=sorted(set(days)) or calendar_evidence["sessions"]!=sessions or trade not in days or settle not in days or days.index(settle)-days.index(trade)!=2:
        raise ValueError("invalid_t_plus_two_calendar")
    if settle>now.date(): raise ValueError("settlement_not_yet_observed")
    if not date.fromisoformat(tax_schedule["effective_from"])<=trade<=date.fromisoformat(tax_schedule["effective_to"]) or tax_schedule["investor_category"]!=investor_category:
        raise ValueError("tax_schedule_not_applicable")
    rate,proceeds,cost=map(lambda x:Decimal(str(x)),(tax_schedule["rate"],net_proceeds,allocated_cost))
    if any(not x.is_finite() or x<0 for x in (rate,proceeds,cost)) or rate>1: raise ValueError("invalid_tax_inputs")
    gain=proceeds-cost
    tax=max(gain,Decimal(0))*rate
    return dict(settlement_calendar_passed=True,estimated_tax=str(tax),estimated_net_gain=str(gain-tax),production_eligible=False,classification="caller_attested_tax_scenario",limitations=["No independent statutory rate, holding period, tax basis or custody confirmation."])
