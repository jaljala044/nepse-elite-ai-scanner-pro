from __future__ import annotations
import argparse
import json
from pathlib import Path
from app.ankit_warehouse import load_ankit_warehouse

def main():
    parser=argparse.ArgumentParser(description="Load Ankit NEPSE Parquet tables into a source-separated DuckDB warehouse")
    parser.add_argument("--input",type=Path,
        default=Path("../data/raw/huggingface/AnkitSanjyal__nepse-market-data/main"))
    parser.add_argument("--database",type=Path,
        default=Path("../data/warehouse/nepse-analytics.duckdb"))
    parser.add_argument("--report",type=Path,
        default=Path("../data/reports/ankit-warehouse-load.json"))
    args=parser.parse_args()
    result=load_ankit_warehouse(args.input,args.database,args.report)
    print(json.dumps({
        "tables":{k:{"status":v.get("status"),"rows":v.get("quality",{}).get("rows"),
                     "qc":v.get("quality")} for k,v in result["tables"].items()},
        "overlap_reconciliation":result["overlap_reconciliation"],
        "database":str(args.database),
        "report":str(args.report),
    },indent=2))
    quality_errors=[]
    for table, info in result["tables"].items():
        if info.get("status") != "loaded":
            continue
        q=info.get("quality",{})
        if q.get("duplicate_key_groups",0):
            quality_errors.append(f"{table}: duplicate keys")
        if q.get("bad_ohlc_rows",0) or q.get("bad_trade_values",0):
            quality_errors.append(f"{table}: invalid OHLC/trade values")
        if q.get("amount_arithmetic_errors_over_npr_1",0):
            quality_errors.append(f"{table}: quantity×rate amount mismatches")
    if quality_errors:
        raise SystemExit("; ".join(quality_errors))

if __name__=="__main__":
    main()
