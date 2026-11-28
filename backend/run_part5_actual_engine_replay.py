"""Bounded causal replay using the repository feature engines themselves."""
import csv,json,sqlite3,sys
from collections import defaultdict
from pathlib import Path
from app.part5_strategy_candidates import candidates
from app.session_calendar import load_calendar
from app.scanner import quality_errors

def run(price_csv,broker_sqlite,calendar_csv,output):
    groups=defaultdict(list)
    with open(price_csv,newline="") as f:
        for r in csv.DictReader(f):
            groups[r["symbol"]].append({k:r[k] for k in ("date","open","high","low","close","volume")})
    calendar=load_calendar(calendar_csv)
    days=sorted(d.isoformat() for d,r in calendar.items() if r["status"] in ("project_accepted_open","verified_open","verified_exceptional_open"))
    # Fixed deterministic subset chosen by symbol, not outcomes; all symbols remain candidates.
    selected=sorted(groups)[:12]
    results=[]
    db=sqlite3.connect(broker_sqlite)
    try:
        for symbol in selected:
            rows=groups[symbol]
            if quality_errors(rows):
                results.append({"symbol":symbol,"status":"invalid_ohlcv"})
                continue
            by={r["date"]:r for r in rows}
            prefix=[]
            busy=defaultdict(lambda:-1)
            stats=defaultdict(lambda:{"eligible":0,"signals":0,"returns":[]})
            for i,d in enumerate(days):
                row=by.get(d)
                if row is None:
                    prefix=[]
                    continue
                if prefix and all(float(row[k])==float(prefix[-1][k]) for k in ("open","high","low","close","volume")):
                    prefix=[]
                    continue
                prefix.append(row)
                # A fixed weekly-like stride reduces compute; not a weekly candle.
                if i%5 or not "2025-01-01"<=d<="2026-11-20" or i+5>=len(days):
                    continue
                partition=d[:4]
                f=candidates(prefix[-252:],symbol=symbol,broker_db=db,broker_sessions=days[i-4:i+1])["candidates"]
                for mode,flag in f.items():
                    key=partition+":"+mode
                    s=stats[key]
                    if flag is None:continue
                    s["eligible"]+=1
                    if not flag:continue
                    s["signals"]+=1
                    if i<=busy[key] or days[i+5][:4]!=partition or days[i+5]>"2026-11-20" or any(x not in by for x in days[i+1:i+6]):
                        continue
                    entry,exit=by[days[i+1]],by[days[i+5]]
                    if min(float(entry["volume"]),float(exit["volume"]))<=0:continue
                    s["returns"].append(100*(float(exit["close"])/float(entry["open"])-1)-1)
                    busy[key]=i+5
            for key,s in sorted(stats.items()):
                vals=s.pop("returns");period,mode=key.split(":")
                results.append(dict(symbol=symbol,partition=period,mode=mode,**s,n=len(vals),
                    mean_net_pct=sum(vals)/len(vals) if vals else None,positive_pct=100*sum(v>0 for v in vals)/len(vals) if vals else None))
    finally:
        db.close()
    report=dict(classification="retrospective_reference_only",candidate_universe=len(groups),selected=selected,
        stride=5,holding_sessions=5,cost_percentage_points=1,production_eligible=False,independent_holdout=False,
        results=results,limitations=["Fixed alphabetical subset, not representative.","No certified fills, lifecycle, price basis or availability.",
        "Master and authentic IDPAT unavailable; no missing components imputed."])
    Path(output).write_text(json.dumps(report,indent=2,allow_nan=False))
    return report

if __name__=="__main__":
    report=run(*sys.argv[1:])
    print(json.dumps({k:v for k,v in report.items() if k!="results"}))
