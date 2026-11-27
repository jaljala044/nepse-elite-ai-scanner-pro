"""Research adjustment of reconciled record-date lots; not a custody ledger."""
from decimal import Decimal
from .portfolio_lot_accounting import _amount, _qty
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available, _day

def adjust_record_date_lots(*,lots,action,assessment_time,available_cash):
    now=_time(assessment_time)
    _available(action,now,"action")
    record=_day(action["record_date"],"record")
    kind=action["action_type"]
    if kind not in ("bonus","split","dividend","rights"): raise ValueError("unsupported_action")
    effective=_day(action["payment_date"] if kind=="dividend" else action["listing_date"],"effective")
    if not record<=effective<=now.date(): raise ValueError("action_not_effective")
    cash=_amount(available_cash)
    adjusted=[]
    audit=[]
    seen=set()
    allocations=action.get("subscriptions",{})
    if kind=="rights":
        payment=_day(action["subscription_payment_date"],"payment")
        if not record<=payment<effective: raise ValueError("invalid_rights_dates")
    for lot in lots:
        _available(lot,now,"lot")
        lid=lot["lot_id"]
        if not lid or lid in seen: raise ValueError("duplicate_lot")
        seen.add(lid)
        if lot["symbol"]!=action["symbol"]: raise ValueError("lot_symbol_mismatch")
        if _day(lot["settlement_date"],"settlement")>record or _day(lot["snapshot_date"],"snapshot")!=record:
            raise ValueError("record_date_custody_required")
        if lot.get("unchanged_through_effective_date") is not True:
            raise ValueError("intervening_lot_events_require_replay")
        if action["action_id"] in lot.get("applied_action_ids",[]): raise ValueError("action_already_applied")
        qty=_qty(lot["quantity"])
        cost=_amount(lot["total_cost"])
        new_qty=Decimal(qty)
        delta=Decimal(0)
        if kind=="dividend":
            delta=qty*_amount(action["cash_per_share"])
        else:
            ratio=_amount(action["ratio"])
            if ratio<=0: raise ValueError("invalid_ratio")
            if kind=="bonus": new_qty+=qty*ratio
            elif kind=="split": new_qty*=ratio
            else:
                n=allocations.get(lid,0)
                if type(n) is not int or n<0 or n>qty*ratio: raise ValueError("invalid_rights_allocation")
                new_qty+=n
                delta=-n*_amount(action["subscription_price"])
                cost-=delta
        if new_qty!=new_qty.to_integral_value(): raise ValueError("fractional_entitlement_requires_evidence")
        cash+=delta
        if cash<0: raise ValueError("insufficient_subscription_cash")
        adjusted.append(dict(lot,quantity=int(new_qty),total_cost=str(cost),snapshot_date=effective.isoformat(),
            applied_action_ids=[*lot.get("applied_action_ids",[]),action["action_id"]]))
        audit.append(dict(lot_id=lid,record_quantity=qty,adjusted_quantity=int(new_qty),cash_delta=str(delta)))
    if kind=="rights" and set(allocations)-seen: raise ValueError("unknown_subscription_lot")
    return dict(lots=adjusted,available_cash=str(cash),audit=audit,production_eligible=False,
        limitations=["Requires caller-attested unchanged record-date lots through effective date.",
        "Rights cash is a retrospective adjustment, not a dated cash ledger; dividends gross.",
        "No tax, fractional cash-in-lieu or intervening trade replay."])
