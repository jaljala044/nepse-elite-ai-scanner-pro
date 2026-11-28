"""Compare disputed opening prices with previous observed closes and secondary candles.
Prior-close matches are diagnostic only, not replacement opening prices.
"""
import argparse,csv,io,subprocess,hashlib
from decimal import Decimal,InvalidOperation
from collections import Counter,defaultdict
def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def source(repo,rev,path):
    try:b=subprocess.check_output(["git","-C",repo,"show",rev+":"+path],stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:return [],""
    return list(csv.DictReader(io.StringIO(b.decode("utf-8-sig")))),hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def num(x):
    try:
        v=Decimal(x)
        return v if v.is_finite() else None
    except (InvalidOperation,TypeError,ValueError):return None
def main():
    p=argparse.ArgumentParser()
    for k in ("diagnostics","overlay","repo","revision","secondary","secondary-revision","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args();history=defaultdict(list)
    for r in read(a.overlay):history[r["symbol"]].append(r)
    groups=defaultdict(list)
    for r in read(a.diagnostics):groups[r["date"]].append(r)
    if sum(map(len,groups.values()))!=163:raise ValueError("unexpected scope")
    counts=Counter();seen=set()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","date","capture_open","capture_high","capture_low","capture_close","prior_observed_date","prior_observed_close","secondary_open","secondary_high","secondary_low","secondary_close","capture_blob_sha","secondary_blob_sha","classification","canonical_promotion_allowed","backtest_promotion_allowed"])
        for day,group in sorted(groups.items()):
            rows,sha=source(a.repo,a.revision,"data/daily/"+day[:4]+"/"+day+".csv")
            sec,ssha=source(a.secondary,a.secondary_revision,"ohlc_unadjusted_stock/unadj_"+day+".csv")
            by=defaultdict(list);sb=defaultdict(list)
            for r in rows:by[r["symbol"]].append(r)
            for r in sec:sb[r["symbol"]].append(r)
            for r in group:
                s=r["symbol"];k=(s,day)
                if k in seen or sha!=r["capture_blob_sha"] or ssha!=r["secondary_blob_sha"]:raise ValueError("source or key mismatch")
                seen.add(k);x=by[s][0] if len(by[s])==1 else {};y=sb[s][0] if len(sb[s])==1 else {}
                prev=max((z for z in history[s] if z["date"]<day),key=lambda z:z["date"],default={})
                o=num(x.get("open"));pc=num(prev.get("close"));so=num(y.get("open"))
                if not x:status="capture_absent"
                elif o is not None and pc is not None and o==pc:status="matches_prior_observed_close"
                elif o is not None and so is not None and o==so:status="matches_secondary_open"
                else:status="opening_price_unresolved"
                counts[status]+=1
                w.writerow([s,day,*[x.get(z,"") for z in ("open","high","low","close")],prev.get("date",""),prev.get("close",""),*[y.get(z,"") for z in ("open","high","low","close")],sha,ssha,status,"false","false"])
    print(dict(counts))
if __name__=="__main__":main()
