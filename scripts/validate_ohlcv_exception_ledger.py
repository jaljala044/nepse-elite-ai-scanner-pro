#!/usr/bin/env python3
"""Validate the immutable NEPSE OHLCV exception ledger; never repairs source data."""
from __future__ import annotations
import argparse, csv, json, re
from collections import Counter
from pathlib import Path

EXPECTED = {"invalid_ohlc": 1331, "cross_source_ohlcv_conflict": 8}
USER_FINAL_KEYS = {("BGWT","2025-07-28"),("MEHL","2025-07-28"),("RAWA","2025-07-28"),("RHGCL","2025-07-28"),("ULHC","2025-07-28"),("API","2026-11-19"),("HRL","2026-11-19")}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMON = {"exception_id","exception_type","symbol","trade_date","source_repository","disposition","reviewer_rationale","evidence_pointer"}

def validate(json_path: Path, csv_path: Path) -> list[str]:
    errors=[]
    data=json.loads(json_path.read_text(encoding="utf-8"))
    with csv_path.open(encoding="utf-8",newline="") as stream: rows=list(csv.DictReader(stream))
    records=data.get("exceptions",[])
    if not isinstance(records,list): return ["JSON exceptions must be a list"]
    if len(records)!=len(rows): errors.append(f"JSON/CSV row count differs: {len(records)} != {len(rows)}")
    counts=Counter(r.get("exception_type") for r in records)
    if counts!=Counter(EXPECTED): errors.append(f"exception type counts differ: {dict(counts)}")
    summary=data.get("counts",{})
    for key,value in (("total_exception_records",1339),("invalid_ohlc_rows",1331),("cross_source_conflict_keys",8)):
        if summary.get(key)!=value: errors.append(f"summary {key} must equal {value}")
    ids=[r.get("exception_id") for r in records]
    if len(ids)!=len(set(ids)): errors.append("duplicate exception_id values")
    resolved=set()
    for i,r in enumerate(records,1):
        missing=sorted(k for k in COMMON if r.get(k) in (None,""))
        if missing: errors.append(f"record {i} missing common fields: {missing}")
        key=(r.get("symbol"),r.get("trade_date"))
        disposition=r.get("disposition")
        if disposition=="resolved_with_user_authoritative_evidence":
            if r.get("exception_type")!="cross_source_ohlcv_conflict" or key not in USER_FINAL_KEYS:
                errors.append(f"record {i} uses user-authoritative disposition outside the approved user-authoritative symbol/date keys")
            resolution=r.get("resolution_evidence") or {}
            if resolution.get("authority")!="explicit_user_designation_as_final_and_authoritative":
                errors.append(f"record {i} lacks explicit user-authority resolution evidence")
            if not isinstance(resolution.get("authoritative_values"),dict) or not resolution["authoritative_values"]:
                errors.append(f"record {i} lacks authoritative numeric values")
            if resolution.get("canonical_promotion_allowed") is not False:
                errors.append(f"record {i} incorrectly permits canonical promotion")
            if resolution.get("raw_source_rows_modified") is not False:
                errors.append(f"record {i} does not affirm source immutability")
            if not str(r.get("evidence_pointer","")):
                errors.append(f"record {i} lacks a user-authority evidence pointer")
            resolved.add(key)
        elif disposition!="quarantined_unresolved":
            errors.append(f"record {i} has unsupported disposition {disposition!r}")
        if r.get("exception_type")=="invalid_ohlc":
            for field in ("source_commit_sha","source_path","source_file_sha256","source_csv_line","raw_source_row","validation_rule_violated"):
                if r.get(field) in (None,""): errors.append(f"record {i} missing {field}")
            if not SHA256.fullmatch(str(r.get("source_file_sha256",""))): errors.append(f"record {i} has invalid source file SHA-256")
            if disposition!="quarantined_unresolved": errors.append(f"invalid OHLC record {i} cannot be resolved by source disagreement")
        elif r.get("exception_type")=="cross_source_ohlcv_conflict":
            evidence=r.get("source_evidence") or {}
            if len(evidence)!=2: errors.append(f"conflict record {i} must retain both source evidence entries")
            for repository,item in evidence.items():
                for field in ("commit_sha","path","file_sha256","row"):
                    if item.get(field) in (None,""): errors.append(f"conflict record {i} evidence {repository} missing {field}")
                if not SHA256.fullmatch(str(item.get("file_sha256",""))): errors.append(f"conflict record {i} evidence {repository} has invalid SHA-256")
    if resolved!=USER_FINAL_KEYS: errors.append(f"user-authoritative conflict keys differ: {sorted(resolved)}")
    expected_unresolved=1332
    if summary.get("unresolved")!=expected_unresolved: errors.append(f"summary unresolved count must equal {expected_unresolved}")
    if summary.get("resolved_with_user_authoritative_evidence")!=7: errors.append("summary user-authoritative resolution count must equal seven")
    actual_unresolved=sum(r.get("disposition")=="quarantined_unresolved" for r in records)
    actual_resolved=sum(r.get("disposition")=="resolved_with_user_authoritative_evidence" for r in records)
    if actual_unresolved!=expected_unresolved: errors.append(f"actual unresolved count must equal {expected_unresolved}, got {actual_unresolved}")
    if actual_resolved!=7: errors.append(f"actual user-authoritative resolution count must equal seven, got {actual_resolved}")
    csv_ids=[r.get("exception_id") for r in rows]
    if len(csv_ids)!=len(set(csv_ids)):
        errors.append("duplicate CSV exception_id values")
    csv_by_id={r.get("exception_id"):r for r in rows}
    if set(csv_by_id)!=set(ids):
        errors.append("JSON and CSV exception_id sets differ")
    else:
        for record in records:
            exception_id=record["exception_id"]
            csv_record=csv_by_id[exception_id]
            for field in set(record) | set(csv_record):
                value=record.get(field)
                if value is None:
                    expected=""
                elif isinstance(value,(dict,list)):
                    expected=json.dumps(value,ensure_ascii=False,sort_keys=True)
                else:
                    expected=str(value)
                actual=csv_record.get(field,"")
                if actual!=expected:
                    errors.append(f"JSON/CSV field mismatch for {exception_id}.{field}")
    return errors

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--json",required=True,type=Path)
    parser.add_argument("--csv",required=True,type=Path)
    args=parser.parse_args()
    errors=validate(args.json,args.csv)
    if errors:
        print("FAIL")
        for error in errors: print(f"- {error}")
        return 1
    print("PASS: 1,339 unique exceptions; 1,332 unresolved; seven user-authoritatively resolved conflicts.")
    return 0

if __name__=="__main__": raise SystemExit(main())
