"""Explicit scenario costs; no implied official fee schedule or executable fills."""
from decimal import Decimal, InvalidOperation

def _number(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("invalid numeric input") from exc
    if not n.is_finite() or n < 0:
        raise ValueError("expected finite nonnegative value")
    return n

def round_trip(entry, exit, quantity, *, assumptions=None):
    result = {"classification":"hypothetical_cost_scenario","net_pnl":None,
              "net_return_pct":None,"production_eligible":False}
    if assumptions is None:
        return dict(result,status="cost_assumptions_missing")
    keys = ("buy_broker_rate","sell_broker_rate","regulatory_rate",
            "sell_dp_charge","capital_gain_tax_rate","slippage_bps","min_broker_fee")
    if any(k not in assumptions for k in keys):
        return dict(result,status="cost_assumptions_missing")
    buy,sell,qty = map(_number,(entry,exit,quantity))
    if buy<=0 or sell<=0 or qty<=0 or qty!=qty.to_integral_value():
        raise ValueError("positive prices and whole-share quantity required")
    a = {k:_number(assumptions[k]) for k in keys}
    for side in ("buy", "sell"):
        for field in ("regulatory_rate", "min_broker_fee"):
            key = side + "_" + field
            a[key] = _number(assumptions.get(key, a[field]))
    if any(a[k]>1 for k in ("buy_broker_rate","sell_broker_rate","regulatory_rate","capital_gain_tax_rate","buy_regulatory_rate","sell_regulatory_rate")) or a["slippage_bps"]>=10000:
        raise ValueError("invalid rate")
    slip = a["slippage_bps"]/10000
    buy_value = buy*(1+slip)*qty
    sell_value = sell*(1-slip)*qty
    buy_fee = max(buy_value*a["buy_broker_rate"],a["buy_min_broker_fee"])+buy_value*a["buy_regulatory_rate"]
    sell_fee = max(sell_value*a["sell_broker_rate"],a["sell_min_broker_fee"])+sell_value*a["sell_regulatory_rate"]+a["sell_dp_charge"]
    invested=buy_value+buy_fee
    pre_tax=sell_value-sell_fee-invested
    tax=max(pre_tax,Decimal(0))*a["capital_gain_tax_rate"]
    net=pre_tax-tax
    return dict(result,status="scenario_only",buy_cash=float(invested),sell_cash=float(sell_value-sell_fee-tax),
                buy_fees=float(buy_fee),sell_fees=float(sell_fee),tax=float(tax),
                net_pnl=float(net),net_return_pct=float(100*net/invested),
                assumptions={k:str(v) for k,v in a.items()},
                limitations=["Flat supplied rates, not verified historical NEPSE slabs.",
                             "Tax basis is a simplified scenario; actual tax treatment may differ.",
                             "No exchange rounding, price-limit or settlement verification."])
