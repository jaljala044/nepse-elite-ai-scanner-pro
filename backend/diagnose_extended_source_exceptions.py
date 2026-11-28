"""Diagnose rejected daily candles and absent symbols without repairing prices by inference."""
import argparse,csv,io,subprocess,hashlib
from collections import Counter,defaultdict
from decimal import Decimal,InvalidOperation
def load(repo,revision,path):
    try:b=subprocess.check_output(["git","-C",repo,"show",revision+":"+path],stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:return [],""
    sha=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    return list(csv.DictReader(io.StringIO(b.decode("utf-8-sig")))),sha
def diagnose(r):
    flags=[]
    vals={}
    for k in ("open","high","low","close","volume","turnover"):
        try:
            v=Decimal(r[k])
            if not v.is_finite():raise ValueError()
            vals[k]=v
        except (KeyError,TypeError,InvalidOperation,ValueError):flags.append("invalid_"+k)
    if len(vals)==6:
        o,h,l,c,v,t=(vals[k] for k in ("open","high","low","close","volume","turnover"))
        if min(o,h,l,c)<=0:flags.append("nonpositive_price")
        if h<max(o,c,l):flags.append("high_below_candle")
        if l>min(o,c,h):flags.append("low_above_candle")
        if v<0 or v!=v.to_integral_value():flags.append("invalid_volume")
        if t<0:flags.append("negative_turnover")
    return ";".join(flags) or "no_structural_error"
def main():
    p=argparse.ArgumentParser()
    for k in ("reconciliation","repo","revision","secondary","secondary-revision","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args();groups=defaultdict(list)
    with open(a.reconciliation,newline="") as f:
        for r in csv.DictReader(f):
            if r["classification"] in {"capture_invalid_row","capture_symbol_absent"}:groups[r["date"]].append(r)
    if sum(map(len,groups.values()))!=163:raise ValueError("scope mismatch")
    counts=Counter();seen=set()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","date","prior_status","capture_diagnosis","secondary_chart_diagnosis","secondary_chart_volume","secondary_floor_volume","capture_blob_sha","secondary_blob_sha","canonical_promotion_allowed","backtest_promotion_allowed"])
        for day,group in sorted(groups.items()):
            rows,sha=load(a.repo,a.revision,"data/daily/"+day[:4]+"/"+day+".csv")
            secondary,ssha=load(a.secondary,a.secondary_revision,"ohlc_unadjusted_stock/unadj_"+day+".csv")
            by=defaultdict(list);sec=defaultdict(list)
            for r in rows:by[r["symbol"]].append(r)
            for r in secondary:sec[r["symbol"]].append(r)
            for r in group:
                s=r["symbol"];key=(s,day)
                if key in seen or sha!=r["capture_blob_sha"]:raise ValueError("duplicate or source mismatch")
                seen.add(key)
                flags=diagnose(by[s][0]) if len(by[s])==1 else ("symbol_absent" if not by[s] else "duplicate_symbol")
                # Secondary chart does not publish turnover; evaluate only candle fields.
                sf=diagnose({**sec[s][0],"turnover":"0"}) if len(sec[s])==1 else ("symbol_absent" if not sec[s] else "duplicate_symbol")
                counts[flags]+=1
                w.writerow([s,day,r["classification"],flags,sf,r["secondary_chart_volume"],r["secondary_floor_volume"],sha,ssha,"false","false"])
    print(dict(counts))
if __name__=="__main__":main()
