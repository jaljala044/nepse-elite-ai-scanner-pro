"""Batch retrospective references on candidate archive, no production admission."""
import csv,json,sys
from collections import defaultdict
from pathlib import Path
from app.part5_reference_comparison import compare_reference_paths
from app.session_calendar import load_calendar

def run(price_csv,calendar_csv,output):
    calendar=load_calendar(calendar_csv)
    days=sorted(d.isoformat() for d,r in calendar.items() if r["status"] in ("project_accepted_open","verified_open","verified_exceptional_open"))
    groups=defaultdict(list)
    with open(price_csv,newline="") as f:
        for r in csv.DictReader(f):
            groups[r["symbol"]].append({k:r[k] for k in ("date","open","high","low","close","volume")})
    results=[]
    # Fixed chronological partitions; prior archive access means 2026 is not an independent holdout.
    for symbol,rows in sorted(groups.items()):
        for label,start,end in (("development","2025-01-01","2025-12-31"),("later_reference","2026-01-01","2026-11-20")):
            try:
                for horizon in (5,20,60):
                    report=compare_reference_paths(rows,days,start=start,end=end,holding_sessions=horizon,cost_pct=1)
                    results.append(dict(symbol=symbol,partition=label,horizon=horizon,**report))
            except (ValueError,KeyError,TypeError) as exc:
                results.append(dict(symbol=symbol,partition=label,status="excluded",reason=str(exc)))
    report=dict(classification="retrospective_price_reference_only",symbols=len(groups),input_rows=sum(map(len,groups.values())),
        independent_holdout=False,production_eligible=False,results=results)
    Path(output).write_text(json.dumps(report,indent=2,allow_nan=False))
    return report
if __name__=="__main__":
    report=run(*sys.argv[1:])
    print(json.dumps({k:v for k,v in report.items() if k!="results"}))
