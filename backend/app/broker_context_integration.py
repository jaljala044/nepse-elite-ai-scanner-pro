"""P4.38 research-only broker/price/sector context. No execution or signal authority."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from hashlib import sha256
import json

VERSION="p438.1"
POLICY="complete_source_sessions_only_no_zero_filling_for_missing_sessions_point_in_time_descriptive_only"

def stamp(v):
    t=datetime.fromisoformat(v.replace("Z","+00:00"))
    if t.utcoffset() is None: raise ValueError("timezone required")
    return t

def number(v, positive=False):
    d=Decimal(str(v))
    if not d.is_finite() or d<0 or (positive and d==0): raise ValueError("invalid numeric")
    return d

def evidence(row, cutoff, day):
    h=row["source_payload_sha256"]
    return (row.get("status")=="verified" and bool(row.get("source_id")) and len(h)==64
        and all(c in "0123456789abcdef" for c in h.lower())
        and stamp(row["available_at"])<=cutoff and date.fromisoformat(day)<=cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date())

def build_context(snapshot, prices, memberships, sector_prices, *, decision_time, expected_sessions, quarantine_keys):
    """Explicit caller-supplied research evidence; not authenticated by this module."""
    cutoff=stamp(decision_time)
    sessions=list(expected_sessions)
    if len(sessions)<5 or sessions!=sorted(set(sessions)): raise ValueError("invalid session window")
    if date.fromisoformat(sessions[-1])>cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date(): raise ValueError("future session")
    if snapshot.get("policy")!=POLICY or stamp(snapshot["as_of_timestamp"])>cutoff or snapshot["as_of_date"]!=sessions[-1]:
        raise ValueError("invalid profile cutoff")
    q=set(tuple(x) for x in quarantine_keys)
    def indexed(rows, key):
        out={}
        for row in rows:
            k=tuple(row[f] for f in key)
            if k in out: raise ValueError("duplicate evidence key")
            out[k]=row
        return out
    px=indexed(prices,("security_id","session_date"))
    sx=indexed(sector_prices,("sector_code","session_date"))
    groups={}
    for profile in snapshot["profiles"]:
        if profile.get("requested_sessions")!=len(sessions): continue
        key=(profile["security_id"],profile["broker_id"])
        if key in groups: raise ValueError("duplicate broker profile")
        groups[key]=profile
    result=[]
    for (sec,broker),p in sorted(groups.items()):
        base={"security_id":sec,"broker_id":broker,"status":"insufficient_evidence","classification":"UNKNOWN","production_eligible":False,"score_eligible":False}
        try:
            daily=p["daily"]
            if (p["status"]!="descriptive_only" or number(p["coverage_ratio"])!=1
                or p["expected_sessions"]!=len(sessions) or p["complete_source_sessions"]!=len(sessions)
                or [x["session_date"] for x in daily]!=sessions): raise ValueError("incomplete broker window")
            bars=[]; sectors=[]; symbols=[]
            for day in sessions:
                b=px[(sec,day)]
                if not evidence(b,cutoff,day): raise ValueError("unverified price evidence")
                symbol=b["symbol"].upper()
                if any(s==symbol and sessions[0]<=d<=sessions[-1] for s,d in q): raise ValueError("historical quarantine")
                matches=[m for m in memberships if m["security_id"]==sec and m["symbol"].upper()==symbol
                    and m["effective_from"]<=day and (m.get("effective_to") is None or day<=m["effective_to"])]
                if len(matches)!=1 or not evidence(matches[0],cutoff,day): raise ValueError("missing or ambiguous sector membership")
                sector=matches[0]["sector_code"]
                idx=sx[(sector,day)]
                if not evidence(idx,cutoff,day): raise ValueError("unverified sector evidence")
                o,h,l,c,v=[number(b[k],True) for k in ("open","high","low","close","volume")]
                if l>min(o,c) or h<max(o,c) or v!=v.to_integral_value(): raise ValueError("invalid OHLCV")
                bars.append((c,v));sectors.append((sector,number(idx["close"],True)));symbols.append(symbol)
            if len(set(symbols))!=1 or len({x[0] for x in sectors})!=1: raise ValueError("identity or sector changed within window")
            buys=[number(x["buy_amount"]) for x in daily];sells=[number(x["sell_amount"]) for x in daily]
            net=[b-s for b,s in zip(buys,sells)]; gross=sum(buys)+sum(sells)
            if gross<=0: raise ValueError("no broker activity")
            shares=[number(x["broker_participation"]) for x in daily]
            if any(x>1 for x in shares): raise ValueError("invalid participation")
            for x,b,s in zip(daily,buys,sells):
                if Decimal(str(x["net_amount"]))!=b-s or number(x["gross_amount"])!=b+s: raise ValueError("daily accounting mismatch")
            if number(p["buy_amount"])!=sum(buys) or number(p["sell_amount"])!=sum(sells): raise ValueError("profile accounting mismatch")
            up=Decimal(sum(x>0 for x in net))/len(net);down=Decimal(sum(x<0 for x in net))/len(net)
            ret=bars[-1][0]/bars[0][0]-1
            relative=ret-(sectors[-1][1]/sectors[0][1]-1)
            vol=bars[-1][1]/(sum(x[1] for x in bars[:-1])/Decimal(len(bars)-1))
            label="mixed_flow"
            if sum(net)>0 and up>=Decimal(".6") and ret>0 and relative>0 and vol>=1: label="accumulation_research_candidate"
            elif sum(net)<0 and down>=Decimal(".6") and ret<0 and relative<0 and vol>=1: label="distribution_research_candidate"
            base.update(status="descriptive_only",classification=label,symbol=symbols[0],sector_code=sectors[0][0],
                net_amount=str(sum(net)),gross_broker_side_amount=str(gross),positive_session_ratio=str(up),
                negative_session_ratio=str(down),mean_participation=str(sum(shares)/len(shares)),
                peak_participation=str(max(shares)),price_return=str(ret),sector_relative_return=str(relative),
                latest_volume_ratio=str(vol),sessions=sessions,source_authentication_performed=False)
        except (KeyError,ValueError,TypeError,InvalidOperation,ArithmeticError,AttributeError) as exc:
            base["reason"]=str(exc)
        result.append(base)
    return {"methodology_version":VERSION,"decision_time":decision_time,"profiles":result,
        "status":"descriptive_only" if any(r["status"]=="descriptive_only" for r in result) else "insufficient_evidence",
        "reason":None if any(r["status"]=="descriptive_only" for r in result) else "no_eligible_profiles",
        "production_eligible":False,"signals_enabled":False,"source_authentication_performed":False,
        "input_sha256":sha256(json.dumps([snapshot,prices,memberships,sector_prices,sessions,sorted(q)],sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "limitations":"Caller-supplied evidence and calendar are not independently authenticated; broker codes are execution channels, not ownership; thresholds are uncalibrated research heuristics."}
