#!/usr/bin/env python3
"""Row-level audit of one pinned NEPSE floorsheet sample and its daily index controls."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

FLOORSHEET_REQUIRED = {
    "contract_no", "calculation_date", "time", "stock_symbol",
    "buyer", "seller", "quantity", "rate", "amount", "id",
}


def read_csv(path: str | Path) -> tuple[list[dict[str, str]], list[str]]:
    source = Path(path)
    opener = gzip.open if source.suffix.lower() == ".gz" else open
    with opener(source, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decimal_value(value: Any) -> Decimal:
    number = Decimal(str(value).replace(",", "").strip())
    if not number.is_finite():
        raise ValueError("non_finite_decimal")
    return number


def audit_floorsheet_rows(rows: list[dict[str, str]], expected_date: str) -> dict[str, Any]:
    date.fromisoformat(expected_date)
    errors: list[dict[str, Any]] = []
    contract_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    id_counts: Counter[str] = Counter()
    symbol_counts: Counter[str] = Counter()
    broker_codes: set[str] = set()
    times: list[str] = []
    null_time_count = 0
    total_quantity = 0
    total_amount = Decimal(0)
    valid_numeric_rows = 0
    prefix_mismatch_count = 0

    for line_no, raw in enumerate(rows, 2):
        row = {str(k): (v or "").strip() for k, v in raw.items() if k is not None}
        contract = row.get("contract_no", "")
        contract_groups[contract].append(row)
        identifier = row.get("id", "")
        if identifier:
            id_counts[identifier] += 1

        if not contract:
            errors.append({"line": line_no, "reason": "missing_contract_no"})
        if not identifier:
            errors.append({"line": line_no, "reason": "missing_id"})
        trade_date = row.get("calculation_date", "")
        if trade_date != expected_date:
            errors.append({"line": line_no, "reason": "calculation_date_mismatch", "actual": trade_date})
        if contract and re.match(r"^\d{8}", contract) and contract[:8] != expected_date.replace("-", ""):
            prefix_mismatch_count += 1
            errors.append({"line": line_no, "reason": "contract_date_prefix_mismatch", "contract_no": contract})

        symbol = row.get("stock_symbol", "").upper()
        if not symbol:
            errors.append({"line": line_no, "reason": "missing_stock_symbol"})
        else:
            symbol_counts[symbol] += 1

        for broker_field in ("buyer", "seller"):
            broker = row.get(broker_field, "")
            try:
                broker_number = int(broker)
                if broker_number <= 0:
                    raise ValueError("non_positive_broker_code")
                broker_codes.add(str(broker_number))
            except (TypeError, ValueError):
                errors.append({"line": line_no, "reason": "invalid_broker_code", "field": broker_field, "value": broker})

        raw_time = row.get("time", "")
        if not raw_time:
            null_time_count += 1
        else:
            try:
                time.fromisoformat(raw_time)
                times.append(raw_time)
            except ValueError:
                errors.append({"line": line_no, "reason": "invalid_execution_time", "value": raw_time})

        try:
            quantity = int(row.get("quantity", ""))
            rate = decimal_value(row.get("rate", ""))
            amount = decimal_value(row.get("amount", ""))
            if quantity <= 0 or rate <= 0 or amount <= 0:
                raise ValueError("non_positive_quantity_rate_or_amount")
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

    exact_duplicate_contracts = []
    conflicting_duplicate_contracts = []
    for contract, group in contract_groups.items():
        if not contract or len(group) < 2:
            continue
        trade_fields = [
            {k: v for k, v in row.items() if k != "id"}
            for row in group
        ]
        if all(item == trade_fields[0] for item in trade_fields[1:]):
            exact_duplicate_contracts.append({"contract_no": contract, "rows": len(group)})
        else:
            conflicting_duplicate_contracts.append({"contract_no": contract, "rows": len(group)})

    duplicate_ids = [{"id": key, "rows": count} for key, count in id_counts.items() if key and count > 1]
    row_validation_pass = (
        len(errors) == 0
        and len(exact_duplicate_contracts) == 0
        and len(conflicting_duplicate_contracts) == 0
        and len(duplicate_ids) == 0
        and len(rows) > 0
    )
    return {
        "expected_date": expected_date,
        "row_count": len(rows),
        "valid_numeric_rows": valid_numeric_rows,
        "row_validation_errors": errors,
        "row_validation_error_count": len(errors),
        "exact_duplicate_contracts": exact_duplicate_contracts,
        "conflicting_duplicate_contracts": conflicting_duplicate_contracts,
        "duplicate_ids": duplicate_ids,
        "unique_contract_numbers": len(contract_groups),
        "unique_ids": len(id_counts),
        "contract_date_prefix_mismatch_count": prefix_mismatch_count,
        "null_execution_time_count": null_time_count,
        "valid_execution_time_count": len(times),
        "execution_time_range": [min(times), max(times)] if times else None,
        "total_quantity": total_quantity,
        "total_amount": str(total_amount),
        "unique_symbols": len(symbol_counts),
        "symbol_row_counts": dict(sorted(symbol_counts.items())),
        "unique_broker_codes": len(broker_codes),
        "row_validation_pass": row_validation_pass,
    }


def find_nepse_index_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    matches = []
    for row in rows:
        for key in ("sector", "symbol", "index_name", "index"):
            value = (row.get(key) or "").strip().upper().replace("%20", " ")
            normalized = re.sub(r"[\s_-]+", "", value)
            if normalized in {"NEPSE", "NEPSEINDEX"}:
                matches.append(row)
                break
    return matches


def find_nepse_index_row(rows: list[dict[str, str]]) -> dict[str, str] | None:
    matches = find_nepse_index_rows(rows)
    return matches[0] if matches else None


def compare_index_controls(
    floorsheet: dict[str, Any],
    index_rows: list[dict[str, str]],
    expected_date: str | None = None,
) -> dict[str, Any]:
    matches = find_nepse_index_rows(index_rows)
    if not matches:
        return {"status": "nepse_index_control_row_missing", "matched": False}
    if len(matches) != 1:
        return {
            "status": "duplicate_nepse_index_control_rows",
            "matched": False,
            "nepse_index_row_count": len(matches),
            "nepse_index_rows": matches,
        }
    index_row = matches[0]
    date_field = next((key for key in ("date", "calculation_date", "trade_date") if index_row.get(key)), None)
    if expected_date and date_field and index_row[date_field] != expected_date:
        return {
            "status": "nepse_index_control_date_mismatch",
            "matched": False,
            "index_date": index_row[date_field],
            "expected_date": expected_date,
            "index_date_field": date_field,
            "index_row": index_row,
        }
    mappings = {
        "turnover_amount": ("total_amount", ("turnover_values", "turnover_value", "turnover")),
        "share_quantity": ("total_quantity", ("turnover_volume", "volume")),
        "transaction_count": ("row_count", ("total_transaction", "total_transactions", "transactions")),
    }
    comparisons = {}
    all_match = True
    for label, (floor_key, index_keys) in mappings.items():
        source_key = next((key for key in index_keys if index_row.get(key) not in (None, "")), None)
        if source_key is None:
            comparisons[label] = {"status": "index_field_missing", "candidate_fields": list(index_keys)}
            all_match = False
            continue
        try:
            floor_value = Decimal(str(floorsheet[floor_key]))
            index_value = Decimal(str(index_row[source_key]).replace(",", "").strip())
            difference = floor_value - index_value
            match = difference == 0
            comparisons[label] = {
                "floorsheet_value": str(floor_value),
                "index_value": str(index_value),
                "index_field": source_key,
                "difference_floorsheet_minus_index": str(difference),
                "absolute_difference": str(abs(difference)),
                "status": "exact_match" if match else "different",
            }
            all_match = all_match and match
        except (InvalidOperation, ValueError, KeyError) as exc:
            comparisons[label] = {"status": "invalid_control_value", "detail": str(exc)}
            all_match = False
    return {
        "status": "exact_control_total_match" if all_match else "control_total_difference_or_missing",
        "matched": all_match,
        "index_row": index_row,
        "comparisons": comparisons,
    }


def validate_index_ohlc(index_row: dict[str, str]) -> dict[str, Any]:
    errors = []
    values = {}
    for field in ("open", "high", "low", "close"):
        try:
            values[field] = decimal_value(index_row[field])
        except (KeyError, InvalidOperation, ValueError) as exc:
            errors.append({"reason": "missing_or_invalid_index_ohlc", "field": field, "detail": str(exc)})
    if len(values) == 4:
        if values["high"] < values["open"]:
            errors.append({"reason": "index_high_below_open", "high": str(values["high"]), "open": str(values["open"])})
        if values["high"] < values["close"]:
            errors.append({"reason": "index_high_below_close", "high": str(values["high"]), "close": str(values["close"])})
        if values["high"] < values["low"]:
            errors.append({"reason": "index_high_below_low", "high": str(values["high"]), "low": str(values["low"])})
        if values["low"] > values["open"]:
            errors.append({"reason": "index_low_above_open", "low": str(values["low"]), "open": str(values["open"])})
        if values["low"] > values["close"]:
            errors.append({"reason": "index_low_above_close", "low": str(values["low"]), "close": str(values["close"])})
    previous_close_diagnostic = None
    try:
        previous_close = decimal_value(index_row["close"]) - decimal_value(index_row["absolute_change"])
        previous_close_diagnostic = {
            "derived_previous_close": str(previous_close),
            "open_equals_derived_previous_close": decimal_value(index_row["open"]) == previous_close,
        }
    except (KeyError, InvalidOperation, ValueError):
        pass
    return {
        "valid": not errors,
        "errors": errors,
        "previous_close_diagnostic": previous_close_diagnostic,
    }


def compare_reference_turnover(
    floorsheet: dict[str, Any],
    reference_rows: list[dict[str, str]],
    expected_date: str,
) -> dict[str, Any]:
    matches = find_nepse_index_rows(reference_rows)
    if not matches:
        return {"status": "reference_nepse_index_row_missing", "matched": False}
    if len(matches) != 1:
        return {
            "status": "duplicate_reference_nepse_index_rows",
            "matched": False,
            "row_count": len(matches),
        }
    row = matches[0]
    date_field = next((key for key in ("date", "calculation_date", "trade_date") if row.get(key)), None)
    if date_field and row[date_field] != expected_date:
        return {
            "status": "reference_index_date_mismatch",
            "matched": False,
            "expected_date": expected_date,
            "actual_date": row[date_field],
        }
    if row.get("volume") in (None, ""):
        return {"status": "reference_turnover_field_missing", "matched": False, "reference_row": row}
    floor_value = Decimal(str(floorsheet["total_amount"]))
    reference_value = decimal_value(row["volume"])
    difference = floor_value - reference_value
    relative_percent = (abs(difference) / reference_value * Decimal(100)) if reference_value else None
    return {
        "status": "exact_match" if difference == 0 else "different",
        "matched": difference == 0,
        "mapping": "SocrateAI index CSV volume field is treated as turnoverValue, not share volume",
        "floorsheet_amount": str(floor_value),
        "reference_turnover": str(reference_value),
        "difference_floorsheet_minus_reference": str(difference),
        "absolute_difference": str(abs(difference)),
        "relative_difference_percent": str(relative_percent) if relative_percent is not None else None,
        "reference_row": row,
    }


def audit_sample(floorsheet_path: str | Path, index_path: str | Path, expected_date: str, reference_index_path: str | Path | None = None) -> dict[str, Any]:
    floor_rows, floor_fields = read_csv(floorsheet_path)
    missing = FLOORSHEET_REQUIRED - set(floor_fields)
    if missing:
        raise ValueError("floorsheet missing columns: " + ", ".join(sorted(missing)))
    index_rows, index_fields = read_csv(index_path)
    floor_audit = audit_floorsheet_rows(floor_rows, expected_date)
    controls = compare_index_controls(floor_audit, index_rows, expected_date)
    index_ohlc = validate_index_ohlc(controls["index_row"]) if controls.get("index_row") else {"valid": False, "errors": [{"reason": "index_control_row_unavailable"}], "previous_close_diagnostic": None}
    reference_control = None
    reference_file = None
    if reference_index_path is not None:
        reference_rows, reference_fields = read_csv(reference_index_path)
        reference_control = compare_reference_turnover(floor_audit, reference_rows, expected_date)
        reference_file = {"path": str(reference_index_path), "size_bytes": Path(reference_index_path).stat().st_size, "sha256": sha256_file(reference_index_path), "columns": reference_fields}
    return {
        "expected_date": expected_date,
        "floorsheet_file": {
            "path": str(floorsheet_path),
            "size_bytes": Path(floorsheet_path).stat().st_size,
            "sha256": sha256_file(floorsheet_path),
            "columns": floor_fields,
        },
        "index_file": {
            "path": str(index_path),
            "size_bytes": Path(index_path).stat().st_size,
            "sha256": sha256_file(index_path),
            "columns": index_fields,
        },
        "floorsheet": floor_audit,
        "index_control_totals": controls,
        "index_ohlc_validation": index_ohlc,
        "reference_index_file": reference_file,
        "reference_index_corroboration": reference_control,
        "floorsheet_row_gate": "PASS" if floor_audit["row_validation_pass"] else "FAIL",
        "same_dataset_index_gate": "PASS" if controls["matched"] and index_ohlc["valid"] else "FAIL",
        "canonical_promotion_allowed": False,
        "limitations": [
            "This is a one-date sample validation, not proof of archive completeness.",
            "A control-total difference is preserved as a discrepancy; no values are auto-corrected.",
            "Broker codes are retained as source identifiers; no beneficial ownership or broker intent is inferred.",
            "Null execution times, if any, remain null and are never imputed.",
            "Contract numbers and IDs remain strings.",
            "Session calendar and upstream data rights gates remain separate from row validation.",
        ],
        "sample_gate": "PASS" if floor_audit["row_validation_pass"] and controls["matched"] and index_ohlc["valid"] and (reference_control is None or reference_control["matched"]) else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--floorsheet", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--reference-index", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/reports/hf-floorsheet-sample-audit.json"))
    args = parser.parse_args()
    report = audit_sample(args.floorsheet, args.index, args.date, args.reference_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "date": report["expected_date"],
        "rows": report["floorsheet"]["row_count"],
        "row_validation_pass": report["floorsheet"]["row_validation_pass"],
        "control_total_status": report["index_control_totals"]["status"],
        "index_ohlc_errors": len(report["index_ohlc_validation"]["errors"]),
        "reference_turnover_status": (report.get("reference_index_corroboration") or {}).get("status"),
        "sample_gate": report["sample_gate"],
        "canonical_promotion_allowed": False,
    }, indent=2))
    if report["sample_gate"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
