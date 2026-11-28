"""Research-only concentration and comparable-window sector participation."""
from decimal import Decimal
from .broker_context_integration import number

def concentration(rows, *, matched_turnover):
    """One row per broker, with reconciled buy and sell amounts.
    Matched turnover is counted once; combined broker sides total twice turnover.
    """
    turnover=number(matched_turnover,True)
    seen=set()
    gross=[]
    buy=sell=Decimal(0)
    for row in rows:
        broker=row["broker_id"]
        if not isinstance(broker,str) or not broker.strip() or broker in seen:
            raise ValueError("invalid or duplicate broker")
        seen.add(broker)
        b,s=number(row["buy_amount"]),number(row["sell_amount"])
        buy+=b;sell+=s;gross.append(b+s)
    if buy!=turnover or sell!=turnover:
        return {"status":"insufficient_evidence","reason":"turnover_reconciliation_failed","production_eligible":False}
    shares=sorted((x/(2*turnover) for x in gross),reverse=True)
    return {"status":"descriptive_only","broker_count":len(shares),
        "matched_turnover":str(turnover),"gross_side_amount":str(buy+sell),
        "hhi":str(sum(x*x for x in shares)),
        "top3_share":str(sum(shares[:3])),"top5_share":str(sum(shares[:5])),
        "production_eligible":False}

def sector_rotation(prior,current):
    """Compare already validated, equal-length nonoverlapping context windows.
    Reject scope or membership changes rather than fabricating missing zeros.
    """
    def collect(report):
        rows=report["profiles"]
        out={}
        for r in rows:
            if r["status"]!="descriptive_only": raise ValueError("incomplete context")
            key=(r["broker_id"],r["security_id"])
            if key in out: raise ValueError("duplicate context")
            out[key]=r
        return out
    a,b=collect(prior),collect(current)
    if not a or a.keys()!=b.keys(): return {"status":"insufficient_evidence","reason":"scope_mismatch","production_eligible":False}
    totals={}
    for k,x in a.items():
        y=b[k]
        if x["sector_code"]!=y["sector_code"] or len(x["sessions"])!=len(y["sessions"]) or x["sessions"][-1]>=y["sessions"][0]:
            return {"status":"insufficient_evidence","reason":"incomparable_windows","production_eligible":False}
        bucket=totals.setdefault(k[0],{})
        p=bucket.setdefault(x["sector_code"],[Decimal(0),Decimal(0)])
        p[0]+=number(x["gross_broker_side_amount"])
        p[1]+=number(y["gross_broker_side_amount"])
    result=[]
    for broker,sectors in sorted(totals.items()):
        p=sum(x[0] for x in sectors.values());c=sum(x[1] for x in sectors.values())
        if not p or not c: return {"status":"insufficient_evidence","reason":"zero_denominator","production_eligible":False}
        for sector,(u,v) in sorted(sectors.items()):
            result.append({"broker_id":broker,"sector_code":sector,"prior_share":str(u/p),"current_share":str(v/c),"share_change":str(v/c-u/p)})
    return {"status":"descriptive_only","rows":result,"production_eligible":False,"signals_enabled":False,
            "limitations":"Participation within supplied common scope; not authenticated market-wide rotation or beneficial ownership."}
