#!/usr/bin/env python3
"""Validate repeated-adjacent OHLCV candidate-ledger integrity without modifying source data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REQUIRED = {
    "repository", "commit_sha", "path", "file_sha256", "symbol",
    "previous_date", "current_date", "previous_csv_line", "current_csv_line",
    "ohlcv", "classification",
}


def _iso_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except (TypeError, ValueError):
        return False


def _positive_or_zero_decimal(value: Any) -> Decimal:
    number = Decimal(str(value))
    if not number.is_finite():
        raise InvalidOperation("non-finite")
    return number


def validate_candidate_ledger(path: Path) -> dict[str, Any]:
    """Return structural integrity findings and row-level review flags.

    This validates the candidate artifact only. It cannot prove session status,
    publisher independence, historical completeness, or authorize promotion.
    """
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    seen: set[tuple[str, str, str, int, int]] = set()
    findings: list[dict[str, Any]] = []
    row_count = 0
    classification_counts: dict[str, int] = {}

    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED - headers)
        if missing:
            raise ValueError(f"candidate ledger missing columns: {', '.join(missing)}")

        for csv_line, row in enumerate(reader, start=2):
            row_count += 1
            source_key: tuple[str, str, str, int, int] | None = None
            try:
                previous_line = int(row["previous_csv_line"])
                current_line = int(row["current_csv_line"])
                source_key = (
                    row["repository"], row["commit_sha"], row["path"],
                    previous_line, current_line,
                )
                if source_key in seen:
                    findings.append({"ledger_line": csv_line, "code": "DUPLICATE_SOURCE_OCCURRENCE"})
                else:
                    seen.add(source_key)
                if current_line != previous_line + 1:
                    findings.append({"ledger_line": csv_line, "code": "NON_ADJACENT_SOURCE_LINES"})
                if len(row["commit_sha"]) != 40 or any(c not in "0123456789abcdef" for c in row["commit_sha"].lower()):
                    findings.append({"ledger_line": csv_line, "code": "INVALID_COMMIT_SHA"})
                if len(row["file_sha256"]) != 64 or any(c not in "0123456789abcdef" for c in row["file_sha256"].lower()):
                    findings.append({"ledger_line": csv_line, "code": "INVALID_SOURCE_FILE_SHA256"})

                prior, current = row["previous_date"], row["current_date"]
                if not _iso_date(prior) or not _iso_date(current):
                    findings.append({"ledger_line": csv_line, "code": "MALFORMED_DATE"})
                elif current == prior:
                    findings.append({"ledger_line": csv_line, "code": "DUPLICATE_ADJACENT_DATE"})
                elif current < prior:
                    findings.append({"ledger_line": csv_line, "code": "OUT_OF_ORDER_DATE"})

                try:
                    values = json.loads(row["ohlcv"])
                    open_, high, low, close = (
                        _positive_or_zero_decimal(values[name])
                        for name in ("Open", "High", "Low", "Close")
                    )
                    volume = _positive_or_zero_decimal(values["Volume"])
                    if min(open_, high, low, close) <= 0 or volume < 0 or volume != volume.to_integral_value():
                        raise InvalidOperation("invalid price or volume domain")
                    if high < max(open_, low, close) or low > min(open_, high, close):
                        findings.append({"ledger_line": csv_line, "code": "INVALID_OHLC_BOUNDS"})
                except (KeyError, TypeError, ValueError, InvalidOperation, json.JSONDecodeError):
                    findings.append({"ledger_line": csv_line, "code": "MALFORMED_OHLCV_PAYLOAD"})

                label = row["classification"] or "UNCLASSIFIED"
                classification_counts[label] = classification_counts.get(label, 0) + 1
            except (TypeError, ValueError) as exc:
                findings.append({"ledger_line": csv_line, "code": "MALFORMED_SOURCE_IDENTITY", "detail": str(exc)})

    counts: dict[str, int] = {}
    for item in findings:
        counts[item["code"]] = counts.get(item["code"], 0) + 1
    return {
        "schema_version": "1.0",
        "input_path": str(path),
        "input_sha256": digest,
        "candidate_rows": row_count,
        "unique_source_occurrences": len(seen),
        "structural_findings": len(findings),
        "finding_counts": counts,
        "source_classification_counts": classification_counts,
        "findings": findings,
        "source_data_modified": False,
        "canonical_promotion_allowed": False,
        "limitations": [
            "Candidate-ledger validation is not a full per-symbol archive continuity audit.",
            "Missing sessions require a separately evidenced session calendar and complete source rows.",
            "Project-accepted calendar status is not NEPSE first-party certification.",
            "No candidate is repaired, deleted, promoted, or used as a training label.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate_candidate_ledger(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "candidate_rows", "unique_source_occurrences", "structural_findings",
        "finding_counts", "input_sha256", "canonical_promotion_allowed"
    )}, indent=2))
    return 0 if report["structural_findings"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
