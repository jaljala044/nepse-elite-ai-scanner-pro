#!/usr/bin/env python3
"""Rank Issue #5 weekly-closure candidate dates without adjudicating OHLCV rows.

Input rows are candidate pairs, not proof of trading or non-trading. This tool
only prioritizes date groups under the documented weekly schedule regimes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

SMC = "jaljala044/nepse-smc-data"
HISTORY = "jaljala044/nepse-history-starter"
REPOSITORIES = {SMC, HISTORY}
CLASSIFICATIONS = {"date_not_in_project_calendar_review", "date_not_listed_in_project_calendar"}
SCHEDULE_CHANGE = date(2026, 4, 6)
REQUIRED = {"repository", "symbol", "previous_date", "current_date"}
CLASSIFICATION_FIELDS = ("session_join_classification", "session_pair_classification")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_day(value: str, field: str, line: int) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid {field} at line {line}: {value!r}") from None
    if parsed.isoformat() != value:
        raise ValueError(f"noncanonical {field} at line {line}: {value!r}")
    return parsed


def load_exclusions(path: Path) -> set[str]:
    excluded: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if "current_date" not in (reader.fieldnames or []):
            raise ValueError("exclusion CSV requires current_date")
        for line, row in enumerate(reader, start=2):
            raw = row["current_date"]
            day = canonical_day(raw, "excluded current_date", line)
            if raw in excluded:
                raise ValueError(f"duplicate excluded date at line {line}: {raw}")
            excluded.add(day.isoformat())
    return excluded


def is_weekly_closure(day: date) -> bool:
    # Python weekday: Monday=0 ... Sunday=6.
    closed_weekdays = {4, 5} if day < SCHEDULE_CHANGE else {5, 6}
    return day.weekday() in closed_weekdays


def rank_batches(
    input_csv: Path,
    exclusion_csv: Path,
    limit: int = 5,
    prior_review_csv: Path | None = None,
) -> dict:
    if limit < 1:
        raise ValueError("limit must be positive")
    registered = load_exclusions(exclusion_csv)
    prior_reviewed = load_exclusions(prior_review_csv) if prior_review_csv else set()
    overlap = registered & prior_reviewed
    if overlap:
        raise ValueError(f"registered and prior-review exclusion files overlap: {sorted(overlap)}")
    excluded = registered | prior_reviewed
    groups: dict[str, dict] = {}
    seen: set[tuple[str, str, str]] = set()

    with input_csv.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or [])
        missing = REQUIRED - headers
        classification_field = next((name for name in CLASSIFICATION_FIELDS if name in headers), None)
        if missing or classification_field is None:
            missing_fields = sorted(missing | ({"session_join_classification or session_pair_classification"}
                                                if classification_field is None else set()))
            raise ValueError("candidate CSV missing columns: " + ", ".join(missing_fields))
        for line, row in enumerate(reader, start=2):
            if row[classification_field] not in CLASSIFICATIONS:
                continue
            repository = row["repository"]
            raw_symbol = row["symbol"]
            if not repository or not repository.strip():
                raise ValueError(f"blank repository at line {line}")
            if raw_symbol is None or not raw_symbol.strip():
                raise ValueError(f"blank symbol at line {line}")
            symbol = raw_symbol.strip().upper()
            if repository not in REPOSITORIES:
                raise ValueError(f"unknown repository at line {line}: {repository!r}")
            if not symbol:
                raise ValueError(f"blank symbol at line {line}")
            current = canonical_day(row["current_date"], "current_date", line)
            previous = canonical_day(row["previous_date"], "previous_date", line)
            if previous >= current:
                raise ValueError(f"previous_date must precede current_date at line {line}")
            key = (repository, symbol, current.isoformat())
            if key in seen:
                raise ValueError(f"duplicate repository/symbol/date row: {key}")
            seen.add(key)
            group = groups.setdefault(current.isoformat(), {
                "current_date": current.isoformat(),
                "previous_dates": set(),
                "symbols": set(),
                "repositories": set(),
                "candidate_pairs": 0,
            })
            group["previous_dates"].add(previous.isoformat())
            group["symbols"].add(symbol)
            group["repositories"].add(repository)
            group["candidate_pairs"] += 1

    if not groups:
        raise ValueError("candidate inventory contains no unlisted-date pairs")

    ranked = []
    for current_text, group in groups.items():
        current = date.fromisoformat(current_text)
        if current_text in excluded or not is_weekly_closure(current):
            continue
        if len(group["previous_dates"]) != 1:
            raise ValueError(f"multiple previous dates for {current_text}")
        if group["repositories"] != REPOSITORIES:
            continue
        ranked.append({
            "current_date": current_text,
            "weekday": current.strftime("%A"),
            "candidate_pairs": group["candidate_pairs"],
            "unique_symbols": len(group["symbols"]),
            "previous_date": next(iter(group["previous_dates"])),
            "repositories": len(group["repositories"]),
            "review_disposition": (
                "WEEKLY_CLOSED_BEFORE_2026-04-06"
                if current < SCHEDULE_CHANGE else "WEEKLY_CLOSED_AFTER_2026-04-06"
            ),
            "evidence_tier_limit": "T2/T3 schedule context; no first-party NEPSE payload asserted",
            "canonical_promotion_allowed": False,
        })
    ranked.sort(key=lambda row: (-row["candidate_pairs"], row["current_date"]))
    selected = ranked[:limit]
    return {
        "report_type": "issue5_weekly_closure_batch_priority_only",
        "input_csv_sha256": digest(input_csv),
        "exclusion_csv_sha256": digest(exclusion_csv),
        "prior_review_csv_sha256": digest(prior_review_csv) if prior_review_csv else None,
        "schedule_change_effective_date": SCHEDULE_CHANGE.isoformat(),
        "registered_exclusion_date_count": len(registered),
        "prior_reviewed_date_count": len(prior_reviewed),
        "excluded_date_count": len(excluded),
        "eligible_date_count": len(ranked),
        "selected_date_count": len(selected),
        "selected_candidate_pair_incidences": sum(x["candidate_pairs"] for x in selected),
        "selected": selected,
        "row_adjudication_complete": False,
        "canonical_or_training_promotion": False,
        "raw_source_modified": False,
        "interpretation": (
            "Schedule-based prioritization only. It does not establish no-trade, "
            "source omission, carry-forward, fabrication or exchange-certified closure."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--exclude", required=True, type=Path,
                        help="Registered review/closure date exclusions.")
    parser.add_argument("--exclude-reviewed", type=Path,
                        help="Additional previously reviewed dates not registered as exchange closures.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    report = rank_batches(args.input, args.exclude, args.limit, args.exclude_reviewed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "selected"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
