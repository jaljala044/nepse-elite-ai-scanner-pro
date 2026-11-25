#!/usr/bin/env python3
"""Derive auditable buyer/seller execution-channel observations from a pinned CSV."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.broker_aggregation import aggregate_broker_observations

EXPECTED_HEADERS = [
    "date", "transaction_no", "symbol", "buyer", "seller",
    "quantity", "rate", "amount",
]
PARTY_HEADERS = [
    "trade_date", "symbol", "side", "amount", "quantity",
    "identity_status", "broker_entity_id", "source_broker_code",
    "source_id", "contract_id", "source_payload_sha256",
    "source_row_number", "identity_evidence_ids",
]


def derive(input_path: Path, *, source_id: str, expected_sha256: str,
           expected_date: str, expected_rows: int) -> tuple[list[dict], dict]:
    payload = input_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256.lower():
        raise ValueError(f"source SHA-256 mismatch: expected {expected_sha256}, got {digest}")

    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames != EXPECTED_HEADERS:
        raise ValueError(f"unexpected source headers: {reader.fieldnames!r}")

    party_rows: list[dict] = []
    contract_ids: set[str] = set()
    broker_codes: set[str] = set()
    symbols: set[str] = set()
    total_quantity = Decimal("0")
    total_amount = Decimal("0")
    amount_exceptions: list[dict] = []
    contract_count = 0

    for line_number, row in enumerate(reader, start=2):
        contract_count += 1
        if row["date"] != expected_date:
            raise ValueError(f"line {line_number}: date differs from expected date")
        contract_id = row["transaction_no"]
        symbol = row["symbol"]
        buyer, seller = row["buyer"], row["seller"]
        if not contract_id or contract_id in contract_ids:
            raise ValueError(f"line {line_number}: blank or duplicate transaction_no")
        if not symbol or symbol != symbol.strip().upper():
            raise ValueError(f"line {line_number}: invalid symbol")
        if not buyer.isdigit() or not seller.isdigit():
            raise ValueError(f"line {line_number}: broker codes must remain numeric strings")
        try:
            quantity = Decimal(row["quantity"])
            rate = Decimal(row["rate"])
            amount = Decimal(row["amount"])
        except (InvalidOperation, TypeError) as exc:
            raise ValueError(f"line {line_number}: invalid Decimal field") from exc
        if any(not value.is_finite() for value in (quantity, rate, amount)):
            raise ValueError(f"line {line_number}: non-finite numeric field")
        if min(quantity, rate, amount) <= 0:
            raise ValueError(f"line {line_number}: non-positive numeric field")
        if quantity * rate != amount:
            amount_exceptions.append({
                "source_row_number": line_number,
                "contract_id": contract_id,
                "quantity": str(quantity), "rate": str(rate),
                "amount": str(amount), "calculated_amount": str(quantity * rate),
            })
        contract_ids.add(contract_id)
        broker_codes.update((buyer, seller))
        symbols.add(symbol)
        total_quantity += quantity
        total_amount += amount

        for side, broker_code in (("buy", buyer), ("sell", seller)):
            party_rows.append({
                "trade_date": expected_date,
                "symbol": symbol,
                "side": side,
                "amount": str(amount),
                "quantity": str(quantity),
                "identity_status": "unmapped",
                "broker_entity_id": None,
                "source_broker_code": broker_code,
                "source_id": source_id,
                "contract_id": contract_id,
                "source_payload_sha256": digest,
                "source_row_number": line_number,
                "identity_evidence_ids": [],
            })

    if contract_count != expected_rows:
        raise ValueError(f"source row count mismatch: expected {expected_rows}, got {contract_count}")
    if len(party_rows) != contract_count * 2:
        raise AssertionError("each contract must produce exactly one buyer and one seller observation")

    aggregated = aggregate_broker_observations(party_rows)
    report = {
        "schema_version": 1,
        "source_id": source_id,
        "source_file": str(input_path),
        "source_sha256": digest,
        "source_byte_count": len(payload),
        "trade_date": expected_date,
        "contract_count": contract_count,
        "party_observation_count": len(party_rows),
        "distinct_broker_codes": len(broker_codes),
        "distinct_symbols": len(symbols),
        "total_quantity_once_per_contract": str(total_quantity),
        "gross_amount_once_per_contract": str(total_amount),
        "quantity_rate_amount_exception_count": len(amount_exceptions),
        "quantity_rate_amount_exceptions": amount_exceptions,
        "aggregation": aggregated,
        "identity_policy": "all source broker codes remain execution-channel identifiers; no beneficial-owner or canonical legal-entity inference",
        "identity_status": "unmapped",
        "canonical_promotion_allowed": False,
    }
    return party_rows, report


def write_outputs(party_rows: list[dict], report: dict,
                  party_output: Path, aggregate_output: Path) -> None:
    party_output.parent.mkdir(parents=True, exist_ok=True)
    aggregate_output.parent.mkdir(parents=True, exist_ok=True)
    with party_output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PARTY_HEADERS)
        writer.writeheader()
        for row in party_rows:
            encoded = dict(row)
            encoded["identity_evidence_ids"] = ";".join(encoded["identity_evidence_ids"])
            writer.writerow(encoded)
    aggregate_output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--expected-rows", required=True, type=int)
    parser.add_argument("--party-output", required=True, type=Path)
    parser.add_argument("--aggregate-output", required=True, type=Path)
    args = parser.parse_args()
    parties, report = derive(
        args.input, source_id=args.source_id,
        expected_sha256=args.expected_sha256,
        expected_date=args.date, expected_rows=args.expected_rows,
    )
    write_outputs(parties, report, args.party_output, args.aggregate_output)
    print(json.dumps({
        "source_sha256": report["source_sha256"],
        "contract_count": report["contract_count"],
        "party_observation_count": report["party_observation_count"],
        "distinct_broker_codes": report["distinct_broker_codes"],
        "distinct_symbols": report["distinct_symbols"],
        "aggregate_rows": report["aggregation"]["aggregate_rows"],
        "canonical_promotion_allowed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
