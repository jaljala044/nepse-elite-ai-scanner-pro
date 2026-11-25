#!/usr/bin/env python3
"""Validate the recovered 616-date candidate set without promoting open sessions."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

from app.session_calendar import schedule_candidate

EXPECTED_START = date(2024, 3, 4)
EXPECTED_END = date(2026, 11, 20)
EXPECTED_COUNTS = {"2024": 189, "2025": 225, "2026": 202}
EXPECTED_INDEX_MISSING = {"2025-04-03", "2026-11-20"}
EXPECTED_INDEX_ROW_CHECKED = {
    "2026-02-05", "2026-03-10", "2026-03-12", "2026-03-30",
    "2026-04-05", "2026-07-02", "2026-08-17",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def audit_candidates(repo_root: Path) -> dict:
    evidence = repo_root / "data/evidence/candidates"
    candidate_rows = read_rows(evidence / "nepse-616-session-date-candidates-2024-2026.csv")
    index_rows = read_rows(evidence / "nepse-616-session-index-crosscheck-2024-2026.csv")
    secondary_rows = read_rows(evidence / "nepse-session-secondary-report-crosscheck.csv")

    dates = [date.fromisoformat(row["date"]) for row in candidate_rows]
    date_strings = [day.isoformat() for day in dates]
    if len(dates) != 616:
        raise ValueError(f"expected 616 candidate rows, found {len(dates)}")
    if len(set(dates)) != len(dates):
        raise ValueError("candidate date list contains duplicates")
    if min(dates) != EXPECTED_START or max(dates) != EXPECTED_END:
        raise ValueError("candidate date window does not match the pinned manifest window")
    if any(row["status"] != "candidate_unverified" for row in candidate_rows):
        raise ValueError("candidate rows must remain candidate_unverified")
    if len({row["source_revision"] for row in candidate_rows}) != 1:
        raise ValueError("candidate rows must use one pinned source revision")

    year_counts = dict(sorted(Counter(day.strftime("%Y") for day in dates).items()))
    if year_counts != EXPECTED_COUNTS:
        raise ValueError(f"unexpected annual candidate counts: {year_counts}")

    weekday_violations = [
        day.isoformat() for day in dates if not schedule_candidate(day)[0]
    ]
    if weekday_violations:
        raise ValueError(f"candidate dates violate the documented weekday regimes: {weekday_violations[:10]}")

    if len(index_rows) != len(candidate_rows):
        raise ValueError("index cross-check row count differs from candidate row count")
    index_by_date = {row["date"]: row for row in index_rows}
    if set(index_by_date) != set(date_strings):
        raise ValueError("index cross-check dates do not exactly match candidate dates")
    index_missing = {
        day for day, row in index_by_date.items()
        if row["index_status"] == "index_file_missing"
    }
    if index_missing != EXPECTED_INDEX_MISSING:
        raise ValueError(f"unexpected missing index dates: {sorted(index_missing)}")
    index_found_count = sum(
        row["index_status"] == "index_file_found" for row in index_rows
    )
    if index_found_count != 614:
        raise ValueError(f"expected 614 index date files, found {index_found_count}")
    row_checked = {
        day for day, row in index_by_date.items()
        if row["index_row_check"] == "one_NEPSE_index_row_checked"
    }
    if row_checked != EXPECTED_INDEX_ROW_CHECKED:
        raise ValueError("the seven market-summary-gap dates do not all have the expected row-level check")

    secondary_dates = {row["date"] for row in secondary_rows}
    if secondary_dates != EXPECTED_INDEX_MISSING:
        raise ValueError(f"secondary report dates do not match the two index gaps: {sorted(secondary_dates)}")
    if any(row["evidence_status"] != "candidate_session_reported" for row in secondary_rows):
        raise ValueError("secondary report evidence status changed unexpectedly")

    holiday_root = repo_root / "data/evidence/raw/nepse/holiday-api-authenticated"
    holiday_dates: set[str] = set()
    holiday_record_count = 0
    for year in ("2024", "2025", "2026"):
        parsed = holiday_root / f"{year}-11-25" / "parsed-response.json"
        payload = json.loads(parsed.read_text(encoding="utf-8"))
        for item in payload:
            value = item.get("holidayDate")
            if value:
                holiday_dates.add(date.fromisoformat(value).isoformat())
                holiday_record_count += 1
    holiday_overlaps = sorted(set(date_strings) & holiday_dates)
    if holiday_overlaps:
        raise ValueError(f"candidate dates overlap explicit NEPSE holiday API records: {holiday_overlaps}")

    weekday_counts = dict(sorted(Counter(day.strftime("%A") for day in dates).items()))
    return {
        "schema_version": 1,
        "status": "passed",
        "candidate_count": len(candidate_rows),
        "unique_candidate_date_count": len(set(dates)),
        "date_window": {"start": min(dates).isoformat(), "end": max(dates).isoformat()},
        "annual_candidate_counts": year_counts,
        "weekday_counts": weekday_counts,
        "weekday_regime_violation_count": len(weekday_violations),
        "index_date_file_count": index_found_count,
        "index_date_file_missing": sorted(index_missing),
        "index_row_level_checked_dates": sorted(row_checked),
        "secondary_session_report_dates": sorted(secondary_dates),
        "holiday_api_record_count": holiday_record_count,
        "candidate_holiday_overlap_count": len(holiday_overlaps),
        "candidate_holiday_overlaps": holiday_overlaps,
        "canonical_calendar_promotion_allowed": False,
        "training_allowed": False,
        "decision": "candidate reconstruction only; exact original calendar identity and primary open-session evidence remain unresolved",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = audit_candidates(args.repo_root.resolve())
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else args.repo_root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
