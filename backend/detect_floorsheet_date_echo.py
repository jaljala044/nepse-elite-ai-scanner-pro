"""Read-only floorsheet response-date and cross-date echo detector.

It quarantines payloads whose row businessDate disagrees with the requested date,
whose rows span multiple business dates, or whose contract IDs encode another
date. It never edits source files or promotes broker evidence.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from datetime import date
from pathlib import Path

def inspect_payload(payload: dict, requested_date: str) -> dict:
    requested = date.fromisoformat(requested_date).isoformat()
    sheet = payload.get("floorsheets", {})
    rows = sheet.get("content", []) if isinstance(sheet, dict) else sheet
    if not isinstance(rows, list):
        raise ValueError("floorsheets content must be a list")
    dates, contract_date_mismatches, malformed = Counter(), [], []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            malformed.append(i); continue
        raw = str(row.get("businessDate", "")).strip()
        try:
            day = date.fromisoformat(raw).isoformat()
        except ValueError:
            malformed.append(i); continue
        dates[day] += 1
        contract = str(row.get("contractId", "")).strip()
        # NEPSE contract IDs begin with YYYYMMDD; do not infer when format differs.
        if len(contract) >= 8 and contract[:8].isdigit():
            encoded = contract[:8]
            if encoded != day.replace("-", ""):
                contract_date_mismatches.append({"row": i, "businessDate": day,
                                                 "contractDate": encoded})
    reasons = []
    if malformed: reasons.append("missing_or_invalid_business_date")
    if len(dates) > 1: reasons.append("mixed_business_dates")
    if any(d != requested for d in dates): reasons.append("requested_date_mismatch")
    if contract_date_mismatches: reasons.append("contract_id_date_mismatch")
    if not rows: reasons.append("empty_floorsheet_payload")
    return {"requested_date": requested, "row_count": len(rows),
            "business_date_counts": dict(sorted(dates.items())),
            "contract_date_mismatches": contract_date_mismatches,
            "malformed_rows": malformed, "echo_suspected": bool(reasons),
            "quarantine": bool(reasons),
            "reasons": reasons, "promotion_allowed": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--requested-date", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = inspect_payload(json.loads(a.input.read_text(encoding="utf-8")),
                             a.requested_date)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",
                        encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
if __name__ == "__main__":
    main()
