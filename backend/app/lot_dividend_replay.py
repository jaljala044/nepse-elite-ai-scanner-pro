"""Conservative chronological dividend entitlement research."""
from decimal import Decimal
from .portfolio_lot_accounting import reconcile_lots, _amount
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available, _day

def replay_lot_dividends(*,lots,sales,actions,sessions,assessment_time):
    now=_time(assessment_time)
    days=[_day(d,"session") for d in sessions]
    if days!=sorted(set(days)) or not days or days[-1]!=now.date():
        raise ValueError("invalid_session_calendar")
    # Validate complete lot disposal history before deriving any entitlement.
    reconcile_lots(lots=lots,sales=sales,marks={},assessment_time=assessment_time)
    for sale in sales:
        trade=_day(sale["trade_date"],"trade")
        settle=_day(sale["settlement_date"],"settlement")
        if trade not in days or settle not in days or days.index(settle)-days.index(trade)!=2:
            raise ValueError("sale_settlement_not_verified_t_plus_two")
    result=[]
    seen=set()
    for action in actions:
        _available(action,now,"action")
        aid=action["action_id"]
        if not aid or aid in seen or action["action_type"]!="dividend":
            raise ValueError("invalid_or_duplicate_dividend")
        seen.add(aid)
        record=_day(action["record_date"],"record")
        payment=_day(action["payment_date"],"payment")
        if record not in days or payment<record: raise ValueError("invalid_dividend_dates")
        symbol=action["symbol"]
        if any(s["symbol"]==symbol and _day(s["trade_date"],"trade")<=record<=_day(s["settlement_date"],"settlement") for s in sales):
            raise ValueError("record_date_sale_custody_ambiguous")
        eligible=[l for l in lots if l["symbol"]==symbol and _day(l["settlement_date"],"settlement")<=record]
        remaining={l["lot_id"]:l["quantity"] for l in eligible}
        for sale in sales:
            if sale["symbol"]==symbol and _day(sale["settlement_date"],"settlement")<record:
                for allocation in sale["allocations"]:
                    if allocation["lot_id"] not in remaining: raise ValueError("entitlement_lot_mismatch")
                    remaining[allocation["lot_id"]]-=allocation["quantity"]
        amount=sum(remaining.values())*_amount(action["cash_per_share"])
        result.append(dict(action_id=aid,symbol=symbol,record_date=record.isoformat(),payment_date=payment.isoformat(),
            lot_entitlements=remaining,gross_dividend=str(amount),status="PAYMENT_DUE_OR_PAST_UNCONFIRMED" if payment<=now.date() else "PENDING",
            spendable_cash_credit="0"))
    return dict(entitlements=result,production_eligible=False,limitations=[
        "Caller-attested complete lot and sale history, no intervening non-dividend corporate actions.",
        "Payment schedule is not proof of receipt; no spendable cash credited.",
        "Same-day or unsettled sale record-date overlaps withheld."])
