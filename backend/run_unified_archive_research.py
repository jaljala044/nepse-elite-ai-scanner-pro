"""Execute existing feature engines on P4 research candidates, without promotion."""
import csv,json,sys,sqlite3
from pathlib import Path
from collections import defaultdict,Counter
from app.trend_features import minervini_trend_template
from app.wyckoff_features import wyckoff_event_features
from app.volume_vsa_features import volume_vsa_features
from app.smc_features import smc_features
from app.broker_archive_memory import profile
from app.scoring_engine import COMPONENT_WEIGHTS

def run(price_csv,broker_db,out):
    groups=defaultdict(list)
    with open(price_csv,newline="") as f:
        for r in csv.DictReader(f):
            groups[r["symbol"]].append(dict(session_date=r["date"],**{k:float(r[k]) for k in ("open","high","low","close","volume")}))
    calendar=sorted({r["session_date"] for g in groups.values() for r in g})
    asof=calendar[-1]
    db=sqlite3.connect(broker_db)
    days=[r[0] for r in db.execute("SELECT day FROM archive_sessions WHERE day<=? ORDER BY day",(asof,))]
    output=[]
    for s,rows in sorted(groups.items()):
        by={r["session_date"]:r for r in rows}
        if len(by)!=len(rows):raise ValueError("duplicate price")
        suffix=[]
        for d in reversed(calendar):
            if d not in by:break
            suffix.append(by[d])
        suffix.reverse()
        rec={"symbol":s,"as_of":asof,"historical_rows":len(rows),"contiguous_observed_rows":len(suffix),"production_score":None,"action":"UNKNOWN"}
        for name,fn in [("trend",minervini_trend_template),("wyckoff",wyckoff_event_features),("volume",volume_vsa_features),("smc",smc_features)]:
            try:
                result=fn(suffix)
                rec[name+"_status"]=result.get("status")
                rec[name+"_research_score"]=result.get("score")
            except (ValueError,TypeError,KeyError,IndexError) as e:
                rec[name+"_status"]="unavailable:"+type(e).__name__
                rec[name+"_research_score"]=None
        p=profile(db,s,days[-5:]) if len(days)>=5 else {}
        rec["broker_status"]=p.get("status","unavailable")
        rec["broker_net_buy_profiles"]=sum(b["classification"]=="persistent_net_buy" for b in p.get("brokers",[]))
        rec["broker_net_sell_profiles"]=sum(b["classification"]=="persistent_net_sell" for b in p.get("brokers",[]))
        rec["broker_observed_profiles"]=len(p.get("brokers",[]))
        rec["broker_last_date"]=days[-1] if days else None
        for k in ("relative_strength","sector","liquidity"):rec[k+"_status"]="verified_inputs_unavailable"
        rec["production_component_coverage_pct"]=0
        output.append(rec)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (out/"stock_coverage.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
    summary={"symbols":len(output),"price_rows":sum(len(g) for g in groups.values()),"as_of":asof,"broker_sessions_as_of":len(days),"broker_window":days[-5:],"production_eligible":False,"statuses":{k:dict(Counter(str(r[k+"_status"]) for r in output)) for k in ("trend","wyckoff","volume","smc","broker","relative_strength","sector","liquidity")},"limitations":["Candidate prices and observed union calendar are not independently certified.","Broker code identity not verified; archive-only profiles.","No future broker observations used.","Existing SMC aggregation convention is not independently certified."]}
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    db.close()
if __name__=="__main__":run(*sys.argv[1:])
