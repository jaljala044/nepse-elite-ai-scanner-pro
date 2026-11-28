"""Cross-check unresolved equity dates against pinned secondary daily files."""
import csv
import argparse
import subprocess
import io
import hashlib
from decimal import Decimal, InvalidOperation
from collections import Counter, defaultdict
from pathlib import Path

def load(repo, revision, path):
    try:
        raw=subprocess.check_output(["git","-C",repo,"show",revision+":"+path],stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return None, ""
    sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    return csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))), sha

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gaps",required=True)
    p.add_argument("--repo",required=True)
    p.add_argument("--revision",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    with open(a.gaps,newline="") as f:
        groups=defaultdict(set)
        seen=set()
        for r in csv.DictReader(f):
            key=(r["symbol"],r["date"])
            if key in seen:
                raise ValueError("duplicate gap")
            seen.add(key)
            if r["classification"]=="unresolved":
                groups[r["date"]].add(r["symbol"])
    counts=Counter()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f)
        w.writerow(["symbol","date","chart_volume","floorsheet_volume","contracts","chart_blob","floorsheet_blob","status","canonical_promotion_allowed"])
        for day, symbols in sorted(groups.items()):
            chart,cs=load(a.repo,a.revision,"ohlc_unadjusted_stock/unadj_"+day+".csv")
            floor,fs=load(a.repo,a.revision,"floorsheet/floorsheet_"+day+".csv")
            cv=defaultdict(list)
            fv=Counter()
            n=Counter()
            invalid=False
            if chart is not None:
                if not {"date","symbol","volume","open","high","low","close"}<=set(chart.fieldnames or []):
                    raise ValueError("unexpected chart schema")
                for r in chart:
                    if r["date"]!=day:
                        raise ValueError("wrong chart date")
                    if r["symbol"] in symbols:
                        cv[r["symbol"]].append(r)
            if floor is not None:
                if not {"transaction","symbol","quantity","date","rate","amount"}<=set(floor.fieldnames or []):
                    raise ValueError("unexpected floor schema")
                ids=set()
                for r in floor:
                    try:
                        q=Decimal(r["quantity"]); rate=Decimal(r["rate"]); amount=Decimal(r["amount"])
                        if r["date"]!=day or not r["transaction"] or r["transaction"] in ids or not all(x.is_finite() for x in (q,rate,amount)) or q<=0 or q!=q.to_integral_value() or rate<=0 or abs(q*rate-amount)>Decimal("0.011"):
                            raise ValueError("invalid contract")
                        ids.add(r["transaction"])
                        if r["symbol"] in symbols:
                            fv[r["symbol"]]+=int(q)
                            n[r["symbol"]]+=1
                    except (ValueError,InvalidOperation,TypeError):
                        invalid=True
            for s in sorted(symbols):
                v=None
                chart_bad=len(cv[s])>1
                if len(cv[s])==1:
                    try:
                        r=cv[s][0]
                        o,h,l,c,q=(Decimal(r[k]) for k in ("open","high","low","close","volume"))
                        if not all(x.is_finite() for x in (o,h,l,c,q)) or not 0<l<=min(o,c)<=max(o,c)<=h or q<0 or q!=q.to_integral_value():
                            raise ValueError("invalid candle")
                        v=int(q)
                    except (ValueError,InvalidOperation,TypeError):
                        chart_bad=True
                if invalid or chart_bad:
                    status="source_quality_exception"
                elif v is not None and v>0:
                    status="positive_chart_candidate"
                elif floor is not None and fv[s]>0:
                    status="positive_floorsheet_candidate"
                elif chart is not None and floor is not None:
                    status="no_positive_trade_in_secondary_archive"
                else:
                    status="source_unavailable"
                counts[status]+=1
                w.writerow([s,day,v if v is not None else "",fv[s] if floor is not None and not invalid else "",n[s] if floor is not None and not invalid else "",cs,fs,status,"false"])
    print(dict(counts))

if __name__=="__main__":
    main()
