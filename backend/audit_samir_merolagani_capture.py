#!/usr/bin/env python3
"""Audit one pinned SamirWagle/MeroLagani-derived floorsheet CSV capture."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SOURCE_REPOSITORY = "SamirWagle/Nepse-All-Scraper"
SOURCE_COMMIT = "e6160adc6bdf3d19562167388e3d9d4f645c455a"
SOURCE_PATH = "data/floorsheet/floorsheet_2026-11-24.csv"
SOURCE_BLOB_SHA1 = "22eaa891b30aac2fe4cf197053efa014953351c0"
SOURCE_SIZE_BYTES = 3538179
SOURCE_SHA256 = "2687b7ed6bc5ebd737fa459ca8dd620941bb3ec1da6613fbd620550495018f55"
CAPTURE_DATE = "2026-11-24"

MEROLAGANI_CONTROLS = {
    "trade_date": CAPTURE_DATE,
    "quantity": "14670177",
    "gross_amount": "5553019249.46",
    "average_rate": "378.52",
}

EXPECTED_HEADERS = (
    "date", "sn", "contract_no", "stock_symbol", "buyer", "seller",
    "quantity", "rate", "amount",
)


def git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def decimal_value(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"non-finite {field}: {value!r}")
    return result


def audit_capture(
    path: str | Path,
    *,
    require_pinned_identity: bool = True,
    control_totals: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Recompute file integrity, schema, row controls and source-summary variances."""
    source_path = Path(path)
    payload = source_path.read_bytes()
    file_sha256 = hashlib.sha256(payload).hexdigest()
    blob_sha1 = git_blob_sha1(payload)

    if require_pinned_identity:
        if len(payload) != SOURCE_SIZE_BYTES:
            raise ValueError(
                f"source byte size mismatch: expected {SOURCE_SIZE_BYTES}, got {len(payload)}"
            )
        if file_sha256 != SOURCE_SHA256:
            raise ValueError("source SHA-256 does not match pinned sample")
        if blob_sha1 != SOURCE_BLOB_SHA1:
            raise ValueError("source Git blob SHA-1 does not match pinned sample")

    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("source is not valid UTF-8") from exc

    import io
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = tuple(reader.fieldnames or ())
    if headers != EXPECTED_HEADERS:
        raise ValueError(
            f"source header mismatch: expected {EXPECTED_HEADERS!r}, got {headers!r}"
        )

    row_count = 0
    malformed_rows = 0
    blank_cells = 0
    duplicate_contract_rows = 0
    formula_mismatch_rows = 0
    capture_date_counts: Counter[str] = Counter()
    contract_prefix_mismatch_rows = 0
    contract_ids: set[str] = set()
    symbols: set[str] = set()
    buyer_codes: set[str] = set()
    seller_codes: set[str] = set()
    serial_numbers: set[int] = set()
    quantity_total = Decimal("0")
    amount_total = Decimal("0")
    rate_total_diagnostic = Decimal("0")
    first_contract = None
    last_contract = None

    for line_number, row in enumerate(reader, start=2):
        row_count += 1
        if None in row or any(row.get(header) is None for header in EXPECTED_HEADERS):
            malformed_rows += 1
            continue
        values = {key: (value or "").strip() for key, value in row.items()}
        if any(value == "" for value in values.values()):
            blank_cells += sum(value == "" for value in values.values())
        if any(not values[key] for key in EXPECTED_HEADERS):
            malformed_rows += 1
            continue

        trade_date = values["date"]
        capture_date_counts[trade_date] += 1
        contract_id = values["contract_no"]
        if contract_id in contract_ids:
            duplicate_contract_rows += 1
        contract_ids.add(contract_id)
        if len(contract_id) < 8 or contract_id[:8] != CAPTURE_DATE.replace("-", ""):
            contract_prefix_mismatch_rows += 1

        symbol = values["stock_symbol"].upper()
        symbols.add(symbol)
        buyer_codes.add(values["buyer"])
        seller_codes.add(values["seller"])

        try:
            serial = int(values["sn"])
            quantity = decimal_value(values["quantity"], "quantity")
            rate = decimal_value(values["rate"], "rate")
            amount = decimal_value(values["amount"], "amount")
        except (ValueError, InvalidOperation):
            malformed_rows += 1
            continue
        if serial <= 0 or quantity <= 0 or rate <= 0 or amount <= 0:
            malformed_rows += 1
            continue
        if quantity != quantity.to_integral_value():
            malformed_rows += 1
            continue
        if serial in serial_numbers:
            # Repeated serials are not an executed-contract duplicate, but an
            # input-order/record-identity anomaly that must remain visible.
            pass
        serial_numbers.add(serial)

        if quantity * rate != amount:
            formula_mismatch_rows += 1
        quantity_total += quantity
        amount_total += amount
        rate_total_diagnostic += rate
        if first_contract is None or contract_id < first_contract:
            first_contract = contract_id
        if last_contract is None or contract_id > last_contract:
            last_contract = contract_id

    serial_min = min(serial_numbers) if serial_numbers else None
    serial_max = max(serial_numbers) if serial_numbers else None
    serial_gaps = (
        [value for value in range(serial_min, serial_max + 1) if value not in serial_numbers]
        if serial_min is not None else []
    )
    weighted_average_rate = (
        amount_total / quantity_total if quantity_total else None
    )

    controls = MEROLAGANI_CONTROLS if control_totals is None else control_totals
    expected_quantity = decimal_value(controls["quantity"], "control quantity")
    expected_amount = decimal_value(controls["gross_amount"], "control gross amount")
    expected_average = decimal_value(controls["average_rate"], "control average rate")
    quantity_diff = quantity_total - expected_quantity
    amount_diff = amount_total - expected_amount
    average_diff = weighted_average_rate - expected_average if weighted_average_rate is not None else None

    exact_controls_match = (
        quantity_diff == 0 and amount_diff == 0
    )
    dates_valid = (
        set(capture_date_counts) == {CAPTURE_DATE}
        and row_count == sum(capture_date_counts.values())
    )

    return {
        "schema_version": "1.0",
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "path": SOURCE_PATH,
            "git_blob_sha1": blob_sha1,
            "expected_git_blob_sha1": SOURCE_BLOB_SHA1,
            "byte_size": len(payload),
            "expected_byte_size": SOURCE_SIZE_BYTES,
            "sha256": file_sha256,
            "expected_sha256": SOURCE_SHA256,
            "pinned_identity_verified": (
                len(payload) == SOURCE_SIZE_BYTES
                and file_sha256 == SOURCE_SHA256
                and blob_sha1 == SOURCE_BLOB_SHA1
            ),
            "observed_header": list(headers),
            "capture_date_semantics": (
                "scraper_generated_date_today; not independently supplied by NEPSE"
            ),
        },
        "row_quality": {
            "data_rows": row_count,
            "malformed_rows": malformed_rows,
            "blank_cells": blank_cells,
            "unique_contract_ids": len(contract_ids),
            "duplicate_contract_id_rows": duplicate_contract_rows,
            "unique_symbols": len(symbols),
            "symbols": sorted(symbols),
            "unique_buyer_broker_codes": len(buyer_codes),
            "unique_seller_broker_codes": len(seller_codes),
            "unique_broker_code_union": len(buyer_codes | seller_codes),
            "capture_date_counts": dict(capture_date_counts),
            "all_rows_on_expected_date": dates_valid,
            "contract_prefix_mismatch_rows": contract_prefix_mismatch_rows,
            "quantity_rate_amount_mismatch_rows": formula_mismatch_rows,
            "total_quantity": str(quantity_total),
            "total_gross_amount": str(amount_total),
            "weighted_average_rate": str(weighted_average_rate) if weighted_average_rate is not None else None,
            "first_contract_id": first_contract,
            "last_contract_id": last_contract,
        },
        "serial_sequence": {
            "unique_serial_count": len(serial_numbers),
            "minimum": serial_min,
            "maximum": serial_max,
            "gap_count": len(serial_gaps),
            "missing_serial_numbers": serial_gaps,
        },
        "independent_daily_control": {
            "source": "MeroLagani indexed datewise floorsheet summary",
            "trade_date": controls["trade_date"],
            "expected_quantity": str(expected_quantity),
            "observed_quantity": str(quantity_total),
            "quantity_difference": str(quantity_diff),
            "expected_gross_amount": str(expected_amount),
            "observed_gross_amount": str(amount_total),
            "gross_amount_difference": str(amount_diff),
            "expected_average_rate": str(expected_average),
            "observed_weighted_average_rate": str(weighted_average_rate) if weighted_average_rate is not None else None,
            "weighted_average_rate_difference": str(average_diff) if average_diff is not None else None,
            "exact_quantity_and_amount_match": exact_controls_match,
            "status": "passed" if exact_controls_match else "failed",
        },
        "acceptance": {
            "sample_integrity": (
                "passed" if malformed_rows == 0 and blank_cells == 0 else "failed"
            ),
            "sample_completeness": "not_established",
            "control_total_reconciliation": "passed" if exact_controls_match else "failed",
            "serial_sequence": "gap_detected" if serial_gaps else "continuous",
            "canonical_promotion_allowed": False,
            "training_eligible": False,
            "overall_status": "review_required",
            "reasons": [
                "capture date is generated by the scraper and is not an exchange-origin timestamp",
                "publisher README labels the data license Educational; reuse rights are unresolved",
                "MeroLagani daily control totals do not match the retrieved CSV",
                "serial-number gaps require investigation against original pagination/source rows",
                "observed symbol set is not yet reconciled to the official 281-equity + 47-fund registry",
            ],
        },
        "policy": "immutable_source_audit_no_auto_repair_no_canonical_promotion",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit_capture(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "source_sha256": report["source"]["sha256"],
        "data_rows": report["row_quality"]["data_rows"],
        "quantity": report["row_quality"]["total_quantity"],
        "gross_amount": report["row_quality"]["total_gross_amount"],
        "control_status": report["independent_daily_control"]["status"],
        "serial_gap_count": report["serial_sequence"]["gap_count"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
