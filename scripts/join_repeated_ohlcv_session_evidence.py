#!/usr/bin/env python3
"""Join repeated-adjacent OHLCV candidates to explicit NEPSE calendar evidence.

This is an evidence annotation step, not an auto-classifier of carry-forward rows.
Weekday-derived dates remain unverified candidates when no explicit calendar row exists.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
import sys

# Allow this repository-root CLI to reuse the backend calendar validator.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.session_calendar import classify_date, load_calendar

REQUIRED = {"repository", "commit_sha", "path", "file_sha256", "symbol",
            "previous_date", "current_date", "previous_csv_line", "current_csv_line"}


def _canonical_date(value: str, *, line: int, field: str) -> date:
    """Accept only an exact YYYY-MM-DD value; reject timestamps and compact forms."""
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"line {line}: {field} must be canonical YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise ValueError(f"line {line}: {field} must be canonical YYYY-MM-DD")
    return parsed


def _validate_source_locator(row: dict[str, str], *, line: int) -> None:
    """Reject malformed source locators before emitting hash-attributed evidence."""
    for field in ("repository", "path", "symbol"):
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"line {line}: {field} must be non-empty")
    commit = row.get("commit_sha", "")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise ValueError(f"line {line}: commit_sha must be 40 hexadecimal characters")
    digest = row.get("file_sha256", "")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise ValueError(f"line {line}: file_sha256 must be 64 hexadecimal characters")
    line_values = []
    for field in ("previous_csv_line", "current_csv_line"):
        value = row.get(field, "")
        if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]*", value):
            raise ValueError(f"line {line}: {field} must be a positive integer")
        line_values.append(int(value))
    if line_values[1] <= line_values[0]:
        raise ValueError(f"line {line}: current_csv_line must follow previous_csv_line")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def join_candidates(candidate_csv: str | Path, calendar_csv: str | Path,
                    output_csv: str | Path, summary_json: str | Path) -> dict:
    candidate_path, calendar_path = Path(candidate_csv), Path(calendar_csv)
    output_path, summary_path = Path(output_csv), Path(summary_json)
    evidence = load_calendar(calendar_path)
    counts: Counter[str] = Counter()
    rows_seen = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with candidate_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError("candidate CSV missing columns: " + ",".join(sorted(missing)))
        fields = list(reader.fieldnames or []) + [
            "previous_session_classification", "current_session_classification",
            "session_pair_classification", "session_evidence_ids",
        ]
        with output_path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=fields)
            writer.writeheader()
            for line, row in enumerate(reader, 2):
                _validate_source_locator(row, line=line)
                previous = _canonical_date(row["previous_date"], line=line, field="previous_date")
                current = _canonical_date(row["current_date"], line=line, field="current_date")
                if current <= previous:
                    raise ValueError(f"line {line}: current_date must follow previous_date")
                prev = classify_date(previous, evidence)
                curr = classify_date(current, evidence)
                prev_class = prev["classification"]
                curr_class = curr["classification"]
                if prev_class in {"verified_closed", "verified_exceptional_closed"} or curr_class in {
                    "verified_closed", "verified_exceptional_closed"
                }:
                    pair = "contains_verified_closure"
                elif prev_class in {"verified_open", "verified_exceptional_open"} and curr_class in {
                    "verified_open", "verified_exceptional_open"
                }:
                    pair = "both_dates_verified_open"
                else:
                    pair = "session_evidence_incomplete"
                row.update({
                    "previous_session_classification": prev_class,
                    "current_session_classification": curr_class,
                    "session_pair_classification": pair,
                    "session_evidence_ids": "|".join(
                        item for item in (prev.get("source_id"), curr.get("source_id")) if item
                    ),
                })
                writer.writerow(row)
                counts[pair] += 1
                rows_seen += 1
    summary = {
        "schema_version": 1,
        "candidate_rows": rows_seen,
        "session_pair_classifications": dict(sorted(counts.items())),
        "candidate_csv_sha256": _sha256(candidate_path),
        "calendar_csv_sha256": _sha256(calendar_path),
        "output_csv_sha256": _sha256(output_path),
        "verified_calendar_dates": len(evidence),
        "policy": "no_weekday_or_missing-evidence inference; candidate rows remain review-only; this output does not authorize OHLCV repair, forward-fill, canonical admission, or training",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--calendar", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()
    result = join_candidates(args.candidates, args.calendar, args.out, args.summary)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
