"""Generate archive-only rolling broker reports; no missing-date imputation."""
import csv,json,sys
from pathlib import Path
from app.broker_archive_memory import connect,profile,rotation
db=connect(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
days=[r[0] for r in db.execute("SELECT day FROM archive_sessions ORDER BY day")]
symbols=[r[0] for r in db.execute("SELECT DISTINCT symbol FROM archive_broker ORDER BY symbol")]
summary={"classification":"archive_research_only","sessions":days,"symbols":len(symbols),"records":db.execute("SELECT COUNT(*) FROM archive_broker").fetchone()[0],"windows":{},"production_eligible":False,"calendar_verified":False,"identity_verified":False}
for n in (1,5,21,63,126,252):
    if len(days)<n:
        summary["windows"][str(n)]={"status":"insufficient_archive_sessions"};continue
    records=[];flips=[]
    for symbol in symbols:
        p=profile(db,symbol,days[-n:])
        for b in p.get("brokers",[]):
            records.append({"symbol":symbol,**b,"top3_gross_share_pct":p["top3_gross_share_pct"],"first_session":days[-n],"last_session":days[-1]})
        if len(days)>=2*n:
            prior=profile(db,symbol,days[-2*n:-n])
            for f in rotation(prior,p).get("direction_changes",[]):flips.append({"symbol":symbol,**f})
    for name,rows in [(f"window_{n}.csv",records),(f"rotation_{n}.csv",flips)]:
        if rows:
            with (out/name).open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary["windows"][str(n)]={"status":"observed_archive_sessions_only","rows":len(records),"rotation_rows":len(flips),"persistent_net_buy":sum(r["classification"]=="persistent_net_buy" for r in records),"persistent_net_sell":sum(r["classification"]=="persistent_net_sell" for r in records),"first":days[-n],"last":days[-1]}
(out/"summary.json").write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
