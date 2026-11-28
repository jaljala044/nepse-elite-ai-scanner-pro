"""Run eight predeclared portfolio scenarios against the pinned candidate archive."""
import csv,json,sys
from collections import defaultdict
from pathlib import Path
from app.session_calendar import load_calendar
from app.part5_strategy_candidates import candidates
from app.part5_portfolio_retry import replay_portfolio

COSTS=dict(buy_broker_rate=.0036,sell_broker_rate=.0036,regulatory_rate=.00015,
           sell_dp_charge=25,capital_gain_tax_rate=.075,slippage_bps=20,min_broker_fee=10)
MODES=("unconditional","momentum","breakout","provisional","minervini","wyckoff",
       "breakout_tight","breakout_wide")

def run(price_csv,calendar_csv,output):
    calendar=load_calendar(calendar_csv)
    days=sorted(d.isoformat() for d,r in calendar.items() if r["status"] in
        ("project_accepted_open","verified_open","verified_exceptional_open") and "2024-01-01"<=d.isoformat()<="2025-12-31")
    groups=defaultdict(list)
    with open(price_csv,newline="") as f:
        for r in csv.DictReader(f):
            if r["date"] in days:
                groups[r["symbol"]].append(dict(date=r["date"],**{k:float(r[k]) for k in ("open","high","low","close","volume")}))
    signals={m:defaultdict(list) for m in MODES}
    for symbol,rows in sorted(groups.items()):
        by={r["date"]:r for r in rows}
        if len(by)!=len(rows):raise ValueError("duplicate symbol date")
        prefix=[]
        for day in days:
            row=by.get(day)
            if row is None:
                prefix=[];continue
            if prefix and all(row[k]==prefix[-1][k] for k in ("open","high","low","close","volume")):
                prefix=[];continue
            prefix.append(row)
            if day<"2025-01-01" or len(prefix)<21:continue
            flags=candidates(prefix[-252:])["candidates"]
            prior=prefix[-21:-1]
            momentum=row["close"]>prior[0]["close"]
            breakout=row["close"]>max(x["high"] for x in prior)
            checks={"unconditional":True,"momentum":momentum,"breakout":breakout,
                    "provisional":flags["provisional"],"minervini":flags["minervini"],
                    "wyckoff":flags["wyckoff"],"breakout_tight":breakout,"breakout_wide":breakout}
            for m,flag in checks.items():
                if flag is True:signals[m][day].append(symbol)
    results={}
    for m in MODES:
        stop={"breakout_tight":.03,"breakout_wide":.08}.get(m,.05)
        results[m]=replay_portfolio(groups,days,signals[m],costs=COSTS,stop=stop,target=2*stop)
    report={"classification":"retrospective_scenario_only","production_eligible":False,
            "symbols":len(groups),"cost_assumptions":COSTS,"results":results,
            "limitations":["Repository implementation differs from earlier local proxy experiment.",
            "Five-session holding from entry, ten-session retry, no certified calendar settlement or fees."]}
    Path(output).write_text(json.dumps(report,indent=2,allow_nan=False))
    return report
if __name__=="__main__":run(*sys.argv[1:])
