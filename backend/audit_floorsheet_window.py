#!/usr/bin/env python3
"""Audit every dated floorsheet file in a pinned acquisition window."""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from audit_hf_floorsheet_sample import audit_floorsheet_rows, decimal_value, read_csv, sha256_file


SOCRATEAI_REQUIRED = {"transaction", "date", "symbol", "buyer", "seller", "quantity", "rate", "amount"}


def audit_socrateai_rows(rows: list[dict[str, str]], expected_date: str) -> dict[str, Any]:
    date.fromisoformat(expected_date)
    errors = []
    contracts: dict[str, list[dict[str, str]]] = defaultdict(list)
    ids = Counter()
    symbols = Counter()
    brokers = set()
    total_quantity = 0
    total_amount = Decimal(0)
    valid_numeric_rows = 0
    prefix_mismatches = 0
    for line_no, raw in enumerate(rows, 2):
        row = {str(k): (v or "").strip() for k, v in raw.items() if k is not None}
        contract = row.get("transaction", "")
        contracts[contract].append(row)
        if not contract:
            errors.append({"line": line_no, "reason": "missing_transaction"})
        if row.get("date") != expected_date:
            errors.append({"line": line_no, "reason": "date_mismatch", "actual": row.get("date")})
        if contract and re.match(r"^\d{8}", contract) and contract[:8] != expected_date.replace("-", ""):
            prefix_mismatches += 1
            errors.append({"line": line_no, "reason": "contract_date_prefix_mismatch", "transaction": contract})
        symbol = row.get("symbol", "").upper()
        if not symbol:
            errors.append({"line": line_no, "reason": "missing_symbol"})
        else:
            symbols[symbol] += 1
        for field in ("buyer", "seller"):
            try:
                broker = int(row.get(field, ""))
                if broker <= 0:
                    raise ValueError("non_positive_broker_code")
                brokers.add(str(broker))
            except ValueError:
                errors.append({"line": line_no, "reason": "invalid_broker_code", "field": field, "value": row.get(field)})
        try:
            quantity_decimal = decimal_value(row.get("quantity", ""))
            if quantity_decimal <= 0 or quantity_decimal != quantity_decimal.to_integral_value():
                raise ValueError("quantity_must_be_positive_integer")
            quantity = int(quantity_decimal)
            rate = decimal_value(row.get("rate", ""))
            amount = decimal_value(row.get("amount", ""))
            if rate <= 0 or amount <= 0:
                raise ValueError("rate_and_amount_must_be_positive")
            calculated = Decimal(quantity) * rate
            if calculated != amount:
                errors.append({
                    "line": line_no,
                    "reason": "quantity_rate_amount_mismatch",
                    "quantity": quantity,
                    "rate": str(rate),
                    "amount": str(amount),
                    "calculated_amount": str(calculated),
                })
            total_quantity += quantity
            total_amount += amount
            valid_numeric_rows += 1
        except (ValueError, InvalidOperation, TypeError) as exc:
            errors.append({"line": line_no, "reason": "invalid_numeric_fields", "detail": str(exc)})

    duplicate_contracts = []
    for contract, group in contracts.items():
        if contract and len(group) > 1:
            duplicate_contracts.append({"transaction": contract, "rows": len(group)})
    row_pass = bool(rows) and not errors and not duplicate_contracts
    return {
        "expected_date": expected_date,
        "row_count": len(rows),
        "valid_numeric_rows": valid_numeric_rows,
        "row_validation_errors": errors,
        "row_validation_error_count": len(errors),
        "duplicate_contracts": duplicate_contracts,
        "unique_contract_numbers": len(contracts),
        "contract_date_prefix_mismatch_count": prefix_mismatches,
        "total_quantity": total_quantity,
        "total_amount": str(total_amount),
        "unique_symbols": len(symbols),
        "symbol_row_counts": dict(sorted(symbols.items())),
        "unique_broker_codes": len(brokers),
        "execution_time_available": False,
        "row_validation_pass": row_pass,
    }


def audit_window(
    manifest_path: str | Path,
    date_list_path: str | Path,
    source_schema: str,
    min_files: int,
    allow_missing_dates: bool,
) -> dict[str, Any]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    date_values = []
    with Path(date_list_path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if "date" not in (reader.fieldnames or []):
            raise ValueError("date list must contain date column")
        for line, row in enumerate(reader, 2):
            day = str(row.get("date") or "").strip()
            try:
                date.fromisoformat(day)
            except ValueError as exc:
                raise ValueError(f"{date_list_path}:{line}: invalid date {day!r}") from exc
            date_values.append(day)
    if not date_values:
        raise ValueError("date list is empty")
    if len(date_values) != len(set(date_values)):
        raise ValueError("date list contains duplicate dates")
    expected_dates = sorted(date_values)
    files = manifest.get("files", [])
    if manifest.get("download_error_count", 0):
        raise ValueError("acquisition manifest contains download errors")
    files_by_date = {str(row["date"]): row for row in files}
    if len(files_by_date) != len(files):
        raise ValueError("acquisition manifest contains duplicate dates")
    unexpected_dates = sorted(set(files_by_date) - set(expected_dates))
    if unexpected_dates:
        raise ValueError("acquisition manifest contains unexpected dates: " + ", ".join(unexpected_dates))
    missing_dates = sorted(set(expected_dates) - set(files_by_date))
    if missing_dates and not allow_missing_dates:
        raise ValueError("missing acquired files: " + ", ".join(missing_dates))
    if len(files) < min_files:
        raise ValueError(f"only {len(files)} files available; minimum required is {min_files}")

    daily = []
    file_errors = []
    repository_root = Path.cwd().resolve()
    for day, entry in sorted(files_by_date.items()):
        path = Path(entry["local_path"])
        try:
            if not path.is_file():
                raise FileNotFoundError(path)
            actual_hash = sha256_file(path)
            if entry.get("local_sha256") and actual_hash != entry["local_sha256"]:
                raise ValueError("local SHA-256 differs from acquisition manifest")
            rows, fields = read_csv(path)
            if source_schema == "urek":
                summary = audit_floorsheet_rows(rows, day)
            else:
                absent = SOCRATEAI_REQUIRED - set(fields)
                if absent:
                    raise ValueError("missing SocrateAI fields: " + ", ".join(sorted(absent)))
                summary = audit_socrateai_rows(rows, day)
            daily.append({
                "date": day,
                "path": str(path),
                "repository_path": path.relative_to(repository_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": actual_hash,
                "columns": fields,
                "summary": summary,
            })
        except Exception as exc:
            file_errors.append({"date": day, "path": str(path), "error": f"{type(exc).__name__}: {exc}"})

    invalid_days = [row["date"] for row in daily if not row["summary"]["row_validation_pass"]]
    total_rows = sum(row["summary"]["row_count"] for row in daily)
    total_quantity = sum(row["summary"]["total_quantity"] for row in daily)
    total_amount = sum((Decimal(row["summary"]["total_amount"]) for row in daily), Decimal(0))
    if file_errors or invalid_days:
        status = "row_validation_failure"
    elif missing_dates:
        status = "partial_source_coverage"
    else:
        status = "complete_row_validated_window"
    return {
        "source_repository": manifest.get("repository") or manifest.get("repo_id"),
        "source_commit": manifest.get("resolved_commit_sha") or manifest.get("commit_sha"),
        "source_schema": source_schema,
        "date_list_path": str(date_list_path),
        "expected_date_count": len(expected_dates),
        "acquired_date_count": len(files),
        "audited_date_count": len(daily),
        "missing_date_count": len(missing_dates),
        "missing_dates": missing_dates,
        "invalid_day_count": len(invalid_days),
        "invalid_days": invalid_days,
        "file_error_count": len(file_errors),
        "file_errors": file_errors,
        "total_rows": total_rows,
        "total_quantity": total_quantity,
        "total_amount": str(total_amount),
        "daily_reports": daily,
        "row_validation_status": status,
        "canonical_promotion_allowed": False,
        "limitations": [
            "File date is not accepted as a verified NEPSE session date; calendar gate is separate.",
            "This audit validates available rows and does not prove the source archive contains every transaction.",
            "No rows are deduplicated, corrected or merged.",
            "Execution times absent from the SocrateAI schema remain unavailable and are not synthesized.",
            "Source availability timestamps and market event timestamps must remain separate for point-in-time analysis.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--date-list", type=Path, required=True)
    parser.add_argument("--source-schema", choices=("urek", "socrateai"), required=True)
    parser.add_argument("--min-files", type=int, default=1)
    parser.add_argument("--allow-missing-dates", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_window(args.manifest, args.date_list, args.source_schema, args.min_files, args.allow_missing_dates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "source_schema": report["source_schema"],
        "expected_dates": report["expected_date_count"],
        "acquired_dates": report["acquired_date_count"],
        "audited_dates": report["audited_date_count"],
        "missing_dates": report["missing_date_count"],
        "invalid_days": report["invalid_day_count"],
        "file_errors": report["file_error_count"],
        "total_rows": report["total_rows"],
        "row_validation_status": report["row_validation_status"],
    }, indent=2))
    if report["file_error_count"] or report["invalid_day_count"]:
        raise SystemExit(2)
    if report["missing_date_count"] and not args.allow_missing_dates:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
