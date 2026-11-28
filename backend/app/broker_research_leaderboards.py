"""Descriptive rankings within a supplied research context, never trade rankings."""
from decimal import Decimal

def research_leaderboards(context, *, limit=10):
    if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=100:
        raise ValueError("invalid limit")
    if context.get("production_eligible") is not False or context.get("signals_enabled") is not False:
        raise ValueError("research context required")
    by_security={};by_broker={};seen=set();windows=set()
    for r in context["profiles"]:
        if r["status"]!="descriptive_only": continue
        key=(r["security_id"],r["broker_id"])
        if key in seen: raise ValueError("duplicate broker security profile")
        seen.add(key)
        if r.get("production_eligible") is not False or r.get("score_eligible") is not False:
            raise ValueError("unsafe profile")
        windows.add(tuple(r["sessions"]))
        net=Decimal(r["net_amount"]);gross=Decimal(r["gross_broker_side_amount"])
        if not net.is_finite() or not gross.is_finite() or gross<=0 or abs(net)>gross:
            raise ValueError("invalid flow accounting")
        row={k:r[k] for k in ("security_id","broker_id","symbol","net_amount","gross_broker_side_amount","classification")}
        by_security.setdefault(key[0],[]).append(row)
        by_broker.setdefault(key[1],[]).append(row)
    if len(windows)>1: raise ValueError("inconsistent research windows")
    def groups(items,field):
        return [{field:key,
                 "net_buyers":sorted((r for r in rows if Decimal(r["net_amount"])>0),key=lambda r:(-Decimal(r["net_amount"]),r["security_id"],r["broker_id"]))[:limit],
                 "net_sellers":sorted((r for r in rows if Decimal(r["net_amount"])<0),key=lambda r:(Decimal(r["net_amount"]),r["security_id"],r["broker_id"]))[:limit]}
                for key,rows in sorted(items.items())]
    return {"status":"descriptive_only" if seen else "insufficient_evidence",
            "by_security":groups(by_security,"security_id"),"by_broker":groups(by_broker,"broker_id"),
            "included_profiles":len(seen),"excluded_profiles":len(context["profiles"])-len(seen),
            "production_eligible":False,"signals_enabled":False,"source_authentication_performed":False,
            "limitations":"Ranks only eligible supplied profiles by net transaction flow; not market-wide coverage, ownership, investment merit or trading recommendations."}
