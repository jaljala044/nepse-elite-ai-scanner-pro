"""Research-only aggregation of observed candles; never synthesize missing sessions."""
import argparse,csv
from collections import defaultdict,Counter
from datetime import date,timedelta
from decimal import Decimal

def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def period(d,mode):
    if mode=="weekly":return (d-timedelta(days=(d.weekday()+1)%7)).isoformat()
    return d.replace(day=1).isoformat()

def aggregate(rows,dates,mode):
    expected=defaultdict(set)
    for d in dates:expected[period(d,mode)].add(d)
    grouped=defaultdict(list)
    for r in rows:grouped[(r["symbol"],period(date.fromisoformat(r["date"]),mode))].append(r)
    for (s,p),rs in sorted(grouped.items()):
        rs.sort(key=lambda r:r["date"])
        observed={date.fromisoformat(r["date"]) for r in rs}
        staged=sum(r["review_status"]!="original_structural_only" for r in rs)
        yield [s,p,rs[0]["date"],rs[-1]["date"],rs[0]["open"],max(Decimal(r["high"]) for r in rs),min(Decimal(r["low"]) for r in rs),rs[-1]["close"],sum(int(Decimal(r["volume"])) for r in rs),len(rs),len(expected[p]),len(expected[p]-observed),staged,"false","false","observed_reference_window_only;price_basis_unverified;period_completion_unverified"]

def main():
    p=argparse.ArgumentParser()
    for k in ("overlay","sessions","weekly","monthly"):p.add_argument("--"+k,required=True)
    a=p.parse_args(); rows=read(a.overlay); dates={date.fromisoformat(r["date"]) for r in read(a.sessions)}
    seen=set()
    for r in rows:
        k=(r["symbol"],r["date"])
        if k in seen or date.fromisoformat(r["date"]) not in dates or any(r[x]!="false" for x in ("canonical_promotion_allowed","backtest_promotion_allowed")):raise ValueError("unsafe input")
        seen.add(k)
        o,h,l,c,v=(Decimal(r[x]) for x in ("open","high","low","close","volume"))
        if not all(x.is_finite() for x in (o,h,l,c,v)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<=0 or v!=v.to_integral_value():raise ValueError("invalid candle")
    if len(rows)!=32965 or len(dates)!=120 or len({r["symbol"] for r in rows})!=281:raise ValueError("unexpected scope")
    total=sum(int(Decimal(r["volume"])) for r in rows)
    for mode in ("weekly","monthly"):
        out=list(aggregate(rows,dates,mode))
        if sum(r[8] for r in out)!=total or sum(r[9] for r in out)!=len(rows):raise ValueError("aggregation reconciliation failed")
        with open(getattr(a,mode),"x",newline="") as f:
            w=csv.writer(f);w.writerow(["symbol","period_start","first_observed_date","last_observed_date","open","high","low","close","volume","observed_bars","reference_dates_in_window","absent_reference_dates","staged_candidates","canonical_promotion_allowed","backtest_promotion_allowed","limitations"]);w.writerows(out)
        print(mode,{"rows":len(out),"daily_observations":len(rows),"volume":total,"reference_incomplete_periods":sum(r[11]>0 for r in out)})
if __name__=="__main__":main()
