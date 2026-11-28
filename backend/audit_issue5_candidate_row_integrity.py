"""Read-only integrity audit for the pinned Issue #5 repeated-row candidate extract.

This checks only candidate pairs in the supplied artifact. It cannot certify all
source rows, missing sessions, or rows not represented in the extract.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = {
    "repository", "commit_sha", "path", "file_sha256", "symbol",
    "previous_date", "current_date", "previous_csv_line", "current_csv_line",
    "ohlcv", "classification", "review_reason",
}


def audit(path: Path) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError("missing required columns: " + ", ".join(sorted(missing)))
        rows = list(reader)

    date_keys, pair_keys = Counter(), Counter()
    source_order = defaultdict(list)
    invalid_ohlc, invalid_dates, invalid_lines = [], [], []
    non_review_only, identity_conflicts = [], []
    file_identity = {}

    for line, row in enumerate(rows, start=2):
        repo, symbol, current = row["repository"], row["symbol"], row["current_date"]
        date_keys[(repo, symbol, current)] += 1
        pair_keys[(repo, symbol, row["previous_date"], current)] += 1
        source_order[(repo, row["path"])].append(
            (row["previous_csv_line"], row["current_csv_line"], line)
        )
        identity = (row["commit_sha"], row["file_sha256"], symbol)
        old_identity = file_identity.setdefault((repo, row["path"]), identity)
        if old_identity != identity:
            identity_conflicts.append({"candidate_csv_line": line, "path": row["path"]})

        try:
            previous = date.fromisoformat(row["previous_date"])
            current_date = date.fromisoformat(current)
            if (previous.isoformat() != row["previous_date"] or
                    current_date.isoformat() != current or current_date <= previous):
                raise ValueError
        except (TypeError, ValueError):
            invalid_dates.append({
                "candidate_csv_line": line, "symbol": symbol,
                "previous_date": row["previous_date"], "current_date": current,
            })

        try:
            previous_line = int(row["previous_csv_line"])
            current_line = int(row["current_csv_line"])
            if previous_line < 2 or current_line <= previous_line:
                raise ValueError
        except (TypeError, ValueError):
            invalid_lines.append({
                "candidate_csv_line": line, "symbol": symbol,
                "previous_csv_line": row["previous_csv_line"],
                "current_csv_line": row["current_csv_line"],
            })

        try:
            values = json.loads(row["ohlcv"])
            open_price, high, low, close, volume = (
                Decimal(str(values[key]))
                for key in ("Open", "High", "Low", "Close", "Volume")
            )
            if (not all(v.is_finite() for v in
                        (open_price, high, low, close, volume)) or
                    min(open_price, high, low, close) <= 0 or volume < 0 or
                    high < max(open_price, close, low) or
                    low > min(open_price, close, high)):
                raise ValueError
        except (KeyError, TypeError, ValueError, InvalidOperation, json.JSONDecodeError):
            invalid_ohlc.append({
                "candidate_csv_line": line, "symbol": symbol, "current_date": current,
            })

        if row["classification"] != "calendar_status_unverified_review_flag":
            non_review_only.append({
                "candidate_csv_line": line, "classification": row["classification"],
            })

    duplicate_dates = [
        {"repository": key[0], "symbol": key[1], "date": key[2], "count": count}
        for key, count in date_keys.items() if count > 1
    ]
    duplicate_pairs = [
        {"repository": key[0], "symbol": key[1], "previous_date": key[2],
         "current_date": key[3], "count": count}
        for key, count in pair_keys.items() if count > 1
    ]
    order_violations = []
    for (repo, source_path), sequence in source_order.items():
        parsed = []
        for previous_line, current_line, candidate_line in sequence:
            try:
                parsed.append((int(previous_line), int(current_line), candidate_line))
            except (TypeError, ValueError):
                continue
        for prior, current_pair in zip(parsed, parsed[1:]):
            if (current_pair[0] < prior[0] or
                    current_pair[1] <= prior[1]):
                order_violations.append({
                    "repository": repo, "path": source_path,
                    "prior_candidate_line": prior[2],
                    "current_candidate_line": current_pair[2],
                })

    return {
        "audit_scope": "candidate_extract_only_not_full_source_archive",
        "input_file": path.name,
        "input_sha256": digest,
        "candidate_rows": len(rows),
        "source_files_represented": len(source_order),
        "duplicate_repository_symbol_current_date_keys": duplicate_dates,
        "duplicate_candidate_pair_keys": duplicate_pairs,
        "source_file_identity_conflicts": identity_conflicts,
        "invalid_date_order": invalid_dates,
        "invalid_source_line_pairs": invalid_lines,
        "invalid_current_ohlc": invalid_ohlc,
        "source_candidate_order_violations": order_violations,
        "non_review_only_classifications": non_review_only,
        "missing_source_rows": {
            "status": "NOT_ASSESSED",
            "reason": "candidate extract omits non-candidate source rows",
        },
        "full_source_duplicate_dates": {
            "status": "NOT_ASSESSED",
            "reason": "requires original pinned source CSVs",
        },
        "raw_source_values_modified": False,
        "canonical_or_training_promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    structural_failures = any(report[key] for key in (
        "duplicate_repository_symbol_current_date_keys",
        "duplicate_candidate_pair_keys", "source_file_identity_conflicts",
        "invalid_date_order", "invalid_source_line_pairs",
        "source_candidate_order_violations", "non_review_only_classifications",
    ))
    status = "FAIL" if structural_failures else "PASS_WITH_OHLC_FLAGS"
    print(json.dumps({
        "candidate_rows": report["candidate_rows"],
        "invalid_current_ohlc": len(report["invalid_current_ohlc"]),
        "structural_gate": status,
        "output": str(args.output),
    }))
    return 1 if structural_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
