"""Dated brokerage and tax references for research scenarios only."""
from datetime import date
from .execution_costs import _number, round_trip
from .historical_fee_reference import brokerage_cap, resident_tax_reference

def dated_round_trip(entry, exit, quantity, *, buy_date, sell_date, assumptions=None):
    base={"status":"historical_cost_evidence_missing","production_eligible":False,
          "net_pnl":None,"net_return_pct":None}
    start,end=date.fromisoformat(str(buy_date)),date.fromisoformat(str(sell_date))
    if end<=start:
        raise ValueError("sale must follow purchase")
    if assumptions is None or any(k not in assumptions for k in ("regulatory_rate","sell_dp_charge","slippage_bps","min_broker_fee")):
        return base
    buy,sell,qty=map(_number,(entry,exit,quantity))
    slip=_number(assumptions["slippage_bps"])/10000
    if buy<=0 or sell<=0 or qty<=0 or qty!=qty.to_integral_value() or slip>=1:
        raise ValueError("invalid trade")
    b=brokerage_cap(start,buy*(1+slip)*qty)
    s=brokerage_cap(end,sell*(1-slip)*qty)
    t=resident_tax_reference(end,(end-start).days)
    if any(r.get("rate") is None for r in (b,s,t)):
        return dict(base,brokerage_buy=b,brokerage_sell=s,tax_reference=t)
    config={**assumptions,"buy_broker_rate":b["rate"],"sell_broker_rate":s["rate"],"capital_gain_tax_rate":t["rate"]}
    result=round_trip(entry,exit,quantity,assumptions=config)
    return dict(result,brokerage_buy=b,brokerage_sell=s,tax_reference=t,
        limitations=result["limitations"]+["Published date-specific brokerage caps and partial tax references, not certified historical charges.",
        "Regulatory fees, DP charges, minimum commission and slippage remain caller assumptions."])
