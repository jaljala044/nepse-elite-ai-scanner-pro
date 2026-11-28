"""Diagnose each remaining recovery exception without fabricating replacement candles."""
import argparse,csv,subprocess,io,hashlib
from collections import Counter,defaultdict
from decimal import Decimal,InvalidOperation
def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser()
    for k in ("reconciliation","repo","revision","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args(); groups=defaultdict(list)
    for r in read(a.reconciliation):
        if r["classification"] in {"capture_invalid_row","capture_symbol_absent"}:groups[r["date"]].append(r)
    if sum(map(len,groups.values()))!=163:raise ValueError("scope mismatch")
    counts=Counter();seen=set()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","date","exception","diagnostic","source_blob_sha","secondary_chart_volume","secondary_floor_volume","next_evidence_required","canonical_promotion_allowed"])
        for day,group in sorted(groups.items()):
            raw=subprocess.check_output(["git","-C",a.repo,"show",a.revision+":data/daily/"+day[:4]+"/"+day+".csv"])
            sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
            rows=defaultdict(list)
            for x in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):rows[x["symbol"]].append(x)
            for r in group:
                s=r["symbol"];key=(s,day)
                if key in seen or sha!=r["capture_blob_sha"]:raise ValueError("duplicate or source mismatch")
                seen.add(key);issues=[]
                if not rows[s]:issues.append("symbol_absent")
                elif len(rows[s])!=1:issues.append("duplicate_symbol")
                else:
                    x=rows[s][0];nums={}
                    for k in ("open","high","low","close","volume","turnover"):
                        try:
                            z=Decimal(x[k])
                            if not z.is_finite():raise ValueError()
                            nums[k]=z
                        except (InvalidOperation,ValueError,TypeError,KeyError):issues.append("invalid_"+k)
                    if all(k in nums for k in ("open","high","low","close")):
                        o,h,l,c=(nums[k] for k in ("open","high","low","close"))
                        if min(o,h,l,c)<=0:issues.append("nonpositive_price")
                        if l>h:issues.append("low_above_high")
                        if not l<=o<=h:issues.append("open_outside_range")
                        if not l<=c<=h:issues.append("close_outside_range")
                    if "volume" in nums and (nums["volume"]<0 or nums["volume"]!=nums["volume"].to_integral_value()):issues.append("invalid_volume")
                    if "turnover" in nums and nums["turnover"]<0:issues.append("negative_turnover")
                if not issues:issues=["prior_exception_not_reproduced"]
                for i in issues:counts[i]+=1
                w.writerow([s,day,r["classification"],";".join(issues),sha,r["secondary_chart_volume"],r["secondary_floor_volume"],"dated_external_chart_and_trade_evidence","false"])
    print({"records":len(seen),"diagnostics":dict(counts)})
if __name__=="__main__":main()
