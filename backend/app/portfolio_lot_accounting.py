"""Explicit lot allocation research; not statutory NEPSE tax accounting."""
from decimal import Decimal
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available, _day

def _amount(value):
    n=Decimal(str(value))
    if not n.is_finite() or n<0: raise ValueError("invalid_amount")
    return n

def _qty(value):
    if type(value) is not int or value<=0: raise ValueError("invalid_whole_share_quantity")
    return value

def reconcile_lots(*,lots,sales,marks,assessment_time):
    now=_time(assessment_time)
    state={}
    for lot in lots:
        _available(lot,now,"lot")
        lid=lot["lot_id"]
        if not lid or lid in state: raise ValueError("duplicate_or_missing_lot_id")
        qty=_qty(lot["quantity"])
        acquired=_day(lot["acquisition_date"],"acquisition")
        settled=_day(lot["settlement_date"],"settlement")
        if acquired>settled or acquired>now.date(): raise ValueError("invalid_lot_dates")
        state[lid]=dict(symbol=lot["symbol"],quantity=qty,cost=_amount(lot["total_cost"]),settled=settled)
    seen=set()
    realized=[]
    prior=None
    for sale in sales:
        _available(sale,now,"sale")
        sid=sale["sale_id"]
        day=_day(sale["trade_date"],"sale_date")
        if not sid or sid in seen or day>now.date() or (prior and day<prior): raise ValueError("invalid_sale_sequence")
        seen.add(sid)
        prior=day
        qty=_qty(sale["quantity"])
        allocations=sale["allocations"]
        if sum(_qty(a["quantity"]) for a in allocations)!=qty or len({a["lot_id"] for a in allocations})!=len(allocations):
            raise ValueError("allocation_quantity_or_duplicate")
        cost=Decimal(0)
        for a in allocations:
            lot=state.get(a["lot_id"])
            n=a["quantity"]
            if not lot or lot["symbol"]!=sale["symbol"] or lot["settled"]>day or n>lot["quantity"]:
                raise ValueError("lot_unavailable_or_oversold")
            debit=lot["cost"] if n==lot["quantity"] else lot["cost"]*n/lot["quantity"]
            lot["quantity"]-=n
            lot["cost"]-=debit
            cost+=debit
        proceeds=_amount(sale["price"])*qty-_amount(sale["fees"])
        if proceeds<0: raise ValueError("negative_sale_proceeds")
        realized.append(dict(sale_id=sid,allocated_cost=str(cost),net_proceeds=str(proceeds),realized_pnl=str(proceeds-cost)))
    remaining=[]
    for lid,lot in state.items():
        if not lot["quantity"]: continue
        mark=marks.get(lot["symbol"])
        pnl=None
        if mark is not None:
            _available(mark,now,"mark")
            if mark["symbol"]!=lot["symbol"] or _day(mark["date"],"mark_date")!=now.date(): raise ValueError("invalid_mark")
            pnl=str(_amount(mark["close"])*lot["quantity"]-lot["cost"])
        remaining.append(dict(lot_id=lid,symbol=lot["symbol"],quantity=lot["quantity"],remaining_cost=str(lot["cost"]),
            settled=lot["settled"]<=now.date(),unrealized_pnl=pnl))
    return dict(realized=realized,remaining_lots=remaining,production_eligible=False,
        limitations=["Explicit caller-supplied allocation; no statutory tax-lot assumption.",
                     "Opening lots must already reflect corporate actions; no settlement cash ledger or tax calculation.",
                     "Caller-attested evidence only."])
