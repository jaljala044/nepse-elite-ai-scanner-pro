"""Check remaining exceptions against pinned company-wise price history; review only."""
import argparse,csv,io,hashlib,subprocess
from collections import defaultdict,Counter
from decimal import Decimal,InvalidOperation
def main():
    p=argparse.ArgumentParser()
    for k in ("diagnostics","repo","revision","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args();groups=defaultdict(list)
    with open(a.diagnostics,newline="") as f:
        for r in csv.DictReader(f):groups[r["symbol"]].append(r)
    if sum(map(len,groups.values()))!=163:raise ValueError("scope mismatch")
    counts=Counter();seen=set()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","date","open","high","low","close","volume","source_blob_sha","classification","canonical_promotion_allowed","backtest_promotion_allowed"])
        for s,group in sorted(groups.items()):
            raw=None;sha="";by=defaultdict(list)
            try:raw=subprocess.check_output(["git","-C",a.repo,"show",a.revision+":data/company-wise/"+s+"/prices.csv"],stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:pass
            if raw:
                sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
                if not {"date","open","high","low","ltp","qty","turnover"}<=set(reader.fieldnames or []):raise ValueError("schema mismatch")
                for r in reader:by[r["date"]].append(r)
            for r in group:
                day=r["date"];key=(s,day);vals=[""]*5
                if key in seen:raise ValueError("duplicate input")
                seen.add(key)
                if raw is None:status="source_unavailable"
                elif not by[day]:status="date_absent"
                elif len(by[day])!=1:status="duplicate_source_date"
                else:
                    x=by[day][0]
                    try:
                        o,h,l,c,v,t=(Decimal(x[k]) for k in ("open","high","low","ltp","qty","turnover"))
                        vals=[o,h,l,c,v]
                        if not all(z.is_finite() for z in (o,h,l,c,v,t)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<0 or v!=v.to_integral_value() or t<0:raise ValueError("invalid candle")
                        if v==0:status="zero_volume"
                        elif r["secondary_floor_volume"] and v==Decimal(r["secondary_floor_volume"]):status="valid_candle_floor_volume_match"
                        else:status="valid_candle_volume_unreconciled"
                    except (InvalidOperation,ValueError,TypeError):status="invalid_source_candle"
                counts[status]+=1;w.writerow([s,day,*vals,sha,status,"false","false"])
    print(dict(counts))
if __name__=="__main__":main()
