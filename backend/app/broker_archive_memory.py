"""Import immutable archive candidates. No canonical or production promotion."""
import csv, hashlib, io, sqlite3
from decimal import Decimal
from collections import defaultdict
from datetime import date

def connect(path):
    db=sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("""CREATE TABLE IF NOT EXISTS archive_sessions(day TEXT PRIMARY KEY, blob_sha TEXT NOT NULL, controls TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS archive_broker(day TEXT REFERENCES archive_sessions(day),symbol TEXT,broker TEXT,buy_qty INTEGER,sell_qty INTEGER,buy_cents INTEGER,sell_cents INTEGER,PRIMARY KEY(day,symbol,broker))""")
    return db

def ingest(db, raw, control):
    day=date.fromisoformat(control["date"]).isoformat()
    if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=control["blob_sha"]:
        raise ValueError("blob hash mismatch")
    def integer(s, factor=1):
        v=Decimal(str(s))*factor
        if not v.is_finite() or v<0 or v!=v.to_integral_value():raise ValueError("invalid numeric value")
        return int(v)
    totals=defaultdict(lambda:[0,0,0,0]);rows=[];keys=set()
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames!=["symbol","date","broker","buy_qty","sell_qty","buy_value","sell_value"]:raise ValueError("schema mismatch")
    for r in reader:
        s,b=r["symbol"],r["broker"]
        if r["date"]!=day or not s or not b or (s,b) in keys:raise ValueError("invalid or duplicate key")
        keys.add((s,b))
        v=[integer(r["buy_qty"]),integer(r["sell_qty"]),integer(r["buy_value"],100),integer(r["sell_value"],100)]
        if any((v[i]==0)!=(v[i+2]==0) for i in (0,1)) or not any(v):raise ValueError("inconsistent side")
        for i,n in enumerate(v):totals[s][i]+=n
        rows.append((day,s,b,*v))
    if any(v[0]!=v[1] or v[2]!=v[3] for v in totals.values()):raise ValueError("unbalanced stock")
    sums=[sum(v[i] for v in totals.values()) for i in range(4)]
    qty=integer(control["shares"]);amount=integer(control["turnover"],100)
    if sums!=[qty,qty,amount,amount] or len(totals)!=integer(control["instruments"]):raise ValueError("control mismatch")
    import json
    evidence=json.dumps(control,sort_keys=True)
    with db:
        prior=db.execute("SELECT blob_sha,controls FROM archive_sessions WHERE day=?",(day,)).fetchone()
        if prior:
            if prior!=(control["blob_sha"],evidence):raise ValueError("immutable session conflict")
            existing=db.execute("SELECT * FROM archive_broker WHERE day=? ORDER BY symbol,broker",(day,)).fetchall()
            if existing!=sorted(rows):raise ValueError("stored rows differ")
            return {"status":"already_recorded","rows":len(rows)}
        db.execute("INSERT INTO archive_sessions VALUES (?,?,?)",(day,control["blob_sha"],evidence))
        db.executemany("INSERT INTO archive_broker VALUES (?,?,?,?,?,?,?)",rows)
    return {"status":"recorded","rows":len(rows)}

def profile(db,symbol,sessions,*,calendar_verified=False,identity_verified=False):
    days=[date.fromisoformat(str(d)).isoformat() for d in sessions]
    if not days or days!=sorted(set(days)):raise ValueError("invalid sessions")
    covered={r[0] for r in db.execute("SELECT day FROM archive_sessions WHERE day BETWEEN ? AND ?",(days[0],days[-1]))}
    missing=sorted(set(days)-covered)
    base={"status":"unavailable","missing_sessions":missing,"production_eligible":False,"symbol":symbol}
    if missing:return base
    totals=defaultdict(lambda:[0]*7)
    for day,b,bq,sq,bv,sv in db.execute("SELECT day,broker,buy_qty,sell_qty,buy_cents,sell_cents FROM archive_broker WHERE symbol=? AND day BETWEEN ? AND ?",(symbol,days[0],days[-1])):
        if day not in days:continue
        x=totals[b]
        for i,v in enumerate((bq,sq,bv,sv)):x[i]+=v
        x[4]+=bv>sv;x[5]+=sv>bv;x[6]+=1
    total=sum(x[2]+x[3] for x in totals.values())
    rows=[]
    for b,x in totals.items():
        net=x[2]-x[3];gross=x[2]+x[3]
        # Exploratory thresholds, not independently validated.
        label="persistent_net_buy" if net>0 and x[4]*5>=len(days)*3 and net*5>=gross else "persistent_net_sell" if net<0 and x[5]*5>=len(days)*3 and -net*5>=gross else "mixed"
        rows.append(dict(broker=b,buy_qty=x[0],sell_qty=x[1],buy_cents=x[2],sell_cents=x[3],net_cents=net,net_buy_days=x[4],net_sell_days=x[5],active_days=x[6],classification=label,gross_share_pct=100*gross/total if total else None))
    rows.sort(key=lambda x:(-x["net_cents"],x["broker"]))
    gross=sorted((x[2]+x[3] for x in totals.values()),reverse=True)
    return dict(base,status="archive_research_only",sessions=days,calendar_verified=calendar_verified,identity_verified=identity_verified,brokers=rows,top3_gross_share_pct=100*sum(gross[:3])/total if total else None,limitations=["Symbol and broker-code continuity not established by archive balance.","No ownership or exit inference.","Persistence thresholds are exploratory."])

def rotation(previous,current):
    if previous.get("status")!="archive_research_only" or current.get("status")!="archive_research_only" or previous["symbol"]!=current["symbol"] or previous["sessions"][-1]>=current["sessions"][0]:
        return {"status":"unavailable"}
    a={r["broker"]:r for r in previous["brokers"]};b={r["broker"]:r for r in current["brokers"]}
    flips=[]
    for k in sorted(a.keys()&b.keys()):
        p,c=a[k]["net_cents"],b[k]["net_cents"]
        if p*c<0:flips.append({"broker":k,"previous_net_cents":p,"current_net_cents":c,"direction":"buy_to_sell" if p>0 else "sell_to_buy"})
    return {"status":"archive_research_only","direction_changes":flips,"production_eligible":False}
