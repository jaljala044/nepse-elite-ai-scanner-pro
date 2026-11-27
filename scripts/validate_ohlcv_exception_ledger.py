#!/usr/bin/env python3
"""Validate the immutable NEPSE OHLCV exception ledger; never repairs source data."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

EXPECTED = {"invalid_ohlc": 1331, "cross_source_ohlcv_conflict": 8}
EXPECTED_DISPOSITIONS = {
    "quarantined_unresolved": 1332,
    "resolved_with_user_authoritative_evidence": 7,
}
COMMON_REQUIRED = {"exception_id", "exception_type", "symbol", "trade_date",
                   "source_repository", "disposition", "reviewer_rationale"}

def validate(json_path: Path, csv_path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(json_path.read_text(encoding="utf-8"))
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    records = data.get("exceptions", [])
    if not isinstance(records, list):
        return ["JSON exceptions must be a list"]
    if len(records) != len(rows):
        errors.append(f"JSON/CSV row count differs: {len(records)} != {len(rows)}")
    counts = Counter(r.get("exception_type") for r in records)
    if counts != Counter(EXPECTED):
        errors.append(f"exception type counts differ: {dict(counts)}")
    summary = data.get("counts", {})
    if summary.get("total_exception_records") != len(records):
        errors.append("JSON summary total does not match exception records")
    if summary.get("invalid_ohlc_rows") != EXPECTED["invalid_ohlc"]:
        errors.append("JSON invalid OHLC count does not match expected baseline")
    if summary.get("cross_source_conflict_keys") != EXPECTED["cross_source_ohlcv_conflict"]:
        errors.append("JSON conflict count does not match expected baseline")
    ids = [r.get("exception_id") for r in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate exception_id values")
    dispositions = Counter(r.get("disposition") for r in records)
    if dispositions != Counter(EXPECTED_DISPOSITIONS):
        errors.append(f"disposition counts differ: {dict(dispositions)}")
    for i, row in enumerate(records, 1):
        missing = sorted(k for k in COMMON_REQUIRED if row.get(k) in (None, ""))
        if missing:
            errors.append(f"JSON record {i} missing common fields: {missing}")
        disposition = row.get("disposition")
        if row.get("exception_type") == "invalid_ohlc" and disposition != "quarantined_unresolved":
            errors.append(f"JSON invalid-OHLC record {i} must remain quarantined_unresolved")
        if disposition == "resolved_with_user_authoritative_evidence":
            resolution = row.get("resolution_evidence") or {}
            if row.get("exception_type") != "cross_source_ohlcv_conflict":
                errors.append(f"JSON record {i} has a resolution on a non-conflict exception")
            if resolution.get("authority") != "explicit_user_designation_as_final_and_authoritative":
                errors.append(f"JSON record {i} lacks explicit user authority evidence")
            if resolution.get("canonical_promotion_allowed") is not False:
                errors.append(f"JSON record {i} incorrectly permits canonical promotion")
            if resolution.get("raw_source_rows_modified") is not False:
                errors.append(f"JSON record {i} does not affirm source immutability")
        elif disposition != "quarantined_unresolved":
            errors.append(f"JSON record {i} has unsupported disposition {disposition!r}")
        if row.get("exception_type") == "invalid_ohlc":
            for key in ("source_commit_sha", "source_path", "source_file_sha256", "source_csv_line", "raw_source_row"):
                if row.get(key) in (None, ""):
                    errors.append(f"JSON invalid-OHLC record {i} missing {key}")
        elif row.get("exception_type") == "cross_source_ohlcv_conflict":
            evidence = row.get("source_evidence") or {}
            if len(evidence) != 2:
                errors.append(f"JSON conflict record {i} must retain both source evidence entries")
            for repo, item in evidence.items():
                for key in ("commit_sha", "path", "file_sha256", "row"):
                    if item.get(key) in (None, ""):
                        errors.append(f"JSON conflict record {i} evidence {repo} missing {key}")
    for i, row in enumerate(rows, 1):
        if row.get("disposition") not in EXPECTED_DISPOSITIONS:
            errors.append(f"CSV record {i} has unsupported disposition {row.get('disposition')!r}")
    if Counter(r.get("disposition") for r in rows) != Counter(EXPECTED_DISPOSITIONS):
        errors.append("CSV disposition counts differ from expected resolved/quarantined totals")
    csv_by_id = {r.get("exception_id"): r for r in rows}
    json_by_id = {r.get("exception_id"): r for r in records}
    if set(csv_by_id) != set(json_by_id):
        errors.append("JSON and CSV exception_id sets differ")
    else:
        # Counts and ID sets alone can hide per-row swaps. Verify the key
        # identity and disposition fields remain attached to the same ID.
        parity_fields = ("exception_type", "symbol", "trade_date",
                         "source_repository", "disposition")
        for exception_id, json_row in json_by_id.items():
            csv_row = csv_by_id[exception_id]
            for field in parity_fields:
                if str(json_row.get(field, "")) != str(csv_row.get(field, "")):
                    errors.append(
                        f"JSON/CSV {field} mismatch for {exception_id}: "
                        f"{json_row.get(field)!r} != {csv_row.get(field)!r}"
                    )
    return errors

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    args = parser.parse_args()
    errors = validate(args.json, args.csv)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: 1,339 unique exceptions; 1,332 quarantined and 7 user-authoritatively resolved; source evidence retained for both sides of all 8 conflicts.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
