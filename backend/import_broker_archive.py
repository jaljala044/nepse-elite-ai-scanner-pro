"""Run from repository root with an explicitly downloaded source archive."""
import argparse,json
from pathlib import Path
from app.broker_archive_memory import connect,ingest
p=argparse.ArgumentParser()
p.add_argument("--archive-root",required=True,type=Path)
p.add_argument("--db",required=True,type=Path)
p.add_argument("--manifest",type=Path,default=Path("data/reference/broker_archive_candidate_manifest.json"))
a=p.parse_args()
m=json.loads(a.manifest.read_text())
a.db.parent.mkdir(parents=True,exist_ok=True)
db=connect(a.db)
results=[]
for c in m["sessions"]:
    try:result=ingest(db,(a.archive_root/c["path"]).read_bytes(),c)
    except (OSError,ValueError,ArithmeticError) as e:result={"status":"rejected","reason":str(e)}
    results.append({"date":c["date"],**result})
print(json.dumps({"classification":"archive_research_only","results":results,"production_eligible":False},indent=2))
db.close()
if any(r["status"]=="rejected" for r in results):raise SystemExit(1)
