#!/usr/bin/env python3
"""Audit preserved raw NEPSE holiday API captures without promoting calendar dates."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path


def audit_archive(root: Path) -> dict:
    reports = sorted(root.glob("*/capture-report.json"))
    years = []
    failures = []
    for report_path in reports:
        year_dir = report_path.parent
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            year = int(report["requested_year"])
            if year_dir.name[:4] != str(year):
                raise ValueError("capture directory year does not match requested_year")
            # A matching payload hash does not authenticate the publisher.
            # Bind each capture report to the official NEPSE endpoint/year.
            from urllib.parse import parse_qs, urlsplit
            source_url = report.get("source_url")
            parsed_url = urlsplit(source_url if isinstance(source_url, str) else "")
            if (parsed_url.scheme != "https"
                    or parsed_url.hostname not in {"nepalstock.com.np", "www.nepalstock.com.np"}
                    or parsed_url.path != "/api/nots/holiday/list"
                    or parsed_url.username is not None
                    or parsed_url.password is not None
                    or parsed_url.port not in (None, 443)
                    or parse_qs(parsed_url.query, keep_blank_values=True) != {"year": [str(year)]}
                    or parsed_url.fragment):
                raise ValueError("source URL is not the official NEPSE holiday endpoint for requested year")
            body_path = year_dir / "response-body.bin"
            parsed_path = year_dir / "parsed-response.json"
            if not body_path.is_file():
                raise ValueError("raw response-body.bin is missing")
            raw = body_path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if report.get("http_status") != 200:
                raise ValueError(f"HTTP status is not 200: {report.get('http_status')!r}")
            if not report.get("response_preserved"):
                raise ValueError("capture report does not mark response_preserved=true")
            if digest != report.get("response_sha256"):
                raise ValueError("raw response SHA-256 does not match capture report")
            if len(raw) != report.get("response_bytes"):
                raise ValueError("raw response byte count does not match capture report")
            payload = json.loads(raw)
            if not isinstance(payload, list):
                raise ValueError("holiday API response must be a JSON list")
            if not parsed_path.is_file():
                raise ValueError("parsed-response.json is missing")
            parsed_copy = json.loads(parsed_path.read_text(encoding="utf-8"))
            if parsed_copy != payload:
                raise ValueError("parsed response differs from the preserved raw response")
            dates = []
            for index, item in enumerate(payload):
                if not isinstance(item, dict):
                    raise ValueError(f"record {index} is not an object")
                value = item.get("holidayDate")
                if not isinstance(value, str):
                    raise ValueError(f"record {index} has no holidayDate")
                day = date.fromisoformat(value)
                if day.year != year:
                    raise ValueError(f"record {index} date {value} is outside requested year {year}")
                dates.append(value)
            counts = Counter(dates)
            duplicate_dates = [
                {"date": day, "record_count": count,
                 "descriptions": [item.get("holidayDescription") for item in payload
                                  if item.get("holidayDate") == day]}
                for day, count in sorted(counts.items()) if count > 1
            ]
            if len(payload) != report.get("parsed_record_count"):
                raise ValueError("parsed record count does not match capture report")
            years.append({
                "year": year,
                "http_status": 200,
                "record_count": len(payload),
                "unique_date_count": len(counts),
                "duplicate_date_row_count": len(payload) - len(counts),
                "duplicate_dates": duplicate_dates,
                "first_date": min(dates) if dates else None,
                "last_date": max(dates) if dates else None,
                "response_bytes": len(raw),
                "response_sha256": digest,
                "instrument_type_ids": sorted({str(item.get("instrumentTypeId")) for item in payload}),
                "active_statuses": sorted({str(item.get("activeStatus")) for item in payload}),
                "integrity_status": "valid",
            })
        except Exception as exc:
            failures.append({"capture_report": str(report_path), "error": str(exc)})
    years.sort(key=lambda row: row["year"])
    return {
        "schema_version": 1,
        "capture_root": str(root),
        "capture_count": len(reports),
        "valid_year_count": len(years),
        "years": years,
        "total_record_count": sum(row["record_count"] for row in years),
        "total_unique_dates_within_years": sum(row["unique_date_count"] for row in years),
        "total_duplicate_date_rows": sum(row["duplicate_date_row_count"] for row in years),
        "failures": failures,
        "failure_count": len(failures),
        "canonical_calendar_promotion_allowed": False,
        "policy": "raw_capture_integrity_only; no date is promoted and no unlisted date is inferred open",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path,
                        default=Path("data/evidence/raw/nepse/holiday-api-authenticated"))
    parser.add_argument("--output", type=Path,
                        default=Path("data/reports/nepse-holiday-api-archive-audit.json"))
    args = parser.parse_args()
    result = audit_archive(args.input_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
    print(json.dumps({
        "capture_count": result["capture_count"],
        "valid_year_count": result["valid_year_count"],
        "total_record_count": result["total_record_count"],
        "total_duplicate_date_rows": result["total_duplicate_date_rows"],
        "failure_count": result["failure_count"],
        "canonical_calendar_promotion_allowed": False,
    }, indent=2))
    return 0 if result["capture_count"] and not result["failure_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
