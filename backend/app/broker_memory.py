"""Persistent immutable daily broker observations, aggregated by verified session windows."""
import sqlite3
import json
from decimal import Decimal
from datetime import date

def connect(path):
    db=sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS broker_daily (
        day TEXT NOT NULL, symbol TEXT NOT NULL, broker TEXT NOT NULL,
        buy_qty TEXT NOT NULL,sell_qty TEXT NOT NULL,buy_amount TEXT NOT NULL,sell_amount TEXT NOT NULL,
        PRIMARY KEY(day,symbol,broker))""")
    db.execute("""CREATE TABLE IF NOT EXISTS broker_session (
        day TEXT NOT NULL,symbol TEXT NOT NULL,evidence TEXT NOT NULL,PRIMARY KEY(day,symbol))""")
    return db

def record_day(db, profile):
    if profile.get("status")!="research_only" or len(profile.get("sessions",[]))!=1 or not profile.get("control_evidence_ids"):
        raise ValueError("reviewed daily profile required")
    day=date.fromisoformat(profile["sessions"][0]).isoformat()
    symbol=profile["symbol"]
    rows={}
    for level in profile["levels"]:
        price=Decimal(level["price"])
        for i,side in enumerate(("buyer","seller")):
            for broker,raw in level[side+"_broker_quantity"].items():
                q=Decimal(raw)
                if not q.is_finite() or q<=0 or not price.is_finite() or price<=0: raise ValueError("invalid level")
                v=rows.setdefault(broker,[Decimal(0)]*4)
                v[i]+=q;v[i+2]+=q*price
    for i,key in enumerate(("total_quantity","total_quantity","total_amount","total_amount")):
        if sum((v[i] for v in rows.values()),Decimal(0))!=Decimal(profile[key]):
            raise ValueError("broker totals mismatch")
    evidence=json.dumps(sorted(profile["control_evidence_ids"]))
    values=[(day,symbol,b,*[str(x) for x in v]) for b,v in sorted(rows.items())]
    with db:
        existing=db.execute("SELECT evidence FROM broker_session WHERE day=? AND symbol=?",(day,symbol)).fetchone()
        if existing:
            prior=db.execute("SELECT * FROM broker_daily WHERE day=? AND symbol=? ORDER BY broker",(day,symbol)).fetchall()
            if existing[0]!=evidence or prior!=values: raise ValueError("immutable daily observation conflict")
            return "already_recorded"
        db.execute("INSERT INTO broker_session VALUES (?,?,?)",(day,symbol,evidence))
        db.executemany("INSERT INTO broker_daily VALUES (?,?,?,?,?,?,?)",values)
    return "recorded"

def memory(db,symbol,verified_sessions,*,calendar_verified=False):
    base={"status":"unavailable","symbol":symbol,"production_score":None}
    days=[date.fromisoformat(str(x)).isoformat() for x in verified_sessions]
    if not calendar_verified or not days or days!=sorted(set(days)):
        return dict(base,reason="verified_session_window_required")
    covered={r[0] for r in db.execute("SELECT day FROM broker_session WHERE symbol=? AND day BETWEEN ? AND ?",(symbol,days[0],days[-1]))}
    if not set(days)<=covered:
        return dict(base,reason="missing_daily_evidence",missing=sorted(set(days)-covered))
    totals={}
    for day,b,*v in db.execute("SELECT day,broker,buy_qty,sell_qty,buy_amount,sell_amount FROM broker_daily WHERE symbol=? AND day BETWEEN ? AND ?",(symbol,days[0],days[-1])):
        if day not in days: continue
        x=totals.setdefault(b,[Decimal(0)]*4+[0,0,0])
        nums=[Decimal(n) for n in v]
        for i,n in enumerate(nums):x[i]+=n
        x[4]+=nums[2]>nums[3];x[5]+=nums[2]<nums[3];x[6]+=1
    out=[]
    for b,x in totals.items():
        out.append({"broker":b,"buy_qty":str(x[0]),"sell_qty":str(x[1]),"buy_amount":str(x[2]),"sell_amount":str(x[3]),"net_amount":str(x[2]-x[3]),"net_buy_days":x[4],"net_sell_days":x[5],"active_days":x[6],"window_sessions":len(days)})
    out.sort(key=lambda r:(-Decimal(r["net_amount"]),r["broker"]))
    return dict(base,status="research_only",sessions=days,brokers=out,limitation="Execution channel persistence, not beneficial ownership.")
