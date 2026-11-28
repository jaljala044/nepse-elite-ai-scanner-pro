"""Read-only integrity audit for the pinned Issue #5 repeated-row candidate extract.

The input is a candidate-pair extract, not a full source archive. This tool
never changes source data, infers session status, or authorizes promotion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tempfile
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

REQUIRED = {
    "repository", "commit_sha", "path", "file_sha256", "symbol",
    "previous_date", "current_date", "previous_csv_line", "current_csv_line",
    "ohlcv", "classification", "review_reason",
}
REVIEW_ONLY = "calendar_status_unverified_review_flag"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_CANONICAL_LINE = re.compile(r"^[1-9][0-9]*$")


def _reject_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _ohlcv_is_valid(raw: str) -> bool:
    try:
        values = json.loads(
            raw, object_pairs_hook=_reject_duplicate_json_keys,
            parse_float=str, parse_int=str,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
        if not isinstance(values, dict) or set(values) != {
            "Open", "High", "Low", "Close", "Volume"
        }:
            return False
        numbers = {key: Decimal(value) for key, value in values.items()
                   if isinstance(value, str)}
        if len(numbers) != 5:
            return False
        open_price, high, low, close, volume = (
            numbers[key] for key in ("Open", "High", "Low", "Close", "Volume")
        )
        return (
            all(value.is_finite() for value in numbers.values())
            and min(open_price, high, low, close) > 0
            and volume >= 0
            and volume == volume.to_integral_value()
            and high >= max(open_price, close, low)
            and low <= min(open_price, close, high)
        )
    except (TypeError, ValueError, InvalidOperation, json.JSONDecodeError):
        return False


def _valid_identity(row: dict[str, Any]) -> bool:
    repository = row["repository"]
    path = row["path"]
    symbol = row["symbol"]
    if any(not isinstance(row[key], str) or not row[key].strip()
           for key in ("repository", "commit_sha", "path", "file_sha256",
                       "symbol", "review_reason")):
        return False
    if repository.strip() != repository or symbol.strip() != symbol:
        return False
    if not _SHA40.fullmatch(row["commit_sha"]):
        return False
    if not _SHA64.fullmatch(row["file_sha256"]):
        return False
    if path.strip() != path or chr(92) in path:
        return False
    posix_path = PurePosixPath(path)
    if posix_path.is_absolute() or any(part in ("", ".", "..") for part in posix_path.parts):
        return False
    return True


def audit(path: Path) -> dict:
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError("duplicate CSV header names")
        missing = REQUIRED - set(fields)
        if missing:
            raise ValueError("missing required columns: " + ", ".join(sorted(missing)))
        rows = []
        malformed_rows = []
        for line, row in enumerate(reader, start=2):
            if None in row or any(row.get(key) is None for key in fields):
                malformed_rows.append({"candidate_csv_line": line,
                                       "reason": "extra_or_missing_csv_fields"})
                continue
            rows.append((line, row))

    date_keys, pair_keys = Counter(), Counter()
    source_order = defaultdict(list)
    invalid_ohlc, invalid_dates, invalid_lines = [], [], []
    non_review_only, identity_conflicts, invalid_identities = [], [], []
    file_identity = {}

    for line, row in rows:
        repo, symbol, current = row["repository"], row["symbol"], row["current_date"]
        if not _valid_identity(row):
            invalid_identities.append({"candidate_csv_line": line, "path": row["path"],
                                       "symbol": symbol})
        date_keys[(repo, symbol, current)] += 1
        pair_keys[(repo, row["path"], symbol, row["previous_date"], current)] += 1
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
            previous_text, current_text = row["previous_csv_line"], row["current_csv_line"]
            if not _CANONICAL_LINE.fullmatch(previous_text) or not _CANONICAL_LINE.fullmatch(current_text):
                raise ValueError
            previous_line, current_line = int(previous_text), int(current_text)
            if previous_line < 2 or current_line != previous_line + 1:
                raise ValueError
        except (TypeError, ValueError):
            invalid_lines.append({
                "candidate_csv_line": line, "symbol": symbol,
                "previous_csv_line": row["previous_csv_line"],
                "current_csv_line": row["current_csv_line"],
            })

        if not _ohlcv_is_valid(row["ohlcv"]):
            invalid_ohlc.append({
                "candidate_csv_line": line, "symbol": symbol, "current_date": current,
            })

        if row["classification"] != REVIEW_ONLY or not row["review_reason"].strip():
            non_review_only.append({
                "candidate_csv_line": line, "classification": row["classification"],
                "review_reason": row["review_reason"],
            })

    duplicate_dates = [
        {"repository": key[0], "symbol": key[1], "date": key[2], "count": count}
        for key, count in date_keys.items() if count > 1
    ]
    duplicate_pairs = [
        {"repository": key[0], "path": key[1], "symbol": key[2],
         "previous_date": key[3], "current_date": key[4], "count": count}
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
            if current_pair[0] < prior[0] or current_pair[1] <= prior[1]:
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
        "malformed_csv_rows": malformed_rows,
        "source_files_represented": len(source_order),
        "invalid_source_file_identity": invalid_identities,
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
    if args.input.resolve() == args.output.resolve():
        parser.error("--output must not overwrite the input candidate artifact")
    report = audit(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\\n", dir=args.output.parent,
        prefix=f".{args.output.name}.", suffix=".tmp", delete=False,
    ) as stream:
        temporary = Path(stream.name)
        stream.write(json.dumps(report, indent=2, sort_keys=True) + "\\n")
        stream.flush()
    temporary.replace(args.output)

    structural_failures = any(report[key] for key in (
        "malformed_csv_rows", "invalid_source_file_identity",
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
