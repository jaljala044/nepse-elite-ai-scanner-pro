#!/usr/bin/env python3
"""Read-only full outer join for distinct OHLCV exception-ledger scopes.

Joins by normalized (symbol, ISO trade date), but preserves every original
record, source locator, exception ID and rule. Duplicate keys are reported;
they are never collapsed into a single disposition.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _read_rows(path: Path, *, source_name: str) -> tuple[list[dict[str, Any]], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            headers = next(reader, None)
            if not headers or any(not str(name or "").strip() for name in headers):
                raise ValueError(f"{source_name}: CSV header is missing or contains blank columns")
            if len(headers) != len(set(headers)):
                raise ValueError(f"{source_name}: CSV contains duplicate column names")
            rows = []
            for ordinal, values in enumerate(reader, start=2):
                if len(values) != len(headers):
                    raise ValueError(f"{source_name}: malformed CSV field count at data row {ordinal}")
                rows.append(dict(zip(headers, values)))
    except (csv.Error, UnicodeDecodeError) as exc:
        raise ValueError(f"{source_name}: malformed UTF-8 CSV: {exc}") from exc
    if not rows:
        raise ValueError(f"{source_name}: CSV has no data rows")
    return rows, digest


def _field(row: dict[str, Any], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normal_key(row: dict[str, Any]) -> tuple[str, str] | None:
    symbol = _field(row, "symbol", "ticker", "security_symbol").upper()
    day = _field(row, "trade_date", "date", "session_date")
    if not symbol or not DATE_RE.fullmatch(day):
        return None
    try:
        from datetime import date
        if date.fromisoformat(day).isoformat() != day:
            return None
    except ValueError:
        return None
    return symbol, day


def _identity(row: dict[str, Any], source: str, ordinal: int) -> dict[str, Any]:
    return {
        "scope": source,
        "exception_id": _field(row, "exception_id", "flag_id", "record_id"),
        "source_repository": _field(row, "source_repository", "repository", "repo"),
        "source_path": _field(row, "source_path", "path", "file_path"),
        "source_file_sha256": _field(row, "source_file_sha256", "file_sha256", "sha256"),
        "source_csv_line": _field(row, "source_csv_line", "csv_line", "line", "row_number"),
        "exception_type": _field(row, "exception_type", "flag_type", "rule_code"),
        "validation_rule": _field(row, "validation_rule_violated", "rule", "reason", "error"),
        "input_row_ordinal": ordinal,
        "raw_record": row,
    }


def reconcile(left_path: Path, right_path: Path, *, left_name: str, right_name: str) -> dict[str, Any]:
    if not left_name.strip() or not right_name.strip() or left_name == right_name:
        raise ValueError("scope names must be non-empty and distinct")
    left_rows, left_hash = _read_rows(left_path, source_name=left_name)
    right_rows, right_hash = _read_rows(right_path, source_name=right_name)
    groups: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {left_name: [], right_name: []}
    )
    invalid_keys: list[dict[str, Any]] = []
    for source_name, rows in ((left_name, left_rows), (right_name, right_rows)):
        for ordinal, row in enumerate(rows, start=2):
            key = _normal_key(row)
            identity = _identity(row, source_name, ordinal)
            if key is None:
                invalid_keys.append({"scope": source_name, "input_row_ordinal": ordinal,
                                     "reason": "missing_or_invalid_symbol_or_iso_trade_date",
                                     "raw_record": row})
                continue
            groups[key][source_name].append(identity)

    joined = []
    for (symbol, day), sides in sorted(groups.items()):
        left = sides[left_name]
        right = sides[right_name]
        status = "overlap" if left and right else "left_only" if left else "right_only"
        joined.append({
            "symbol": symbol, "trade_date": day, "join_status": status,
            "left_record_count": len(left), "right_record_count": len(right),
            "left_duplicate_key": len(left) > 1, "right_duplicate_key": len(right) > 1,
            "left_exact_duplicate_rows": sum(count - 1 for count in Counter(
                json.dumps(x["raw_record"], sort_keys=True, ensure_ascii=False) for x in left
            ).values()),
            "right_exact_duplicate_rows": sum(count - 1 for count in Counter(
                json.dumps(x["raw_record"], sort_keys=True, ensure_ascii=False) for x in right
            ).values()),
            "left_rule_multiplicity": dict(sorted(Counter(x["validation_rule"] or x["exception_type"] for x in left).items())),
            "right_rule_multiplicity": dict(sorted(Counter(x["validation_rule"] or x["exception_type"] for x in right).items())),
            "left_records": left, "right_records": right,
        })

    left_duplicate_keys = sum(len(item[left_name]) > 1 for item in groups.values())
    right_duplicate_keys = sum(len(item[right_name]) > 1 for item in groups.values())
    status_counts = Counter(item["join_status"] for item in joined)
    summary = {
        "left_scope": left_name, "right_scope": right_name,
        "left_input_sha256": left_hash, "right_input_sha256": right_hash,
        "left_input_rows": len(left_rows), "right_input_rows": len(right_rows),
        "valid_join_keys": len(joined), "overlap_keys": status_counts["overlap"],
        "left_only_keys": status_counts["left_only"], "right_only_keys": status_counts["right_only"],
        "left_duplicate_keys": left_duplicate_keys, "right_duplicate_keys": right_duplicate_keys,
        "left_exact_duplicate_rows": sum(item["left_exact_duplicate_rows"] for item in joined),
        "right_exact_duplicate_rows": sum(item["right_exact_duplicate_rows"] for item in joined),
        "invalid_key_rows": len(invalid_keys),
        "left_duplicate_rows_beyond_first": sum(max(0, len(v[left_name])-1) for v in groups.values()),
        "right_duplicate_rows_beyond_first": sum(max(0, len(v[right_name])-1) for v in groups.values()),
        "rule_multiplicity_preserved": True,
        "raw_inputs_modified": False,
        "canonical_promotion_allowed": False,
        "limitations": [
            "Matching symbol/date is a scope overlap, not proof that two flags identify the same raw source row.",
            "Source identities and all raw CSV fields are retained for manual reconciliation.",
            "The two input scopes are not interchangeable; overlap does not subtract one scope from the other.",
            "No invalidity is resolved and no OHLCV value is changed or promoted.",
        ],
        "joined_records": joined,
        "invalid_key_records": invalid_keys,
    }
    return summary


def write_outputs(report: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    if json_path.resolve() == csv_path.resolve():
        raise ValueError("JSON and CSV output paths must be different")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fields = ["symbol", "trade_date", "join_status", "left_record_count", "right_record_count",
              "left_duplicate_key", "right_duplicate_key", "left_rule_multiplicity",
              "right_rule_multiplicity", "left_records", "right_records"]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in report["joined_records"]:
            writer.writerow({k: json.dumps(item[k], ensure_ascii=False, sort_keys=True)
                             if isinstance(item[k], (dict, list)) else item[k] for k in fields})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True, type=Path, help="Issue #4 1,339-row ledger CSV")
    parser.add_argument("--right", required=True, type=Path, help="SMC #56 1,368-row invariant ledger CSV")
    parser.add_argument("--left-name", default="issue4_1339")
    parser.add_argument("--right-name", default="smc_issue56_1368")
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--csv-output", required=True, type=Path)
    args = parser.parse_args()
    report = reconcile(args.left, args.right, left_name=args.left_name, right_name=args.right_name)
    write_outputs(report, args.json_output, args.csv_output)
    print(json.dumps({k: v for k, v in report.items() if k not in {"joined_records", "invalid_key_records"}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
