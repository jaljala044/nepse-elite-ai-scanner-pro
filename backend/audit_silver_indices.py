"""Audit normalized sector-index partitions independently from floorsheet data."""
from __future__ import annotations
import argparse
import csv
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "silver" / "indices"

def audit(root: Path) -> dict:
    files=sorted(root.glob("date=*/indices.csv"))
    sessions=[]
    seen=set()
    duplicates=[]
    errors=[]
    changes=[]
    for file in files:
        session=file.parent.name.split("=",1)[-1]
        rows=0
        date_mismatches=0
        sector_names=set()
        with file.open("r",encoding="utf-8-sig",newline="") as handle:
            for line_no,row in enumerate(csv.DictReader(handle),start=2):
                rows+=1
                if row["index_date"]!=session:
                    date_mismatches+=1
                sector=row["sector"].strip()
                key=(row["index_date"],sector.casefold())
                if key in seen:
                    duplicates.append({"date":row["index_date"],"sector":sector})
                seen.add(key)
                sector_names.add(sector)
                try:
                    opening=Decimal(row["open"])
                    high=Decimal(row["high"])
                    low=Decimal(row["low"])
                    close=Decimal(row["close"])
                    if low>min(opening,high,close) or high<max(opening,low,close):
                        errors.append({"file":str(file),"line":line_no,"sector":sector,"reason":"OHLC range"})
                    changes.append({"sector":sector,"percentage_change_pct":row["percentage_change_pct"]})
                except Exception as exc:
                    errors.append({"file":str(file),"line":line_no,"sector":sector,"reason":str(exc)})
        sessions.append({"date":session,"rows":rows,"sectors":sorted(sector_names),"date_mismatches":date_mismatches})
    ranked=[]
    for item in changes:
        try:
            ranked.append((item["sector"],Decimal(item["percentage_change_pct"])))
        except Exception:
            pass
    ranked.sort(key=lambda x:x[1],reverse=True)
    return {
        "audited_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_layer":"silver_daily_sector_indices",
        "partition_files":len(files),
        "sessions":sessions,
        "total_rows":sum(s["rows"] for s in sessions),
        "duplicate_date_sector_keys":duplicates,
        "date_mismatches":sum(s["date_mismatches"] for s in sessions),
        "ohlc_errors":errors,
        "top_sector_changes":[[name,str(value)] for name,value in ranked[:20]],
        "bottom_sector_changes":[[name,str(value)] for name,value in ranked[-20:]],
        "limitations":[
            "The source labels sector rows; it does not guarantee every index turnover field is populated.",
            "Zero-valued turnover volume and transaction-count fields are preserved rather than inferred.",
            "The audit tests structure and OHLC integrity, not exchange completeness or index methodology."
        ],
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,default=DEFAULT_DATA)
    parser.add_argument("--output",type=Path,default=ROOT/"data"/"reports"/"sector-index-audit.json")
    args=parser.parse_args()
    result=audit(args.input)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({
        "partition_files":result["partition_files"],
        "sessions":len(result["sessions"]),
        "total_rows":result["total_rows"],
        "duplicates":len(result["duplicate_date_sector_keys"]),
        "date_mismatches":result["date_mismatches"],
        "ohlc_errors":len(result["ohlc_errors"]),
        "output":str(args.output),
    },indent=2))
    if result["partition_files"]==0 or result["total_rows"]==0:
        raise SystemExit("No normalized sector-index data found")
    if result["duplicate_date_sector_keys"] or result["date_mismatches"] or result["ohlc_errors"]:
        raise SystemExit("Sector index audit failed quality gates")
if __name__=="__main__":
    main()
