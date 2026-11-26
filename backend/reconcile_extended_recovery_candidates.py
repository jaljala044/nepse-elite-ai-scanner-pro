"""Reconcile positive candidates and source-quality exceptions against independent daily capture.
No OHLCV is inferred from contracts and no record is promoted.
"""
import argparse,csv,subprocess,io,hashlib
from collections import Counter,defaultdict
from decimal import Decimal,InvalidOperation
def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser()
    for k in ("gaps","repo","revision","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    groups=defaultdict(list);seen=set()
    for r in read(a.gaps):
        k=(r["symbol"],r["date"])
        if k in seen:raise ValueError("duplicate input")
        seen.add(k)
        if r["status"] in {"positive_chart_candidate","positive_floorsheet_candidate","source_quality_exception"}:groups[r["date"]].append(r)
    if sum(map(len,groups.values()))!=423:raise ValueError("unexpected review scope")
    counts=Counter()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","date","prior_status","secondary_chart_volume","secondary_floor_volume","capture_volume","capture_blob_sha","classification","canonical_promotion_allowed","backtest_promotion_allowed"])
        for day,group in sorted(groups.items()):
            raw=None;sha="";rows=defaultdict(list);valid=False
            try:raw=subprocess.check_output(["git","-C",a.repo,"show",a.revision+":data/daily/"+day[:4]+"/"+day+".csv"],stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:pass
            if raw:
                sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
                if not {"date","symbol","open","high","low","close","volume","turnover"}<=set(reader.fieldnames or []):raise ValueError("schema mismatch")
                records=list(reader);valid=bool(records) and all(x["date"]==day for x in records)
                for r in records:rows[r["symbol"]].append(r)
            for r in group:
                s=r["symbol"];v=""
                if not valid:status="capture_unavailable"
                elif not rows[s]:status="capture_symbol_absent"
                elif len(rows[s])!=1:status="capture_duplicate_symbol"
                else:
                    try:
                        x=rows[s][0];o,h,l,c,q,t=(Decimal(x[k]) for k in ("open","high","low","close","volume","turnover"))
                        if not all(z.is_finite() for z in (o,h,l,c,q,t)) or not 0<l<=min(o,c)<=max(o,c)<=h or q<0 or q!=q.to_integral_value() or t<0:raise ValueError("invalid candle")
                        v=int(q)
                        if v==0:status="capture_zero_volume"
                        elif r["floorsheet_volume"] and Decimal(r["floorsheet_volume"])==q:status="positive_capture_floor_volume_match"
                        elif r["chart_volume"] and Decimal(r["chart_volume"])==q:status="positive_capture_chart_volume_match"
                        else:status="positive_capture_volume_unreconciled"
                    except (InvalidOperation,ValueError,TypeError):status="capture_invalid_row"
                counts[status]+=1;w.writerow([s,day,r["status"],r["chart_volume"],r["floorsheet_volume"],v,sha,status,"false","false"])
    print(dict(counts))
if __name__=="__main__":main()
