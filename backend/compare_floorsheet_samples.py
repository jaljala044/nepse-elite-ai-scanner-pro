#!/usr/bin/env python3
"""Compare one date's Urekmazino and SocrateAI floorsheet transactions without merging them."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

FIELD_MAP = {
    "stock_symbol": "symbol",
    "buyer": "buyer",
    "seller": "seller",
    "quantity": "quantity",
    "rate": "rate",
    "amount": "amount",
    "calculation_date": "date",
}
DECIMAL_FIELDS = {"quantity", "rate", "amount"}


def read_rows(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    opener = gzip.open if source.suffix.lower() == ".gz" else open
    with opener(source, "rt", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decimal_value(value: Any) -> Decimal:
    result = Decimal(str(value).replace(",", "").strip())
    if not result.is_finite():
        raise ValueError("non_finite_decimal")
    return result


def _index(rows: list[dict[str, str]], key: str) -> tuple[dict[str, dict[str, str]], list[str]]:
    counts = Counter((row.get(key) or "").strip() for row in rows)
    duplicates = sorted(value for value, count in counts.items() if value and count > 1)
    indexed = {}
    for row in rows:
        value = (row.get(key) or "").strip()
        if value and value not in indexed:
            indexed[value] = row
    return indexed, duplicates


def _totals(rows: list[dict[str, str]], symbol_field: str, quantity_field: str, amount_field: str) -> dict[str, Any]:
    quantity = 0
    amount = Decimal(0)
    symbols = Counter()
    errors = []
    for line_no, row in enumerate(rows, 2):
        symbol = (row.get(symbol_field) or "").strip().upper()
        if symbol:
            symbols[symbol] += 1
        try:
            quantity += int(decimal_value(row[quantity_field]))
            amount += decimal_value(row[amount_field])
        except (KeyError, ValueError, InvalidOperation) as exc:
            errors.append({"line": line_no, "reason": "invalid_total_field", "detail": str(exc)})
    return {
        "row_count": len(rows),
        "unique_symbols": len(symbols),
        "symbol_row_counts": dict(sorted(symbols.items())),
        "total_quantity": quantity,
        "total_amount": str(amount),
        "total_errors": errors,
    }


def compare_samples(
    urek_rows: list[dict[str, str]],
    socrateai_rows: list[dict[str, str]],
    expected_date: str,
) -> dict[str, Any]:
    required_urek = {"contract_no", "calculation_date", "stock_symbol", "buyer", "seller", "quantity", "rate", "amount"}
    required_soc = {"transaction", "date", "symbol", "buyer", "seller", "quantity", "rate", "amount"}
    missing_urek = sorted(required_urek - set(urek_rows[0] if urek_rows else {}))
    missing_soc = sorted(required_soc - set(socrateai_rows[0] if socrateai_rows else {}))
    if missing_urek or missing_soc:
        raise ValueError(f"missing schema fields: Urek={missing_urek}, SocrateAI={missing_soc}")

    urek, urek_duplicates = _index(urek_rows, "contract_no")
    soc, soc_duplicates = _index(socrateai_rows, "transaction")
    urek_keys = set(urek)
    soc_keys = set(soc)
    shared = sorted(urek_keys & soc_keys)
    urek_only = sorted(urek_keys - soc_keys)
    soc_only = sorted(soc_keys - urek_keys)
    mismatches = []
    date_errors = []

    for contract in shared:
        left = urek[contract]
        right = soc[contract]
        field_differences = []
        for urek_field, soc_field in FIELD_MAP.items():
            lv = (left.get(urek_field) or "").strip()
            rv = (right.get(soc_field) or "").strip()
            if urek_field in DECIMAL_FIELDS:
                try:
                    equal = decimal_value(lv) == decimal_value(rv)
                except (ValueError, InvalidOperation):
                    equal = False
            else:
                equal = lv == rv
            if not equal:
                field_differences.append({
                    "field": urek_field,
                    "urek_value": lv,
                    "socrateai_value": rv,
                })
        if left.get("calculation_date") != expected_date:
            date_errors.append({"contract_no": contract, "source": "urek", "date": left.get("calculation_date")})
        if right.get("date") != expected_date:
            date_errors.append({"contract_no": contract, "source": "socrateai", "date": right.get("date")})
        if field_differences:
            mismatches.append({"contract_no": contract, "field_differences": field_differences})

    urek_totals = _totals(urek_rows, "stock_symbol", "quantity", "amount")
    soc_totals = _totals(socrateai_rows, "symbol", "quantity", "amount")
    exact = (
        not urek_duplicates
        and not soc_duplicates
        and not urek_only
        and not soc_only
        and not mismatches
        and not date_errors
        and not urek_totals["total_errors"]
        and not soc_totals["total_errors"]
        and len(urek_rows) == len(socrateai_rows)
        and len(shared) == len(urek_rows)
    )
    return {
        "expected_date": expected_date,
        "urek": urek_totals,
        "socrateai": soc_totals,
        "contract_number_comparison": {
            "urek_unique_contracts": len(urek),
            "socrateai_unique_contracts": len(soc),
            "shared_contracts": len(shared),
            "urek_only_contracts": len(urek_only),
            "socrateai_only_contracts": len(soc_only),
            "urek_duplicate_contract_numbers": urek_duplicates,
            "socrateai_duplicate_contract_numbers": soc_duplicates,
        },
        "shared_field_mismatch_count": len(mismatches),
        "shared_field_mismatches_preview": mismatches[:100],
        "date_error_count": len(date_errors),
        "date_errors_preview": date_errors[:100],
        "shared_fields_compared": list(FIELD_MAP),
        "urek_only_fields_not_cross_checked": ["time", "sector", "id"],
        "socrateai_only_fields_not_cross_checked": [],
        "cross_source_status": "EXACT_MATCH_ON_SHARED_TRANSACTION_FIELDS" if exact else "CROSS_SOURCE_MISMATCH",
        "cross_source_match_pass": exact,
        "provenance_independence": "not_established; both publishers may share an upstream source",
        "canonical_promotion_allowed": False,
        "limitations": [
            "This is a one-date cross-source comparison, not proof of full archive completeness.",
            "No source is selected as canonical by this comparison.",
            "Urek-only time, sector and id fields cannot be independently verified against SocrateAI's schema.",
            "All raw files and source manifests remain separately preserved; no merged transaction table is written.",
        ],
    }


def audit_files(urek_path: str | Path, socrateai_path: str | Path, expected_date: str) -> dict[str, Any]:
    urek_rows = read_rows(urek_path)
    soc_rows = read_rows(socrateai_path)
    report = compare_samples(urek_rows, soc_rows, expected_date)
    report["urek_file"] = {
        "path": str(urek_path),
        "size_bytes": Path(urek_path).stat().st_size,
        "sha256": sha256_file(urek_path),
    }
    report["socrateai_file"] = {
        "path": str(socrateai_path),
        "size_bytes": Path(socrateai_path).stat().st_size,
        "sha256": sha256_file(socrateai_path),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urek", type=Path, required=True)
    parser.add_argument("--socrateai", type=Path, required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/reports/floorsheet-cross-source-sample.json"))
    args = parser.parse_args()
    report = audit_files(args.urek, args.socrateai, args.date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "date": report["expected_date"],
        "urek_rows": report["urek"]["row_count"],
        "socrateai_rows": report["socrateai"]["row_count"],
        "shared_contracts": report["contract_number_comparison"]["shared_contracts"],
        "shared_field_mismatch_count": report["shared_field_mismatch_count"],
        "cross_source_status": report["cross_source_status"],
        "canonical_promotion_allowed": False,
    }, indent=2))
    if not report["cross_source_match_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
