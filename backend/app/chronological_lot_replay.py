"""Research chronological lot replay; explicit allocations, no statutory tax claims."""
from decimal import Decimal
from .portfolio_lot_accounting import _amount,_qty
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available,_day

def replay_lot_events(*,events,sessions,assessment_time,initial_cash=None):
    now=_time(assessment_time)
    days=[_day(d,"session") for d in sessions]
    if not days or days!=sorted(set(days)) or days[-1]>now.date(): raise ValueError("invalid_calendar")
    lots={}
    entitlements={}
    seen=set()
    realized=[]
    cash_receipts=Decimal(0)
    rights_paid=Decimal(0)
    cash=None if initial_cash is None else _amount(initial_cash)
    receivables=[]
    prior=None
    prior_timestamp=None
    daily_counts={}
    for event in events:
        d=_day(event['date'],'event_date')
        daily_counts[d]=daily_counts.get(d,0)+1
    for e in events:
        _available(e,now,"event")
        day=_day(e["date"],"event_date")
        eid=e["event_id"]
        if not eid or eid in seen or day>now.date() or _time(e["available_at"]).date()<day or (prior and day<prior):
            raise ValueError("ambiguous_or_invalid_event_order")
        timestamp=None
        if daily_counts[day]>1 or "event_time" in e:
            if "event_time" not in e: raise ValueError("intraday_timestamp_required")
            timestamp=_time(e["event_time"])
            if timestamp.date()!=day or timestamp>_time(e["available_at"]) or timestamp>now:
                raise ValueError("invalid_event_timestamp")
            if prior==day and (prior_timestamp is None or timestamp<=prior_timestamp):
                raise ValueError("ambiguous_intraday_order")
        seen.add(eid)
        prior=day
        prior_timestamp=timestamp
        if cash is not None:
            cash+=sum((v for d,v in receivables if d<day),Decimal(0))
            receivables=[(d,v) for d,v in receivables if d>=day]
        kind=e["type"]
        symbol=e["symbol"]
        if kind=="buy":
            settle=_day(e["settlement_date"],"settlement")
            if day not in days or settle not in days or days.index(settle)-days.index(day)!=2: raise ValueError("invalid_t_plus_two")
            if cash is not None:
                cash-=_amount(e["total_cost"])
                if cash<0: raise ValueError("insufficient_purchase_cash")
            lots[eid]=dict(symbol=symbol,quantity=_qty(e["quantity"]),cost=_amount(e["total_cost"]),settled=settle)
        elif kind=="sell":
            settle=_day(e["settlement_date"],"settlement")
            if day not in days or settle not in days or days.index(settle)-days.index(day)!=2: raise ValueError("invalid_t_plus_two")
            # Conservative: do not dispose of lots with unresolved share entitlements.
            if any(a["symbol"]==symbol and a["kind"]!="dividend" and not a["closed"] for a in entitlements.values()): raise ValueError("pending_share_action")
            allocations=e["allocations"]
            qty=_qty(e["quantity"])
            if sum(_qty(a["quantity"]) for a in allocations)!=qty or len({a["lot_id"] for a in allocations})!=len(allocations): raise ValueError("invalid_allocations")
            cost=Decimal(0)
            for a in allocations:
                l=lots[a["lot_id"]]; n=a["quantity"]
                if l["symbol"]!=symbol or l["settled"]>=day or n>l["quantity"]: raise ValueError("unavailable_lot")
                debit=l["cost"] if n==l["quantity"] else l["cost"]*n/l["quantity"]
                l["quantity"]-=n; l["cost"]-=debit; cost+=debit
            proceeds=_amount(e["price"])*qty-_amount(e["fees"])
            if proceeds<0: raise ValueError("negative_proceeds")
            if cash is not None: receivables.append((settle,proceeds))
            realized.append(dict(event_id=eid,cost=str(cost),pnl=str(proceeds-cost),symbol=symbol,settlement=settle))
        elif kind=="record":
            aid=e["action_id"]; action=e["action_type"]
            if aid in entitlements or action not in ("bonus","split","rights","dividend"): raise ValueError("invalid_action")
            if any(s["symbol"]==symbol and s["settlement"]>=day for s in realized): raise ValueError("ambiguous_record_date")
            if any(l["symbol"]==symbol and l["quantity"] and l["settled"]>=day for l in lots.values()): raise ValueError("unsettled_record_date_buy")
            if any(a["symbol"]==symbol and a["kind"]!="dividend" and not a["closed"] for a in entitlements.values()): raise ValueError("overlapping_share_actions")
            entitlements[aid]=dict(symbol=symbol,kind=action,quantities={k:l["quantity"] for k,l in lots.items() if l["symbol"]==symbol and l["quantity"]},terms=e,closed=False,paid=False)
        elif kind in ("rights_payment","credit"):
            a=entitlements[e["action_id"]]
            if a["symbol"]!=symbol or a["closed"]: raise ValueError("invalid_action_credit")
            terms=a["terms"]; action=a["kind"]
            if kind=="rights_payment":
                if action!="rights" or a["paid"]: raise ValueError("invalid_rights_payment")
                subscriptions=e["subscriptions"]
                if set(subscriptions)-set(a["quantities"]): raise ValueError("unknown_subscription_lot")
                ratio=_amount(terms["ratio"])
                if ratio<=0: raise ValueError("invalid_ratio")
                for lid,n in subscriptions.items():
                    if _qty(n)>a["quantities"][lid]*ratio: raise ValueError("excess_subscription")
                amount=sum(subscriptions.values())*_amount(terms["subscription_price"])
                if amount!=_amount(e["amount"]): raise ValueError("payment_mismatch")
                if cash is not None:
                    cash-=amount
                    if cash<0: raise ValueError("insufficient_rights_cash")
                rights_paid+=amount; a["paid"]=True; a["subscriptions"]=subscriptions
                continue
            if action=="dividend":
                net=_amount(e["net_amount"])
                if net>sum(a["quantities"].values())*_amount(terms["cash_per_share"]): raise ValueError("excess_dividend")
                cash_receipts+=net
                if cash is not None: cash+=net
            else:
                if action=="rights" and not a["paid"]: raise ValueError("rights_payment_required")
                ratio=_amount(terms["ratio"])
                if ratio<=0: raise ValueError("invalid_ratio")
                expected={}
                for lid,n in a["quantities"].items():
                    l=lots[lid]
                    if l["quantity"]!=n: raise ValueError("lot_changed")
                    q=Decimal(n)*ratio if action in ("bonus","split") else Decimal(a["subscriptions"].get(lid,0))
                    if q!=q.to_integral_value(): raise ValueError("fractional_entitlement")
                    expected[lid]=int(q)
                if e["quantities"]!=expected: raise ValueError("credit_quantity_mismatch")
                for lid,q in expected.items():
                    l=lots[lid]
                    if action=="split": l["quantity"]=q
                    else: l["quantity"]+=q
                    if action=="rights": l["cost"]+=q*_amount(terms["subscription_price"])
            a["closed"]=True
        else: raise ValueError("unsupported_event")
    if cash is not None:
        cash+=sum((v for d,v in receivables if d<=now.date()),Decimal(0))
        receivables=[(d,v) for d,v in receivables if d>now.date()]
    return dict(available_cash=None if cash is None else str(cash),sale_receivables=None if cash is None else str(sum((v for d,v in receivables),Decimal(0))),lots={k:dict(symbol=l["symbol"],quantity=l["quantity"],cost=str(l["cost"])) for k,l in lots.items()},
        realized=[dict(s,settlement=s["settlement"].isoformat()) for s in realized],
        dividend_receipts=str(cash_receipts),rights_payments=str(rights_paid),
        pending_action_ids=[k for k,a in entitlements.items() if not a["closed"]],production_eligible=False,
        limitations=["Same-day events require strictly increasing evidence-backed timestamps; settlement-day cash and shares unavailable for intraday use. Overlapping share actions withheld.",
        "Caller-attested confirmed credits; optional simulated cash funding, no tax or independent custody verification."])
