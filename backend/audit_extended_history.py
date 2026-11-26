"""Extended observed-date archive audit; no canonical or strategy approval."""
import argparse,csv,hashlib,subprocess
from collections import Counter
from audit_priority_equity_continuity import audit

def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser()
    for k in ("archive","queue","sessions","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    q=read(a.queue); sessions=read(a.sessions)
    dates=sorted(r["date"] for r in sessions if r["classification"]=="primary_positive_trade_observation" and r["closure_overlap"]=="false" and int(r["total_trades"])>0 and int(r["volume"])>0)
    if len(dates)!=225 or len(set(dates))!=225 or len(q)!=281 or len({r["symbol"] for r in q})!=281:raise ValueError("scope mismatch")
    counts=Counter()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","archive_blob_sha","reference_dates","valid_225","valid_latest_140","missing_225","invalid_225","duplicate_225","structural_140_gate","backtest_promotion_allowed"])
        for r in q:
            sha=r["archive_blob_sha"]
            raw=subprocess.check_output(["git","-C",a.archive,"cat-file","blob",sha])
            if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=sha:raise ValueError("blob mismatch")
            v,m,i,d=audit(raw.decode("utf-8-sig"),dates)
            v140,*_=audit(raw.decode("utf-8-sig"),dates[-140:])
            counts.update(valid=v,missing=len(m.split(";")) if m else 0,invalid=len(i.split(";")) if i else 0,duplicate=len(d.split(";")) if d else 0)
            counts["latest140_original_complete" if v140==140 else "latest140_original_incomplete"]+=1
            w.writerow([r["symbol"],sha,225,v,v140,m,i,d,str(v140==140).lower(),"false"])
    print(dict(counts))
if __name__=="__main__":main()
