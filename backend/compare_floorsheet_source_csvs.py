#!/usr/bin/env python3
"""Compare two dated NEPSE floorsheet CSV sources by canonical contract ID."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

HEADERS = {
    "samir": (
        "date", "sn", "contract_no", "stock_symbol", "buyer", "seller",
        "quantity", "rate", "amount",
    ),
    "socrate": (
        "transaction", "symbol", "buyer", "seller", "quantity", "rate",
        "amount", "date",
    ),
}
FIELDS = ("date", "symbol", "buyer", "seller", "quantity", "rate", "amount")


def parse_decimal(value: str, field: str) -> Decimal:
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{field} must be finite and positive")
    return number


def normalized(number: Decimal) -> str:
    return format(number.normalize(), "f")


def read_source(path: str | Path, source_format: str) -> dict[str, Any]:
    if source_format not in HEADERS:
        raise ValueError(f"unsupported source format: {source_format}")
    source_path = Path(path)
    payload = source_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("source payload must be valid UTF-8") from exc

    import io
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = tuple(reader.fieldnames or ())
    if headers != HEADERS[source_format]:
        raise ValueError(
            f"{source_format} header mismatch: expected {HEADERS[source_format]!r}, got {headers!r}"
        )

    rows: dict[str, dict[str, str]] = {}
    duplicate_contract_ids: list[str] = []
    malformed_rows = 0
    formula_mismatch_ids: list[str] = []
    date_counts: Counter[str] = Counter()
    quantity_total = Decimal("0")
    amount_total = Decimal("0")
    symbols: set[str] = set()

    for row in reader:
        if None in row or any(row.get(header) is None for header in headers):
            malformed_rows += 1
            continue
        raw = {key: (value or "").strip() for key, value in row.items()}
        if any(value == "" for value in raw.values()):
            malformed_rows += 1
            continue

        contract_id = raw["contract_no"] if source_format == "samir" else raw["transaction"]
        date = raw["date"]
        symbol = raw["stock_symbol"] if source_format == "samir" else raw["symbol"]
        if not contract_id or len(date) != 10 or date[4] != "-" or date[7] != "-":
            malformed_rows += 1
            continue

        try:
            quantity = parse_decimal(raw["quantity"], "quantity")
            rate = parse_decimal(raw["rate"], "rate")
            amount = parse_decimal(raw["amount"], "amount")
        except ValueError:
            malformed_rows += 1
            continue
        canonical = {
            "date": date,
            "symbol": symbol.upper(),
            "buyer": raw["buyer"],
            "seller": raw["seller"],
            "quantity": normalized(quantity),
            "rate": normalized(rate),
            "amount": normalized(amount),
        }
        if quantity != quantity.to_integral_value():
            malformed_rows += 1
            continue
        if quantity * rate != amount:
            formula_mismatch_ids.append(contract_id)
        if contract_id in rows:
            duplicate_contract_ids.append(contract_id)
        else:
            rows[contract_id] = canonical
        date_counts[date] += 1
        symbols.add(symbol.upper())
        quantity_total += quantity
        amount_total += amount

    return {
        "source_format": source_format,
        "source_path": source_path.name,
        "byte_size": len(payload),
        "sha256": digest,
        "headers": list(headers),
        "row_count": sum(date_counts.values()),
        "unique_contract_count": len(rows),
        "duplicate_contract_ids": sorted(set(duplicate_contract_ids)),
        "malformed_rows": malformed_rows,
        "formula_mismatch_contract_ids": sorted(set(formula_mismatch_ids)),
        "date_counts": dict(date_counts),
        "symbols": sorted(symbols),
        "quantity": quantity_total,
        "gross_amount": amount_total,
        "contracts": rows,
    }


def _source_summary(source: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (
            str(value) if isinstance(value, Decimal)
            else value
        )
        for key, value in source.items()
        if key != "contracts"
    }


def compare_sources(
    left_path: str | Path,
    right_path: str | Path,
    *,
    left_format: str,
    right_format: str,
    independent_control: dict[str, str] | None = None,
) -> dict[str, Any]:
    left = read_source(left_path, left_format)
    right = read_source(right_path, right_format)
    left_ids = set(left["contracts"])
    right_ids = set(right["contracts"])
    shared = sorted(left_ids & right_ids)
    left_only = sorted(left_ids - right_ids)
    right_only = sorted(right_ids - left_ids)

    exact_matches = []
    conflicts = []
    for contract_id in shared:
        lrow, rrow = left["contracts"][contract_id], right["contracts"][contract_id]
        differences = [field for field in FIELDS if lrow[field] != rrow[field]]
        if differences:
            conflicts.append({
                "contract_id": contract_id,
                "different_fields": differences,
                "left": lrow,
                "right": rrow,
            })
        else:
            exact_matches.append(contract_id)

    control_report = None
    if independent_control is not None:
        expected_quantity = Decimal(str(independent_control["quantity"]))
        expected_amount = Decimal(str(independent_control["gross_amount"]))
        control_report = {}
        for label, source in (("left", left), ("right", right)):
            qdiff = source["quantity"] - expected_quantity
            adiff = source["gross_amount"] - expected_amount
            control_report[label] = {
                "expected_quantity": str(expected_quantity),
                "observed_quantity": str(source["quantity"]),
                "quantity_difference": str(qdiff),
                "expected_gross_amount": str(expected_amount),
                "observed_gross_amount": str(source["gross_amount"]),
                "gross_amount_difference": str(adiff),
                "status": "passed" if qdiff == 0 and adiff == 0 else "failed",
            }

    if left_only or right_only or conflicts:
        comparison_status = "mismatch"
    else:
        comparison_status = "exact_contract_set_and_row_match"

    return {
        "schema_version": "1.0",
        "left_source": _source_summary(left),
        "right_source": _source_summary(right),
        "comparison": {
            "left_only_contract_count": len(left_only),
            "right_only_contract_count": len(right_only),
            "shared_contract_count": len(shared),
            "exact_row_match_count": len(exact_matches),
            "conflicting_shared_contract_count": len(conflicts),
            "exact_match_rate_on_shared": (
                str(Decimal(len(exact_matches)) / Decimal(len(shared)))
                if shared else None
            ),
            "left_only_contracts": [
                {"contract_id": cid, **left["contracts"][cid]} for cid in left_only
            ],
            "right_only_contracts": [
                {"contract_id": cid, **right["contracts"][cid]} for cid in right_only
            ],
            "conflicts": conflicts,
            "status": comparison_status,
        },
        "independent_control": control_report,
        "acceptance": {
            "canonical_source_selected": False,
            "training_eligible": False,
            "policy": "contract_level_comparison_only_no_source_auto_selection",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True, type=Path)
    parser.add_argument("--right", required=True, type=Path)
    parser.add_argument("--left-format", choices=sorted(HEADERS), required=True)
    parser.add_argument("--right-format", choices=sorted(HEADERS), required=True)
    parser.add_argument("--control-date")
    parser.add_argument("--control-quantity")
    parser.add_argument("--control-gross-amount")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    control_values = (
        args.control_date, args.control_quantity, args.control_gross_amount
    )
    if any(control_values) and not all(control_values):
        parser.error("--control-date, --control-quantity and --control-gross-amount must be supplied together")
    control = None
    if all(control_values):
        control = {
            "trade_date": args.control_date,
            "quantity": args.control_quantity,
            "gross_amount": args.control_gross_amount,
        }

    report = compare_sources(
        args.left, args.right,
        left_format=args.left_format,
        right_format=args.right_format,
        independent_control=control,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "left_only": report["comparison"]["left_only_contract_count"],
        "right_only": report["comparison"]["right_only_contract_count"],
        "shared": report["comparison"]["shared_contract_count"],
        "exact": report["comparison"]["exact_row_match_count"],
        "conflicts": report["comparison"]["conflicting_shared_contract_count"],
        "status": report["comparison"]["status"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
