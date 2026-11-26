"""Classify audited absent observations without authorizing exclusions or promotion."""
import argparse
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

def read(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def classify(row, day, life, july, listing=None):
    if life and life["valid_from_evidence_status"] in {
        "verified_primary_notice", "verified_secondary_notice",
        "verified_secondary_first_trade_archive_match"
    } and life["valid_from"] and life["valid_from_evidence_uri"] and life["valid_from_evidence_note"]:
        if date.fromisoformat(day) < date.fromisoformat(life["valid_from"]):
            return "before_documented_first_trade_candidate", life["valid_from_evidence_uri"]
    if day == "2026-07-24" and july:
        if july["chart_volume"] and int(july["chart_volume"]) > 0:
            return "secondary_ohlcv_recovery_candidate", july["chart_evidence"]
        if july["floorsheet_volume"] and int(july["floorsheet_volume"]) > 0:
            return "positive_floorsheet_observation", july["floorsheet_evidence"]
    if listing and date.fromisoformat(day) < date.fromisoformat(listing["scheduled_trading_start"]):
        return "before_scheduled_commencement_candidate", listing["evidence_uri"]
    return "unresolved", ""

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audits", nargs="+", required=True)
    p.add_argument("--lifecycle", required=True)
    p.add_argument("--july", required=True)
    p.add_argument("--listing", required=True)
    p.add_argument("--output", required=True)
    a=p.parse_args()
    lifecycle=read(a.lifecycle)
    july=read(a.july)
    life={r["symbol"]:r for r in lifecycle}
    jmap={r["symbol"]:r for r in july}
    if len(lifecycle)!=281 or len(life)!=281 or len(july)!=281 or len(jmap)!=281 or set(life)!=set(jmap):
        raise ValueError("universe mismatch")
    listing_rows=read(a.listing)
    listings={r["symbol"]:r for r in listing_rows}
    if len(listings)!=len(listing_rows) or not set(listings)<=set(life):
        raise ValueError("invalid listing universe")
    for r in listing_rows:
        if not r["evidence_uri"].startswith("https://") or r["canonical_promotion_allowed"]!="false" or date.fromisoformat(r["scheduled_trading_start"])>date.fromisoformat(r["first_archived_date"]):
            raise ValueError("invalid listing evidence")
    seen=set()
    counts=Counter()
    result=[]
    for path in a.audits:
        for r in read(path):
            s=r["symbol"]
            if s in seen or s not in life or r["error"]:
                raise ValueError("invalid audit symbol or failed audit")
            seen.add(s)
            days=[d for d in r["missing_dates"].split(";") if d]
            invalid=[d for d in r["invalid_dates"].split(";") if d]
            dup=[d for d in r["duplicate_dates"].split(";") if d]
            if len(set(days+invalid+dup))!=len(days+invalid+dup) or int(r["valid_structural_rows"])+len(days+invalid+dup)!=120:
                raise ValueError("audit counts inconsistent")
            for day in days:
                date.fromisoformat(day)
                status,evidence=classify(r,day,life[s],jmap[s],listings.get(s))
                counts[status]+=1
                result.append([s,day,status,evidence,"false","false"])
    if seen!=set(life) or len(result)!=1030:
        raise ValueError("unexpected audit totals")
    with Path(a.output).open("x",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(["symbol","date","classification","evidence_reference","canonical_promotion_allowed","backtest_promotion_allowed"])
        w.writerows(sorted(result))
    print(json.dumps(dict(counts),sort_keys=True))

if __name__=="__main__":
    main()
