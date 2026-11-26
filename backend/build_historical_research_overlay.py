"""Build a separate, non-promotable research overlay and stock-wise coverage report."""
import argparse,csv,hashlib,subprocess,io
from pathlib import Path
from decimal import Decimal
from collections import Counter,defaultdict
def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def blob(repo,sha):
    raw=subprocess.check_output(["git","-C",repo,"cat-file","blob",sha])
    if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=sha:raise ValueError("blob mismatch")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
def values(r,keys):
    o,h,l,c,v=(Decimal(r[k]) for k in keys)
    if not all(x.is_finite() for x in (o,h,l,c,v)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<=0 or v!=v.to_integral_value():raise ValueError("invalid candle")
    return o,h,l,c,v
def main():
    p=argparse.ArgumentParser()
    for k in ("archive","queue","sessions","candidates","secondary","gaps","output","coverage"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    q=read(a.queue); dates={r["date"] for r in read(a.sessions)}
    cand=read(a.candidates); gaps=read(a.gaps)
    if len(q)!=281 or len({r["symbol"] for r in q})!=281 or len(dates)!=120 or len(cand)!=275:raise ValueError("scope mismatch")
    source={r["symbol"]:r for r in blob(a.secondary,"08669d50c4f11bdcf638c06bdc6083baf4e28ab4")}
    symbols={r["symbol"] for r in q}; overlay={}; gapmap={}
    for r in gaps:
        k=(r["symbol"],r["date"])
        if k in gapmap or k[0] not in symbols or k[1] not in dates or r["canonical_promotion_allowed"]!="false":raise ValueError("invalid gap")
        gapmap[k]=r["classification"]
    for r in cand:
        k=(r["symbol"],r["date"])
        if k in overlay or k[0] not in symbols or k[1]!="2026-07-24" or k not in gapmap or any(r[x]!="false" for x in ("canonical_promotion_allowed","backtest_promotion_allowed")):raise ValueError("invalid overlay key")
        if r["source_blob_sha"]!="08669d50c4f11bdcf638c06bdc6083baf4e28ab4":raise ValueError("source mismatch")
        v=values(r,("open","high","low","close","volume"))
        sr=source[k[0]]
        if sr["date"]!=k[1] or v!=values(sr,("open","high","low","close","volume")) or v[-1]!=Decimal(r["floorsheet_volume"]):raise ValueError("source value mismatch")
        overlay[k]=r
    total=Counter()
    with open(a.output,"x",newline="") as f,open(a.coverage,"x",newline="") as cf:
        w=csv.writer(f); cw=csv.writer(cf)
        w.writerow(["symbol","date","open","high","low","close","volume","source_blob_sha","review_status","canonical_promotion_allowed","backtest_promotion_allowed"])
        cw.writerow(["symbol","reference_dates","original_valid","staged_candidates","remaining_absent","backtest_promotion_allowed"])
        for r in sorted(q,key=lambda r:r["symbol"]):
            s=r["symbol"];sha=r["archive_blob_sha"]; raw=blob(a.archive,sha);seen=set();n=0;added=0
            for x in raw:
                d=x["Date"]
                if d not in dates:continue
                if d in seen or (s,d) in gapmap:raise ValueError("archive collision")
                seen.add(d);v=values(x,("Open","High","Low","Close","Volume"))
                w.writerow([s,d,*v,sha,"original_structural_only","false","false"]);n+=1
            for d in sorted(dates-seen):
                k=(s,d)
                if k not in gapmap:raise ValueError("unrecorded absence")
                if k in overlay:
                    x=overlay[k];w.writerow([s,d,*values(x,("open","high","low","close","volume")),x["source_blob_sha"],x["review_status"],"false","false"]);added+=1
            cw.writerow([s,120,n,added,120-n-added,"false"])
            total.update(original=n,staged=added,remaining=120-n-added)
    if total!=Counter(original=32690,staged=275,remaining=755):raise ValueError(str(total))
    print(dict(total))
if __name__=="__main__":main()
