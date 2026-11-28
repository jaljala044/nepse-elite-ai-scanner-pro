"""Compare no-positive-trade candidates with a separate ShareSansar capture."""
import argparse,csv,subprocess,io,hashlib
from collections import Counter,defaultdict
from decimal import Decimal,InvalidOperation

def main():
    p=argparse.ArgumentParser()
    for k in ("gaps","repo","revision","output"): p.add_argument("--"+k,required=True)
    a=p.parse_args()
    groups=defaultdict(set)
    with open(a.gaps,newline="") as f:
        for r in csv.DictReader(f):
            if r["status"]=="no_positive_trade_in_secondary_archive":
                if r["symbol"] in groups[r["date"]]: raise ValueError("duplicate observation")
                groups[r["date"]].add(r["symbol"])
    counts=Counter()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f)
        w.writerow(["symbol","date","sharesansar_volume","blob_sha","classification","canonical_promotion_allowed"])
        for day,symbols in sorted(groups.items()):
            path="data/daily/"+day[:4]+"/"+day+".csv"
            try:
                raw=subprocess.check_output(["git","-C",a.repo,"show",a.revision+":"+path],stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                raw=None
            sha=""
            rows=defaultdict(list)
            valid=False
            if raw:
                sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
                if not {"date","symbol","open","high","low","close","volume","turnover"}<=set(reader.fieldnames or []):
                    raise ValueError("unexpected source schema")
                n=0
                valid=True
                for r in reader:
                    n+=1
                    if r["date"]!=day: valid=False
                    if r["symbol"] in symbols: rows[r["symbol"]].append(r)
                valid=valid and n>0
            for s in sorted(symbols):
                volume=""
                if not valid: status="source_unavailable_or_invalid"
                elif not rows[s]: status="absent_from_separate_daily_capture"
                elif len(rows[s])!=1: status="duplicate_symbol_in_capture"
                else:
                    try:
                        r=rows[s][0]
                        o,h,l,c,v,t=(Decimal(r[k]) for k in ("open","high","low","close","volume","turnover"))
                        if not all(x.is_finite() for x in (o,h,l,c,v,t)) or v<0 or v!=v.to_integral_value() or t<0 or not 0<l<=min(o,c)<=max(o,c)<=h: raise ValueError("invalid row")
                        volume=int(v)
                        status="positive_trade_conflict" if v>0 else "zero_volume_in_separate_daily_capture"
                    except (ValueError,InvalidOperation,TypeError): status="invalid_symbol_row"
                counts[status]+=1
                w.writerow([s,day,volume,sha,status,"false"])
    print(dict(counts))
if __name__=="__main__": main()
