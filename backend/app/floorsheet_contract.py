"""Normalized floorsheet contract schema and conservative duplicate classification.

Rows are never silently discarded. Every input row receives a disposition and
retains source/payload/line evidence for audit and later adjudication.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Iterable


@dataclass(frozen=True)
class FloorsheetContract:
    source_id: str
    source_payload_sha256: str
    source_row_number: int
    trade_date: str
    contract_id: str
    symbol: str
    buyer_broker_code: str
    seller_broker_code: str
    quantity: Decimal
    rate: Decimal
    amount: Decimal

    def __post_init__(self):
        text_fields = (
            ("source_id", self.source_id), ("source_payload_sha256", self.source_payload_sha256),
            ("trade_date", self.trade_date), ("contract_id", self.contract_id),
            ("symbol", self.symbol), ("buyer_broker_code", self.buyer_broker_code),
            ("seller_broker_code", self.seller_broker_code),
        )
        if any(not isinstance(value, str) or not value.strip() for _, value in text_fields):
            raise ValueError("required floorsheet identifiers/evidence must be nonblank strings")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.source_payload_sha256):
            raise ValueError("source_payload_sha256 must be a 64-character hex digest")
        if isinstance(self.source_row_number, bool) or not isinstance(self.source_row_number, int) or self.source_row_number < 1:
            raise ValueError("source_row_number must be a positive integer")
        if not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", self.trade_date):
            raise ValueError("trade_date must use YYYY-MM-DD")
        try:
            date.fromisoformat(self.trade_date)
        except ValueError as exc:
            raise ValueError("trade_date must be a valid ISO date") from exc
        if self.symbol != self.symbol.strip().upper():
            raise ValueError("symbol must be uppercase and trimmed")
        if any(not isinstance(value, Decimal) for value in (self.quantity, self.rate, self.amount)):
            raise ValueError("quantity, rate and amount must be Decimal values")
        if any(not value.is_finite() for value in (self.quantity, self.rate, self.amount)):
            raise ValueError("quantity, rate and amount must be finite decimals")
        if min(self.quantity, self.rate, self.amount) <= 0:
            raise ValueError("quantity, rate and amount must be positive")

    @classmethod
    def from_mapping(cls, row: dict, *, source_id: str, payload_sha256: str, row_number: int):
        if not isinstance(row, dict):
            raise ValueError("source row must be an object")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id must be a nonblank string")
        if not isinstance(payload_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", payload_sha256):
            raise ValueError("payload_sha256 must be a 64-character hex digest")
        if isinstance(row_number, bool) or not isinstance(row_number, int) or row_number < 1:
            raise ValueError("row_number must be a positive integer")
        text_fields = ("trade_date", "contract_id", "symbol", "buyer_broker_code", "seller_broker_code")
        if any(not isinstance(row.get(field), str) or not row[field].strip() for field in text_fields):
            raise ValueError("trade date, contract, symbol and broker codes must be nonblank strings")
        try:
            quantity = Decimal(str(row["quantity"]))
            rate = Decimal(str(row["rate"]))
            amount = Decimal(str(row["amount"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("quantity, rate and amount must be valid decimals") from exc
        return cls(source_id, payload_sha256.lower(), row_number, row["trade_date"],
                   row["contract_id"], row["symbol"], row["buyer_broker_code"],
                   row["seller_broker_code"], quantity, rate, amount)


def reconcile_floorsheet_rows(rows: Iterable[FloorsheetContract],
                              amount_tolerance: Decimal = Decimal("0.01")) -> dict:
    """Classify exact repeats and conflicting contract IDs without dropping rows."""
    if not amount_tolerance.is_finite() or amount_tolerance < 0:
        raise ValueError("amount_tolerance must be finite and non-negative")
    materialized = list(rows)
    by_contract = {}
    for row in materialized:
        by_contract.setdefault((row.trade_date, row.contract_id), []).append(row)
    output = []
    counts = {"unique": 0, "exact_duplicate": 0, "conflicting_duplicate": 0,
              "amount_reconciliation_exception": 0}
    for row in materialized:
        peers = by_contract[(row.trade_date, row.contract_id)]
        signatures = {(x.symbol, x.buyer_broker_code, x.seller_broker_code,
                       x.quantity, x.rate, x.amount) for x in peers}
        if len(signatures) > 1:
            disposition = "conflicting_duplicate"
        elif len(peers) > 1:
            disposition = "exact_duplicate"
        else:
            disposition = "unique"
        calculated = row.quantity * row.rate
        amount_exception = abs(calculated - row.amount) > amount_tolerance
        if amount_exception:
            counts["amount_reconciliation_exception"] += 1
        counts[disposition] += 1
        output.append({
            **asdict(row),
            "quantity": str(row.quantity), "rate": str(row.rate), "amount": str(row.amount),
            "calculated_gross_amount": str(calculated),
            "amount_reconciliation_exception": amount_exception,
            "duplicate_disposition": disposition,
            "duplicate_group_size": len(peers),
            "retained_for_review": disposition != "unique" or amount_exception,
        })
    return {"input_rows": len(materialized), "output_rows": len(output),
            "counts": counts, "rows": output,
            "rows_discarded": 0, "policy": "classify_and_retain_all_rows"}
