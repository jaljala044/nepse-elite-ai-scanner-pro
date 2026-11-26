"""Research-only indicator history inventory; counts are not strategy eligibility."""
import argparse,csv
from collections import defaultdict,Counter
from datetime import date
def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser()
    for k in ("overlay","weekly","monthly","manifest","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    daily=defaultdict(list); weekly=defaultdict(list); monthly=defaultdict(list)
    for path,dst,key in [(a.overlay,daily,"date"),(a.weekly,weekly,"period_start"),(a.monthly,monthly,"period_start")]:
        seen=set()
        for r in read(path):
            k=(r["symbol"],r[key])
            if k in seen or any(r[x]!="false" for x in ("canonical_promotion_allowed","backtest_promotion_allowed")):raise ValueError("unsafe input")
            date.fromisoformat(k[1]);seen.add(k);dst[k[0]].append(r)
    manifest=read(a.manifest)
    symbols={r["symbol"] for r in manifest}
    if len(manifest)!=281 or len(symbols)!=281 or set(daily)!=symbols:raise ValueError("scope mismatch")
    counts=Counter()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","daily_bars","daily_idpat_21_count_gate","daily_smc_10_count_gate","daily_pivot_5_count_gate","weekly_reference_buckets_excluding_latest","monthly_reference_buckets_excluding_latest","weekly_iso_smc_gate","monthly_smc_10_count_gate","warmup_120_plus_20_count_gate","backtest_eligible","limitations"])
        for r in manifest:
            s=r["symbol"];n=len(daily[s])
            if n!=int(r["research_observations"]):raise ValueError("manifest count mismatch")
            wk=max(0,len(weekly[s])-1);mo=max(0,len(monthly[s])-1)
            gates=[n>=21,n>=10,n>=5,mo>=10,n>=140]
            for k,v in zip(("idpat21","smc10","pivot5","monthly10","research140"),gates):counts[k+"_pass" if v else k+"_fail"]+=1
            w.writerow([s,n,*[str(x).lower() for x in gates[:3]],wk,mo,"not_assessed_week_convention_mismatch",str(gates[3]).lower(),str(gates[4]).lower(),"false","counts_only;corporate_actions_unverified;session_calendar_unverified;weekly_convention_mismatch;120_plus_20_is_proposed_research_gate"])
    print(dict(counts))
if __name__=="__main__":main()
