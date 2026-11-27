#!/usr/bin/env python3
"""Validate the immutable NEPSE OHLCV exception ledger; never repairs source data."""
from __future__ import annotations
import argparse, csv, json, re
from collections import Counter
from pathlib import Path

EXPECTED = {"invalid_ohlc": 1331, "cross_source_ohlcv_conflict": 8}
USER_FINAL_KEYS = {
    ("BGWT","2025-07-28"),("MEHL","2025-07-28"),("RAWA","2025-07-28"),
    ("RHGCL","2025-07-28"),("ULHC","2025-07-28"),
}
NEPSE_FIELD_KEYS = {("API","2026-11-19"),("RHGCL","2026-11-19")}
NEPSE_REQUIRED_FIELDS = {
    ("API","2026-11-19"): {"high","low","close","volume"},
    ("RHGCL","2026-11-19"): {"high","low","close","volume","trades"},
}
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
    user_resolved=set(); nepse_resolved=set()
    for i,r in enumerate(records,1):
        missing=sorted(k for k in COMMON if r.get(k) in (None,""))
        if missing: errors.append(f"record {i} missing common fields: {missing}")
        key=(r.get("symbol"),r.get("trade_date")); disposition=r.get("disposition")
        resolution=r.get("resolution_evidence") or {}
        if disposition=="resolved_with_user_authoritative_evidence":
            if r.get("exception_type")!="cross_source_ohlcv_conflict" or key not in USER_FINAL_KEYS:
                errors.append(f"record {i} uses user-authoritative disposition outside the five approved July keys")
            if resolution.get("authority")!="explicit_user_designation_as_final_and_authoritative":
                errors.append(f"record {i} lacks explicit user-authority resolution evidence")
            if not isinstance(resolution.get("authoritative_values"),dict) or not resolution["authoritative_values"]:
                errors.append(f"record {i} lacks authoritative numeric values")
            if resolution.get("canonical_promotion_allowed") is not False: errors.append(f"record {i} incorrectly permits canonical promotion")
            if resolution.get("raw_source_rows_modified") is not False: errors.append(f"record {i} does not affirm source immutability")
            user_resolved.add(key)
        elif disposition=="resolved_with_nepse_field_evidence":
            if r.get("exception_type")!="cross_source_ohlcv_conflict" or key not in NEPSE_FIELD_KEYS:
                errors.append(f"record {i} uses field-scoped NEPSE disposition outside approved keys")
            if resolution.get("authority")!="captured_nepse_source_field_scoped":
                errors.append(f"record {i} lacks field-scoped NEPSE authority")
            fields=resolution.get("supported_fields")
            if not isinstance(fields,dict) or set(fields)!=NEPSE_REQUIRED_FIELDS.get(key,set()):
                errors.append(f"record {i} has incorrect supported NEPSE fields for {key}")
            if "open" not in resolution.get("omitted_fields",[]):
                errors.append(f"record {i} must explicitly record that NEPSE response omits open")
            if resolution.get("canonical_promotion_allowed") is not False: errors.append(f"record {i} incorrectly permits canonical promotion")
            if resolution.get("raw_source_rows_modified") is not False: errors.append(f"record {i} does not affirm source immutability")
            nepse_resolved.add(key)
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
                for field in ("commit_sha","path","file_sha256","source_csv_line","row"):
                    if item.get(field) in (None,""): errors.append(f"conflict record {i} evidence {repository} missing {field}")
                if not SHA256.fullmatch(str(item.get("file_sha256",""))): errors.append(f"conflict record {i} evidence {repository} has invalid SHA-256")
                if not isinstance(item.get("source_csv_line"),int) or item["source_csv_line"]<2:
                    errors.append(f"conflict record {i} evidence {repository} has invalid source CSV line")
    if user_resolved!=USER_FINAL_KEYS: errors.append(f"user-authoritative conflict keys differ: {sorted(user_resolved)}")
    if nepse_resolved!=NEPSE_FIELD_KEYS: errors.append(f"field-scoped NEPSE conflict keys differ: {sorted(nepse_resolved)}")
    expected_unresolved=1332
    if summary.get("unresolved")!=expected_unresolved: errors.append(f"summary unresolved count must equal {expected_unresolved}")
    if summary.get("resolved_with_user_authoritative_evidence")!=5: errors.append("summary user-authoritative resolution count must equal five")
    if summary.get("resolved_with_nepse_field_evidence")!=2: errors.append("summary field-scoped NEPSE resolution count must equal two")
    actual_unresolved=sum(r.get("disposition")=="quarantined_unresolved" for r in records)
    actual_user=sum(r.get("disposition")=="resolved_with_user_authoritative_evidence" for r in records)
    actual_nepse=sum(r.get("disposition")=="resolved_with_nepse_field_evidence" for r in records)
    if actual_unresolved!=expected_unresolved: errors.append(f"actual unresolved count must equal {expected_unresolved}, got {actual_unresolved}")
    if actual_user!=5: errors.append(f"actual user-authoritative resolution count must equal five, got {actual_user}")
    if actual_nepse!=2: errors.append(f"actual field-scoped NEPSE resolution count must equal two, got {actual_nepse}")
    csv_ids=[r.get("exception_id") for r in rows]
    if len(csv_ids)!=len(set(csv_ids)): errors.append("duplicate CSV exception_id values")
    csv_by_id={r.get("exception_id"):r for r in rows}
    if set(csv_by_id)!=set(ids): errors.append("JSON and CSV exception_id sets differ")
    else:
        for record in records:
            exception_id=record["exception_id"]; csv_record=csv_by_id[exception_id]
            for field in set(record)|set(csv_record):
                value=record.get(field)
                expected="" if value is None else json.dumps(value,ensure_ascii=False,sort_keys=True) if isinstance(value,(dict,list)) else str(value)
                if csv_record.get(field,"")!=expected: errors.append(f"JSON/CSV field mismatch for {exception_id}.{field}")
    return errors

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--json",required=True,type=Path); parser.add_argument("--csv",required=True,type=Path)
    args=parser.parse_args(); errors=validate(args.json,args.csv)
    if errors:
        print("FAIL")
        for error in errors: print(f"- {error}")
        return 1
    print("PASS: 1,339 unique exceptions; 1,332 unresolved; five user-authoritative and two field-scoped NEPSE resolutions.")
    return 0

if __name__=="__main__": raise SystemExit(main())
