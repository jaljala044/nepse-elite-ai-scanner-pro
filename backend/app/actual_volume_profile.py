"""Exact transaction-volume profile. Caller supplies independently reviewed symbol/day controls."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from .floorsheet_contract import FloorsheetContract

def actual_volume_profile(symbol, contracts, *, sessions, controls, eligible=False):
    base = {"status":"unavailable","symbol":symbol,"levels":[],"production_score":None,
            "method":"exact_execution_price_v1"}
    if not eligible or not sessions:
        return dict(base,reason="evidence_gate")
    days=[date.fromisoformat(str(d)).isoformat() for d in sessions]
    if days!=sorted(set(days)):
        raise ValueError("sessions must be unique and ascending")
    if any(d not in controls for d in days):
        return dict(base,reason="missing_daily_controls")
    seen=set()
    daily={d:[0,Decimal(0),Decimal(0)] for d in days}
    levels={}
    for r in contracts:
        if not isinstance(r,FloorsheetContract):
            return dict(base,reason="invalid_contract_type")
        if r.symbol!=symbol or r.trade_date not in daily:
            return dict(base,reason="out_of_scope_contract")
        key=(r.trade_date,r.contract_id)
        if key in seen:
            return dict(base,reason="duplicate_contract")
        seen.add(key)
        if r.quantity!=r.quantity.to_integral_value() or r.quantity*r.rate!=r.amount:
            return dict(base,reason="contract_amount_or_quantity_mismatch")
        totals=daily[r.trade_date]
        totals[0]+=1
        totals[1]+=r.quantity
        totals[2]+=r.amount
        x=levels.setdefault(r.rate,{"quantity":Decimal(0),"amount":Decimal(0),"count":0,
                                  "buyers":defaultdict(Decimal),"sellers":defaultdict(Decimal)})
        x["quantity"]+=r.quantity
        x["amount"]+=r.amount
        x["count"]+=1
        x["buyers"][r.buyer_broker_code]+=r.quantity
        x["sellers"][r.seller_broker_code]+=r.quantity
    for d in days:
        c=controls[d]
        try:
            if c.get("reviewed") is not True or c.get("symbol")!=symbol or not c.get("evidence_id"):
                return dict(base,reason="unreviewed_control",date=d)
            expected=[Decimal(str(c[k])) for k in ("contracts","quantity","amount")]
            if any(not v.is_finite() or v<0 for v in expected) or expected!=daily[d]:
                return dict(base,reason="daily_control_mismatch",date=d)
        except (KeyError,TypeError,ValueError,InvalidOperation,AttributeError):
            return dict(base,reason="invalid_control",date=d)
    if not levels:
        return dict(base,status="verified_zero_contracts",sessions=days)
    prices=sorted(levels)
    total=sum((x["quantity"] for x in levels.values()),Decimal(0))
    turnover=sum((x["amount"] for x in levels.values()),Decimal(0))
    poc=max(range(len(prices)),key=lambda i:levels[prices[i]]["quantity"])
    a=b=poc
    covered=levels[prices[poc]]["quantity"]
    while covered<total*Decimal("0.70") and (a>0 or b<len(prices)-1):
        if a>0 and (b==len(prices)-1 or levels[prices[a-1]]["quantity"]>=levels[prices[b+1]]["quantity"]):
            a-=1
            covered+=levels[prices[a]]["quantity"]
        else:
            b+=1
            covered+=levels[prices[b]]["quantity"]
    output=[]
    for i,p in enumerate(prices):
        x=levels[p]
        q=x["quantity"]
        node=None
        if 0<i<len(prices)-1:
            left,right=levels[prices[i-1]]["quantity"],levels[prices[i+1]]["quantity"]
            node="HVN" if q>max(left,right) else "LVN" if q<min(left,right) else None
        output.append({"price":str(p),"quantity":str(q),"amount":str(x["amount"]),
            "contracts":x["count"],"in_value_area":a<=i<=b,"local_volume_node":node,
            "buyer_broker_quantity":{k:str(v) for k,v in sorted(x["buyers"].items())},
            "seller_broker_quantity":{k:str(v) for k,v in sorted(x["sellers"].items())}})
    return dict(base,status="research_only",levels=output,sessions=days,
        total_quantity=str(total),total_amount=str(turnover),contract_count=len(seen),
        poc=str(prices[poc]),val=str(prices[a]),vah=str(prices[b]),
        value_area_fraction=str(covered/total),control_evidence_ids=[controls[d]["evidence_id"] for d in days],
        limitations=["Caller must establish independent control provenance and complete session calendar.",
                     "Exact traded prices, no interpolation; value area expands over adjacent observed prices.",
                     "POC ties choose lower price; value area expansion ties choose lower neighbor.",
                     "HVN/LVN are strict local extrema, not smoothed nodes.",
                     "Broker codes identify execution channels, not beneficial owners."])
