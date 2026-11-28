#!/usr/bin/env python3
"""Rank unlisted candidate CURRENT dates from the pinned Issue #5 artifact.

Counts one candidate source occurrence per current_date. It does not count the
same date again when it appears as a previous endpoint in another candidate.
Schedule context is T2/T3 only and never changes exchange-session disposition.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

EXPECTED_CANDIDATE_ROWS = 196_784
EXPECTED_CSV_SHA256 = "a343c1a4c87fb305415b0ce2b62427753250152e74d69cdbb0558b13153cbef1"
ALREADY_REVIEWED_DATES = {
    # Current-main top-five package (2026-11-28)
    "2026-06-27", "2026-06-28", "2026-02-21", "2026-05-31", "2026-06-20",
    # Earlier Issue #5 review packages #348, #349 and their current-main port #356
    "2026-06-21", "2026-06-06", "2026-06-07", "2026-03-20", "2026-03-21",
    "2026-05-03", "2026-06-13", "2026-06-14", "2026-05-16", "2026-05-17",
}
REQUIRED_FIELDS = {
    "repository", "commit_sha", "path", "file_sha256", "symbol",
    "previous_date", "current_date", "previous_csv_line", "current_csv_line",
    "current_session_classification",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _schedule(day: date) -> tuple[bool, str]:
    # Keep in sync with backend/app/session_calendar.py schedule_candidate.
    if day <= date(2020, 3, 22):
        closed = {4, 5}
        note = "Sunday-Thursday regular; Friday odd-lot only; Saturday closed"
    elif day <= date(2020, 5, 11):
        closed = set()
        note = "COVID lockdown; trading suspended"
        return False, note
    elif day <= date(2020, 5, 13):
        return True, "Exceptional restricted sessions; schedule context only"
    elif day <= date(2020, 6, 28):
        return False, "COVID lockdown; trading suspended"
    elif day <= date(2022, 5, 14):
        closed = {4, 5}
        note = "Sunday-Thursday regular; Friday odd-lot only; Saturday closed"
    elif day <= date(2022, 6, 14):
        closed = {5, 6}
        note = "Monday-Friday regular; Saturday/Sunday closed"
    elif day <= date(2022, 9, 16):
        closed = {5}
        note = "Sunday-Thursday regular; Friday half-day; Saturday closed"
    elif day <= date(2026, 4, 5):
        closed = {4, 5}
        note = "Sunday-Thursday regular; Friday/Saturday closed"
    else:
        closed = {5, 6}
        note = "Monday-Friday regular; Saturday/Sunday closed"
    return day.weekday() not in closed, note


def rank_batches(candidate_csv: Path, *, top_n: int = 5,
                 excluded_dates: set[str] | None = None,
                 expected_sha256: str | None = None) -> dict[str, Any]:
    digest = sha256_file(candidate_csv)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError(f"candidate CSV SHA-256 mismatch: {digest}")
    excluded = ALREADY_REVIEWED_DATES | (excluded_dates or set())
    aggregates: dict[str, dict[str, Any]] = {}
    seen_occurrences: set[tuple[str, str, str, str, str]] = set()
    row_count = 0
    with candidate_csv.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED_FIELDS - set(reader.fieldnames or [])
        if missing:
            raise ValueError("candidate CSV missing columns: " + ", ".join(sorted(missing)))
        for line, row in enumerate(reader, start=2):
            row_count += 1
            occurrence = (row["repository"], row["commit_sha"], row["path"],
                          row["previous_csv_line"], row["current_csv_line"])
            if occurrence in seen_occurrences:
                raise ValueError(f"duplicate source occurrence at input line {line}: {occurrence}")
            seen_occurrences.add(occurrence)
            try:
                prior = date.fromisoformat(row["previous_date"])
                current = date.fromisoformat(row["current_date"])
            except ValueError as exc:
                raise ValueError(f"invalid candidate date at input line {line}") from exc
            if prior.isoformat() != row["previous_date"] or current.isoformat() != row["current_date"]:
                raise ValueError(f"noncanonical ISO date at input line {line}")
            try:
                prior_line, current_line = int(row["previous_csv_line"]), int(row["current_csv_line"])
            except ValueError as exc:
                raise ValueError(f"invalid source line number at input line {line}") from exc
            if current_line != prior_line + 1:
                raise ValueError(f"non-adjacent source line numbers at input line {line}")
            if row["current_session_classification"] != "not_listed_in_project_calendar":
                continue
            day = row["current_date"]
            if day in excluded:
                continue
            item = aggregates.setdefault(day, {
                "date": day, "candidate_pair_count": 0, "symbols": set(),
                "source_pair_counts": Counter(), "source_symbols": defaultdict(set),
            })
            item["candidate_pair_count"] += 1
            item["symbols"].add(row["symbol"].strip().upper())
            item["source_pair_counts"][row["repository"]] += 1
            item["source_symbols"][row["repository"]].add(row["symbol"].strip().upper())

    if row_count != EXPECTED_CANDIDATE_ROWS:
        raise ValueError(f"candidate row count mismatch: expected {EXPECTED_CANDIDATE_ROWS}, got {row_count}")
    ranked = sorted(aggregates.values(),
                    key=lambda item: (-item["candidate_pair_count"], item["date"]))[:top_n]
    results = []
    for item in ranked:
        day = date.fromisoformat(item["date"])
        expected_open, note = _schedule(day)
        results.append({
            "date": item["date"],
            "candidate_pair_count": item["candidate_pair_count"],
            "distinct_symbols": len(item["symbols"]),
            "smc_pair_count": item["source_pair_counts"]["jaljala044/nepse-smc-data"],
            "history_starter_pair_count": item["source_pair_counts"]["jaljala044/nepse-history-starter"],
            "smc_symbols": len(item["source_symbols"]["jaljala044/nepse-smc-data"]),
            "history_starter_symbols": len(item["source_symbols"]["jaljala044/nepse-history-starter"]),
            "weekday": day.strftime("%A"),
            "schedule_context": "scheduled_open_candidate" if expected_open else "scheduled_non_session_candidate",
            "schedule_note": note,
            "exchange_session_disposition": "UNKNOWN_NO_T1_NOTICE",
            "review_tier": "T2_T3_SCHEDULE_CONTEXT_ONLY",
            "canonical_promotion_allowed": False,
        })
    return {
        "candidate_csv_sha256": digest,
        "candidate_rows_read": row_count,
        "unique_source_occurrences": len(seen_occurrences),
        "duplicate_source_occurrences": 0,
        "already_reviewed_dates_excluded": sorted(excluded),
        "ranking_basis": "current_date only; one candidate source occurrence counted once for its current endpoint",
        "top_date_batches": results,
        "total_candidate_pair_incidences": sum(x["candidate_pair_count"] for x in results),
        "all_exchange_session_dispositions": "UNKNOWN_NO_T1_NOTICE",
        "raw_source_modified": False,
        "calendar_modified": False,
        "canonical_promotion_allowed": False,
    }


def write_report(report: dict[str, Any], csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(report["top_date_batches"][0]) if report["top_date_batches"] else []
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["top_date_batches"])
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Enriched candidate CSV extracted from the pinned workflow artifact")
    parser.add_argument("--csv-output", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--expected-sha256", default=EXPECTED_CSV_SHA256)
    args = parser.parse_args()
    if args.top_n < 1:
        parser.error("--top-n must be positive")
    report = rank_batches(args.input, top_n=args.top_n, expected_sha256=args.expected_sha256)
    write_report(report, args.csv_output, args.json_output)
    print(json.dumps({k: v for k, v in report.items() if k != "top_date_batches"}, indent=2))
    for item in report["top_date_batches"]:
        print(json.dumps(item, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
