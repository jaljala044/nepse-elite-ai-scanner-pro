#!/usr/bin/env python3
"""Build a review-only ledger from preserved NEPSE holiday API records.

These rows are closure-evidence candidates, not verified trading-session
calendar entries. The endpoint's null scope fields and incomplete-looking
annual ranges are retained explicitly; absence from the endpoint is never
interpreted as an open session.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from audit_nepse_holiday_api_archive import audit_archive

FIELDS = (
    "candidate_id", "source_year", "holiday_date", "holiday_description",
    "source_record_index", "source_id", "source_url", "http_status",
    "retrieved_at_utc", "raw_response_path", "raw_response_sha256",
    "instrument_type_id", "active_status", "scope_assessment",
    "annual_completeness", "same_date_record_count", "disposition",
    "canonical_calendar_promotion_allowed",
)

INCOMPLETE_LOOKING_YEARS = {2018, 2019}


def build_closure_candidate_ledger(root: Path, expected_years: set[int] | None = None) -> dict:
    audit = audit_archive(root)
    if audit["failure_count"]:
        raise ValueError(f"holiday archive integrity failures: {audit['failures']}")
    reports = sorted(root.glob("*/capture-report.json"))
    observed_years = set()
    rows = []
    for report_path in reports:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        year = int(report["requested_year"])
        observed_years.add(year)
        body_path = report_path.parent / "response-body.bin"
        payload = json.loads(body_path.read_bytes())
        date_counts: dict[str, int] = {}
        for item in payload:
            day = item["holidayDate"]
            date_counts[day] = date_counts.get(day, 0) + 1
        for index, item in enumerate(payload):
            day = item["holidayDate"]
            instrument_type_id = item.get("instrumentTypeId")
            active_status = item.get("activeStatus")
            rows.append({
                "candidate_id": f"{year}:{day}:{index:04d}",
                "source_year": year,
                "holiday_date": day,
                "holiday_description": item.get("holidayDescription") or "",
                "source_record_index": index,
                "source_id": report.get("source_id") or "NEPSE_OFFICIAL_HOLIDAY_API",
                "source_url": report.get("source_url") or f"https://nepalstock.com.np/api/nots/holiday/list?year={year}",
                "http_status": report.get("http_status"),
                "retrieved_at_utc": report.get("retrieved_at_utc") or "",
                "raw_response_path": body_path.as_posix(),
                "raw_response_sha256": report["response_sha256"],
                "instrument_type_id": instrument_type_id,
                "active_status": active_status,
                "scope_assessment": "unknown_null_source_fields" if instrument_type_id is None and active_status is None else "requires_independent_scope_review",
                "annual_completeness": "incomplete_looking_range" if year in INCOMPLETE_LOOKING_YEARS else "not_established",
                "same_date_record_count": date_counts[day],
                "disposition": "review_only_closure_evidence_candidate",
                "canonical_calendar_promotion_allowed": False,
            })
    if expected_years is not None and observed_years != expected_years:
        missing = sorted(expected_years - observed_years)
        unexpected = sorted(observed_years - expected_years)
        raise ValueError(f"captured year set mismatch; missing={missing}, unexpected={unexpected}")
    rows.sort(key=lambda row: (row["source_year"], row["holiday_date"], row["source_record_index"]))
    unique_keys = {(row["source_year"], row["holiday_date"]) for row in rows}
    duplicate_rows = [row for row in rows if row["same_date_record_count"] > 1]
    return {
        "schema_version": 1,
        "source_capture_root": root.as_posix(),
        "captured_years": sorted(observed_years),
        "capture_year_count": len(observed_years),
        "closure_evidence_candidate_count": len(rows),
        "unique_year_date_count": len(unique_keys),
        "duplicate_date_row_count": len(rows) - len(unique_keys),
        "duplicate_candidate_ids": [row["candidate_id"] for row in duplicate_rows],
        "annual_completeness": {
            str(year): ("incomplete_looking_range" if year in INCOMPLETE_LOOKING_YEARS else "not_established")
            for year in sorted(observed_years)
        },
        "scope_policy": "API instrumentTypeId and activeStatus are retained verbatim; null values mean scope is unknown.",
        "calendar_policy": "These are review-only closure evidence candidates. They do not verify all-market scope, annual completeness, open sessions, or trading sessions. Absence from this list is not evidence of an open session.",
        "canonical_calendar_promotion_allowed": False,
        "rows": rows,
    }


def write_outputs(result: dict, json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(result["rows"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("data/evidence/raw/nepse/holiday-api-authenticated"))
    parser.add_argument("--output-json", type=Path, default=Path("data/reports/nepse-holiday-closure-candidates-2015-2026.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("data/reports/nepse-holiday-closure-candidates-2015-2026.csv"))
    parser.add_argument("--require-years", action="store_true", help="Require every capture year from 2015 through 2026")
    args = parser.parse_args()
    expected = set(range(2015, 2027)) if args.require_years else None
    result = build_closure_candidate_ledger(args.input_root, expected)
    write_outputs(result, args.output_json, args.output_csv)
    print(json.dumps({key: result[key] for key in (
        "capture_year_count", "closure_evidence_candidate_count", "unique_year_date_count",
        "duplicate_date_row_count", "canonical_calendar_promotion_allowed",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
