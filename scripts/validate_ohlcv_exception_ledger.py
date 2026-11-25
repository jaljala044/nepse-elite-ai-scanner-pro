#!/usr/bin/env python3
"""Validate the immutable NEPSE OHLCV exception ledger; never repairs source data."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

EXPECTED = {
    "invalid_ohlc": 1331,
    "cross_source_ohlcv_conflict": 8,
}
REQUIRED = {
    "exception_id", "exception_type", "symbol", "trade_date",
    "source_repository", "source_commit_sha", "source_path",
    "source_file_sha256", "disposition", "reviewer_rationale",
}

def validate(json_path: Path, csv_path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(json_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    records = data.get("exceptions", [])
    if not isinstance(records, list):
        return ["JSON exceptions must be a list"]
    if len(records) != len(rows):
        errors.append(f"JSON/CSV row count differs: {len(records)} != {len(rows)}")
    counts = Counter(r.get("exception_type") for r in records)
    if counts != Counter(EXPECTED):
        errors.append(f"exception type counts differ: {dict(counts)}")
    if data.get("counts", {}).get("total_exception_records") != len(records):
        errors.append("JSON summary total does not match exception records")
    if data.get("counts", {}).get("invalid_ohlc_rows") != EXPECTED["invalid_ohlc"]:
        errors.append("JSON invalid OHLC count does not match expected baseline")
    if data.get("counts", {}).get("cross_source_conflict_keys") != EXPECTED["cross_source_ohlcv_conflict"]:
        errors.append("JSON conflict count does not match expected baseline")
    ids = [r.get("exception_id") for r in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate exception_id values")
    for i, row in enumerate(records, 1):
        missing = sorted(k for k in REQUIRED if row.get(k) in (None, ""))
        if missing:
            errors.append(f"JSON record {i} missing required fields: {missing}")
        if row.get("disposition") != "quarantined_unresolved":
            errors.append(f"JSON record {i} is not quarantined_unresolved")
    for i, row in enumerate(rows, 1):
        if row.get("disposition") != "quarantined_unresolved":
            errors.append(f"CSV record {i} is not quarantined_unresolved")
    json_ids, csv_ids = set(ids), {r.get("exception_id") for r in rows}
    if json_ids != csv_ids:
        errors.append("JSON and CSV exception_id sets differ")
    return errors

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", required=True, type=Path)
    p.add_argument("--csv", required=True, type=Path)
    args = p.parse_args()
    errors = validate(args.json, args.csv)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: 1,339 unique unresolved exceptions; 1,331 invalid OHLC + 8 cross-source conflicts; JSON/CSV agree.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
