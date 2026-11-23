from __future__ import annotations
import argparse
import json
from pathlib import Path

from app.parquet_inspector import inspect_directory

def main():
    parser=argparse.ArgumentParser(description="Inspect downloaded NEPSE Parquet tables")
    parser.add_argument("--input",type=Path,
        default=Path("../data/raw/huggingface/AnkitSanjyal__nepse-market-data/main"))
    parser.add_argument("--max-files",type=int)
    parser.add_argument("--output",type=Path,
        default=Path("../data/reports/ankit-parquet-inspection.json"))
    args=parser.parse_args()
    result=inspect_directory(args.input,args.max_files)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({
        "files_found":result["files_found"],
        "files_inspected":result["files_inspected"],
        "files_failed":result["files_failed"],
        "tables":{
            name:{
                "files":value["files"],
                "rows":value["rows"],
                "bytes":value["bytes"],
                "schema_variants":len(value["schemas"]),
                "date_ranges":value["date_ranges"],
            } for name,value in result["tables"].items()
        },
        "output":str(args.output),
    },indent=2))
    if result["files_failed"] or result["files_inspected"]==0:
        raise SystemExit(1)

if __name__=="__main__":
    main()
