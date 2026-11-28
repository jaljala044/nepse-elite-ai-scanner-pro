"""Extended research inventory: original price basis unknown; recovery separate; no promotion."""
import argparse,csv,hashlib,subprocess,io
from collections import Counter,defaultdict
from datetime import date,timedelta
from decimal import Decimal
def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def rawblob(repo,sha):
    b=subprocess.check_output(["git","-C",repo,"cat-file","blob",sha])
    if hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()!=sha:raise ValueError("hash mismatch")
    return list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))
def candle(r,keys):
    o,h,l,c,v=(Decimal(r[k]) for k in keys)
    if not all(x.is_finite() for x in (o,h,l,c,v)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<=0 or v!=v.to_integral_value():raise ValueError("invalid candle")
    return o,h,l,c,v
def sunday(d):
    return (d-timedelta(days=(d.weekday()+1)%7)).isoformat()
def main():
    p=argparse.ArgumentParser()
    for k in ("archive","queue","sessions","recovery","output","warmup"):p.add_argument("--"+k,required=True)
    a=p.parse_args();q=read(a.queue);dates=sorted(r["date"] for r in read(a.sessions) if r["classification"]=="primary_positive_trade_observation" and r["closure_overlap"]=="false" and int(r["total_trades"])>0 and int(r["volume"])>0)
    rec=read(a.recovery); recovery={}
    for r in rec:
        k=(r["symbol"],r["date"])
        if k in recovery or k[1] not in dates or any(r[x]!="false" for x in ("canonical_promotion_allowed","backtest_promotion_allowed")):raise ValueError("invalid recovery")
        recovery[k]=r
    if len(q)!=281 or len({r["symbol"] for r in q})!=281 or len(dates)!=225 or len(set(dates))!=225 or len(recovery)!=275:raise ValueError("scope mismatch")
    counts=Counter();latest=set(dates[-140:])
    with open(a.output,"x",newline="") as f,open(a.warmup,"x",newline="") as g:
        w=csv.writer(f);v=csv.writer(g)
        w.writerow(["symbol","date","open","high","low","close","volume","source_id","source_blob_sha","adjustment_basis","week_start_sunday","review_status","canonical_promotion_allowed","backtest_promotion_allowed"])
        v.writerow(["symbol","original_bars","recovery_candidates","latest140_observations","latest140_count_gate","weekly_buckets_excluding_latest","monthly_buckets_excluding_latest","price_basis_verified","backtest_eligible"])
        for r in q:
            s=r["symbol"];sha=r["archive_blob_sha"];seen=set();original=0;staged=0
            for x in rawblob(a.archive,sha):
                d=x["Date"]
                if d not in dates:continue
                if d in seen or (s,d) in recovery:raise ValueError("collision")
                seen.add(d);w.writerow([s,d,*candle(x,("Open","High","Low","Close","Volume")),"original_archive",sha,"unknown",sunday(date.fromisoformat(d)),"structural_only","false","false"]);original+=1
            for d in dates:
                x=recovery.get((s,d))
                if x:
                    seen.add(d);w.writerow([s,d,*candle(x,("open","high","low","close","volume")),"sharesansar_candidate",x["source_blob_sha"],"unknown",sunday(date.fromisoformat(d)),x["review_status"],"false","false"]);staged+=1
            n=len(seen&latest);weeks=max(0,len({sunday(date.fromisoformat(d)) for d in seen})-1);months=max(0,len({d[:7] for d in seen})-1)
            v.writerow([s,original,staged,n,str(n==140).lower(),weeks,months,"false","false"])
            counts.update(original=original,staged=staged,absent=225-len(seen),latest140_pass=int(n==140),monthly10_count_pass=int(months>=10))
    if counts["original"]!=59674 or counts["staged"]!=275:raise ValueError(str(counts))
    print(dict(counts))
if __name__=="__main__":main()
