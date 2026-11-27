"""Caller-attested pending asset reconciliation; no implied custody or fair value."""
from decimal import Decimal
from .portfolio_lot_accounting import _amount, _qty
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available, _day

def review_pending_assets(*,entitlements,confirmations,assessment_time):
    now=_time(assessment_time)
    by_id={}
    for c in confirmations:
        _available(c,now,"confirmation")
        aid=c["action_id"]
        if not aid or aid in by_id: raise ValueError("duplicate_confirmation")
        by_id[aid]=c
    seen=set()
    rows=[]
    cash=Decimal(0)
    rights_cost=Decimal(0)
    dividends=Decimal(0)
    listed={}
    unknown=[]
    for e in entitlements:
        _available(e,now,"entitlement")
        aid=e["action_id"]
        if not aid or aid in seen: raise ValueError("duplicate_entitlement")
        seen.add(aid)
        record=_day(e["record_date"],"record")
        due=_day(e["due_date"],"due")
        if not record<=now.date() or due<record: raise ValueError("invalid_entitlement_dates")
        kind=e["action_type"]
        if kind not in ("dividend","bonus","rights"): raise ValueError("unsupported_pending_asset")
        c=by_id.get(aid)
        if c:
            effective=_day(c["effective_date"],"confirmation_date")
            if not record<=effective<=now.date() or _time(c["available_at"]).date()<effective or c["symbol"]!=e["symbol"]:
                raise ValueError("invalid_confirmation")
        value=None
        if kind=="dividend":
            gross=_amount(e["gross_amount"])
            if c:
                if c["event_type"]!="cash_received": raise ValueError("wrong_confirmation_type")
                net=_amount(c["net_amount"])
                if net>gross: raise ValueError("receipt_exceeds_entitlement")
                cash+=net
            else:
                dividends+=gross
        else:
            qty=_qty(e["quantity"])
            if kind=="rights":
                _available(e["payment_evidence"],now,"rights_payment")
                p=e["payment_evidence"]
                paid=_day(p["payment_date"],"payment")
                if p["action_id"]!=aid or p["symbol"]!=e["symbol"] or not record<=paid<=now.date() or _time(p["available_at"]).date()<paid:
                    raise ValueError("invalid_rights_payment")
                cost=_amount(p["amount"])
                if cost<=0: raise ValueError("invalid_rights_cost")
            if c:
                if c["event_type"]!="shares_credited" or _qty(c["quantity"])!=qty: raise ValueError("share_credit_mismatch")
                listed[e["symbol"]]=listed.get(e["symbol"],0)+qty
            elif kind=="rights":
                rights_cost+=cost
                value=str(cost)
            else:
                unknown.append(aid)
        rows.append(dict(action_id=aid,action_type=kind,status="CONFIRMED" if c else ("OVERDUE_UNCONFIRMED" if due<=now.date() else "PENDING"),pending_carrying_cost=value))
    if set(by_id)-seen: raise ValueError("confirmation_without_entitlement")
    return dict(assets=rows,confirmed_cash_receipt_delta=str(cash),confirmed_share_credit_delta=listed,
        pending_gross_dividends=str(dividends),pending_paid_rights_at_cost=str(rights_cost),
        unknown_valuation_action_ids=unknown,complete_fair_value=None,production_eligible=False,
        limitations=["Deltas only; do not add again to balances already reflecting receipts.",
        "Gross dividends not spendable; rights at cost not fair value; bonus valuation withheld.",
        "No partial confirmations, taxes, or independent custody verification."])
