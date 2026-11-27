"""Delayed stop cost sensitivity; not a fill or portfolio return."""
from decimal import Decimal, ROUND_FLOOR
from .scanner_delayed_exit import delayed_exit_reference
from .execution_backtest import _d,_tick,_band_check
from .execution_costs import round_trip

def delayed_stop_costs(*,risk_inputs,quantity,cost_assumptions,tick_size,max_participation):
    result=delayed_exit_reference(**risk_inputs)
    if result["exit_status"]!="HYPOTHETICAL_OPEN_REFERENCE": return dict(result,net_pnl=None)
    qty=_d(quantity,"quantity",positive=True)
    tick=_d(tick_size,"tick",positive=True)
    cap=_d(max_participation,"participation",positive=True)
    slip=_d(cost_assumptions["slippage_bps"],"slippage")
    if qty!=qty.to_integral_value() or cap>1 or not 0<=slip<10000: raise ValueError("invalid_execution_assumptions")
    bars={r["date"]:r for r in risk_inputs["rows"]}
    day=result["exit_reference_date"]
    bar=bars[day]; band=risk_inputs["price_bands"][day]
    entry_day=risk_inputs["entry_date"]; entry_bar=bars[entry_day]; entry_band=risk_inputs["price_bands"].get(entry_day)
    if not entry_band or not _band_check(entry_bar,entry_band)[0]: return dict(result,net_pnl=None,cost_status="ENTRY_BAND_UNAVAILABLE")
    if _d(entry_bar["high"],"high")==_d(entry_bar["low"],"low")==_d(entry_band["upper"],"upper"): return dict(result,net_pnl=None,cost_status="ENTRY_LOCKED")
    capacity=min((_d(b["volume"],"volume")*cap).to_integral_value(rounding=ROUND_FLOOR) for b in (entry_bar,bar))
    if capacity<qty: return dict(result,net_pnl=None,cost_status="FULL_QUANTITY_CAPACITY_UNPROVEN")
    buy=_tick(_d(risk_inputs["entry_price"],"entry",positive=True)*(1+slip/10000),tick,buy=True)
    sell=_tick(_d(result["exit_reference"],"exit",positive=True)*(1-slip/10000),tick,buy=False)
    if not _d(entry_band["lower"],"lower")<=buy<=_d(entry_band["upper"],"upper") or not _d(band["lower"],"lower")<=sell<=_d(band["upper"],"upper"): return dict(result,net_pnl=None,cost_status="PRICE_OUTSIDE_BAND")
    costs=round_trip(buy,sell,qty,assumptions=dict(cost_assumptions,slippage_bps=0))
    return dict(result,cost_status=costs["status"],net_pnl=costs.get("net_pnl"),net_return_pct=costs.get("net_return_pct"),costs=costs,production_eligible=False)
