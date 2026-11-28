"""Stage additional volume-corroborated candles without modifying original research files."""
import argparse,csv,subprocess,hashlib,io
from collections import defaultdict,Counter
from decimal import Decimal
def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser()
    for k in ("reconciliation","overlay","repo","revision","output","coverage"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    original=read(a.overlay);seen={(r["symbol"],r["date"]) for r in original}
    if len(original)!=59949 or len(seen)!=len(original):raise ValueError("original scope mismatch")
    groups=defaultdict(list)
    for r in read(a.reconciliation):
        if r["classification"]=="positive_capture_floor_volume_match":groups[r["date"]].append(r)
    if sum(map(len,groups.values()))!=260:raise ValueError("candidate scope mismatch")
    counts=Counter(r["symbol"] for r in original);added=Counter()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","date","open","high","low","close","volume","source_blob_sha","adjustment_basis","review_status","canonical_promotion_allowed","backtest_promotion_allowed"])
        for day,group in sorted(groups.items()):
            raw=subprocess.check_output(["git","-C",a.repo,"show",a.revision+":data/daily/"+day[:4]+"/"+day+".csv"])
            sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
            records=defaultdict(list)
            for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):records[r["symbol"]].append(r)
            for r in group:
                s=r["symbol"];k=(s,day)
                if k in seen or s not in counts or len(records[s])!=1 or sha!=r["capture_blob_sha"]:raise ValueError("collision or source mismatch")
                x=records[s][0];o,h,l,c,v,t=(Decimal(x[k]) for k in ("open","high","low","close","volume","turnover"))
                if x["date"]!=day or not all(z.is_finite() for z in (o,h,l,c,v,t)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<=0 or v!=v.to_integral_value() or t<0 or v!=Decimal(r["secondary_floor_volume"]) or v!=Decimal(r["capture_volume"]):raise ValueError("invalid recovery candle")
                seen.add(k);added[s]+=1
                w.writerow([s,day,o,h,l,c,v,sha,"unknown","volume_corroborated_price_review_pending","false","false"])
    with open(a.coverage,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","prior_research_rows","additional_candidates","combined_candidate_rows","remaining_reference_absences","backtest_eligible"])
        for s in sorted(counts):
            n=counts[s]+added[s]
            if n>225:raise ValueError("reference overflow")
            w.writerow([s,counts[s],added[s],n,225-n,"false"])
    print({"additional":sum(added.values()),"combined":len(seen),"absent":63225-len(seen)})
if __name__=="__main__":main()
