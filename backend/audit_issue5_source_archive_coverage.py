"""Inventory unclassified project-session gaps in the pinned full OHLCV archive audit.

A date gap is not proof of a missing trade: no-trade, suspension, lifecycle and
source-omission explanations remain unresolved until independent evidence exists.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

REPOSITORIES = (
    "jaljala044/nepse-smc-data",
    "jaljala044/nepse-history-starter",
)
OPEN_STATUSES = {"project_accepted_open", "verified_open", "verified_exceptional_open"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(audit_json: Path, calendar_csv: Path, universe_csv: Path) -> tuple[dict, list[dict]]:
    audit = json.loads(audit_json.read_text(encoding="utf-8"))
    with calendar_csv.open(encoding="utf-8-sig", newline="") as stream:
        calendar_rows = list(csv.DictReader(stream))
    with universe_csv.open(encoding="utf-8-sig", newline="") as stream:
        universe_rows = list(csv.DictReader(stream))

    required_calendar = {"date", "status"}
    required_universe = {"symbol", "instrument_type", "status"}
    if not calendar_rows or not required_calendar.issubset(calendar_rows[0]):
        raise ValueError("calendar requires date and status columns")
    if not universe_rows or not required_universe.issubset(universe_rows[0]):
        raise ValueError("universe requires symbol, instrument_type and status columns")

    calendar = {}
    for row in calendar_rows:
        day = date.fromisoformat(row["date"])
        if day.isoformat() != row["date"] or row["date"] in calendar:
            raise ValueError("calendar dates must be canonical and unique")
        calendar[row["date"]] = row["status"]
    expected_sessions = sorted(day for day, status in calendar.items() if status in OPEN_STATUSES)

    active_equities = sorted({
        row["symbol"].strip() for row in universe_rows
        if row["instrument_type"].strip().lower() == "equity"
        and row["status"].strip().lower() == "active"
        and row["symbol"].strip()
    })
    if not active_equities:
        raise ValueError("active equity universe is empty")

    gaps = []
    repository_summaries = {}
    for repository in REPOSITORIES:
        source = audit.get("repositories", {}).get(repository)
        if not isinstance(source, dict):
            raise ValueError(f"missing repository audit: {repository}")
        files = source.get("files", [])
        file_index = {}
        for item in files:
            symbol = item.get("symbol")
            if not isinstance(symbol, str) or not symbol:
                continue
            if symbol in file_index:
                raise ValueError(f"duplicate symbol file in {repository}: {symbol}")
            file_index[symbol] = item

        observed_by_symbol = {}
        for item in source.get("date_coverage", []):
            day = item.get("date")
            symbols = item.get("symbols", [])
            if not isinstance(day, str) or not isinstance(symbols, list):
                raise ValueError(f"invalid date coverage row in {repository}")
            for symbol in symbols:
                observed_by_symbol.setdefault(symbol, set()).add(day)

        missing_files = []
        symbol_summaries = []
        for symbol in active_equities:
            file_info = file_index.get(symbol)
            if file_info is None:
                missing_files.append(symbol)
                symbol_summaries.append({
                    "repository": repository, "symbol": symbol,
                    "status": "MISSING_SOURCE_FILE", "first_date": None,
                    "last_date": None, "expected_open_sessions": 0,
                    "observed_valid_dates": 0, "unclassified_gap_count": None,
                })
                continue
            first, last = file_info.get("first_date"), file_info.get("last_date")
            if not first or not last:
                symbol_summaries.append({
                    "repository": repository, "symbol": symbol,
                    "status": "NO_VALID_DATE_RANGE", "first_date": first,
                    "last_date": last, "expected_open_sessions": 0,
                    "observed_valid_dates": 0, "unclassified_gap_count": None,
                })
                continue
            start, end = date.fromisoformat(first), date.fromisoformat(last)
            if end < start:
                raise ValueError(f"invalid file date range: {repository}/{symbol}")
            expected = [day for day in expected_sessions if first <= day <= last]
            observed = observed_by_symbol.get(symbol, set())
            missing = [day for day in expected if day not in observed]
            for day in missing:
                gaps.append({
                    "repository": repository, "symbol": symbol, "trade_date": day,
                    "gap_status": "UNCLASSIFIED_NO_TRADE_OR_MISSING_OR_LIFECYCLE",
                    "canonical_promotion_allowed": False,
                    "raw_source_modified": False,
                })
            symbol_summaries.append({
                "repository": repository, "symbol": symbol, "status": "REVIEW_ONLY",
                "first_date": first, "last_date": last,
                "expected_open_sessions": len(expected),
                "observed_valid_dates": len(set(expected) & observed),
                "unclassified_gap_count": len(missing),
            })

        repository_summaries[repository] = {
            "commit_sha": source.get("commit_sha"),
            "files_audited": source.get("files_audited"),
            "file_count": source.get("file_count"),
            "total_rows": source.get("total_rows"),
            "duplicate_date_count": source.get("duplicate_date_count"),
            "out_of_order_transitions": source.get("out_of_order_transitions"),
            "invalid_row_count": source.get("invalid_row_count"),
            "download_error_count": len(source.get("download_errors", [])),
            "active_equity_files_missing": missing_files,
            "active_equity_count": len(active_equities),
            "symbol_gap_summaries": symbol_summaries,
        }

    report = {
        "audit_scope": "full_archive_date_gap_inventory_not_missing_trade_adjudication",
        "audit_json_sha256": _sha256(audit_json),
        "calendar_csv_sha256": _sha256(calendar_csv),
        "universe_csv_sha256": _sha256(universe_csv),
        "calendar_row_count": len(calendar),
        "project_open_session_count": len(expected_sessions),
        "active_equity_count": len(active_equities),
        "repository_summaries": repository_summaries,
        "unclassified_gap_count": len(gaps),
        "unclassified_gap_csv": "issue5_unclassified_equity_session_gaps.csv",
        "raw_source_values_modified": False,
        "canonical_or_training_promotion": False,
        "limitations": [
            "A project_accepted_open date is a research-baseline session, not exchange certification.",
            "An absent symbol/date may be no-trade, suspension, lifecycle boundary, source omission or missing data.",
            "No gap is classified as a missing trade without independent instrument lifecycle and no-trade evidence.",
            "The source audit's duplicate-date and out-of-order counts are structural source checks; this script does not alter source row order.",
        ],
    }
    return report, gaps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-json", required=True, type=Path)
    parser.add_argument("--calendar-csv", required=True, type=Path)
    parser.add_argument("--universe-csv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    report, gaps = build_report(args.audit_json, args.calendar_csv, args.universe_csv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "issue5_full_source_gap_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = ["repository", "symbol", "trade_date", "gap_status",
              "canonical_promotion_allowed", "raw_source_modified"]
    with (args.output_dir / report["unclassified_gap_csv"]).open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(gaps)
    print(json.dumps({
        "active_equities": report["active_equity_count"],
        "project_open_sessions": report["project_open_session_count"],
        "unclassified_gap_count": report["unclassified_gap_count"],
        "output_dir": str(args.output_dir),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
