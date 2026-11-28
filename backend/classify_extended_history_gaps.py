"""Inventory extended missing dates, retaining original evidence and approval gates."""
import argparse,csv
from collections import Counter
from datetime import date
def read(p):
    with open(p,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser()
    for k in ("extended","overlay","prior-gaps","prior-crosscheck","listing","suspension","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    prior={(r["symbol"],r["date"]):r for r in read(a.prior_gaps)}
    cross={(r["symbol"],r["date"]):r for r in read(a.prior_crosscheck)}
    listing={r["symbol"]:r for r in read(a.listing)}
    susp={r["symbol"]:r for r in read(a.suspension)}
    available={(r["symbol"],r["date"]) for r in read(a.overlay)}
    counts=Counter();seen=set()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","date","classification","evidence","canonical_promotion_allowed","backtest_promotion_allowed"])
        for r in read(a.extended):
            s=r["symbol"]
            if r["invalid_225"] or r["duplicate_225"]:raise ValueError("unexpected archive quality issue")
            for d in filter(None,r["missing_225"].split(";")):
                date.fromisoformat(d); k=(s,d)
                if k in available:continue
                if k in seen:raise ValueError("duplicate missing date")
                seen.add(k);status="unresolved";evidence=""
                if k in prior:
                    status=prior[k]["classification"];evidence=prior[k]["evidence_reference"]
                    if status=="unresolved" and k in cross and cross[k]["classification"]=="absent_from_separate_daily_capture":
                        status="no_trade_candidate_cross_capture";evidence=cross[k]["blob_sha"]
                elif s in listing and d<listing[s]["scheduled_trading_start"]:
                    status="before_scheduled_commencement_candidate";evidence=listing[s]["evidence_uri"]
                elif s in susp and susp[s]["suspension_start"]<=d<=susp[s]["relisting_notice_date"]:
                    status="merger_suspension_interval_candidate";evidence=susp[s]["suspension_evidence_uri"]
                counts[status]+=1;w.writerow([s,d,status,evidence,"false","false"])
    if len(seen)!=3276:raise ValueError(str(counts))
    print(dict(counts))
if __name__=="__main__":main()
