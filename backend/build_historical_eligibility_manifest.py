"""Produce research-only eligibility manifest; no canonical approval."""
import argparse,csv,json
from collections import Counter
def read(path):
    with open(path,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser()
    for k in ("coverage","gaps","overlay","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    coverage=read(a.coverage); gaps=read(a.gaps); overlay=read(a.overlay)
    counts=Counter(); observed=Counter(); staged=Counter(); seen=set()
    for r in overlay:
        k=(r["symbol"],r["date"])
        if k in seen or r["canonical_promotion_allowed"]!="false" or r["backtest_promotion_allowed"]!="false":raise ValueError("unsafe overlay")
        seen.add(k);observed[k[0]]+=1
        if r["review_status"]!="original_structural_only":staged[k[0]]+=1
    absent=Counter();gapkeys=set()
    for r in gaps:
        k=(r["symbol"],r["date"])
        if k in gapkeys:raise ValueError("duplicate gap")
        gapkeys.add(k)
        if k not in seen:absent[k[0]]+=1
    symbols={r["symbol"] for r in coverage}
    if len(coverage)!=281 or len(symbols)!=281 or set(observed)-symbols or set(absent)-symbols:raise ValueError("scope mismatch")
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f)
        w.writerow(["symbol","reference_dates","research_observations","staged_candidates","remaining_absent","structural_120_bar_gate","canonical_approval","backtest_eligible","blockers"])
        for r in coverage:
            s=r["symbol"];n=observed[s];m=absent[s]
            if n+m!=120 or n!=int(r["original_valid"])+int(r["staged_candidates"]) or staged[s]!=int(r["staged_candidates"]) or m!=int(r["remaining_absent"]):raise ValueError("coverage mismatch")
            gate=n>=120
            counts["structural_120_bar_gate_pass" if gate else "structural_120_bar_gate_fail"]+=1
            blockers=["canonical_review_pending","source_rights_pending","official_session_calendar_pending","warmup_not_assessed","independent_strategy_validation_pending"]
            if staged[s]:blockers.append("recovery_candidate_review_pending")
            if m:blockers.append("absent_observation_disposition_pending")
            w.writerow([s,120,n,staged[s],m,str(gate).lower(),"false","false",";".join(blockers)])
    print(json.dumps(dict(counts),sort_keys=True))
if __name__=="__main__":main()
