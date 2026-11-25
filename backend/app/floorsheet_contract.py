"""Normalized floorsheet contract schema and conservative duplicate classification.

Rows are never silently discarded. Every input row receives a disposition and
retains source/payload/line evidence for audit and later adjudication.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
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
        required = (self.source_id, self.source_payload_sha256, self.trade_date,
                    self.contract_id, self.symbol, self.buyer_broker_code,
                    self.seller_broker_code)
        if not all(str(value).strip() for value in required):
            raise ValueError("required floorsheet identifiers/evidence cannot be blank")
        if len(self.source_payload_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_payload_sha256.lower()):
            raise ValueError("source_payload_sha256 must be a 64-character hex digest")
        if self.source_row_number < 1:
            raise ValueError("source_row_number must be positive")
        if any(not value.is_finite() for value in (self.quantity, self.rate, self.amount)):
            raise ValueError("quantity, rate and amount must be finite decimals")
        if min(self.quantity, self.rate, self.amount) <= 0:
            raise ValueError("quantity, rate and amount must be positive")

    @classmethod
    def from_mapping(cls, row: dict, *, source_id: str, payload_sha256: str, row_number: int):
        text_fields = ("trade_date", "contract_id", "symbol", "buyer_broker_code", "seller_broker_code")
        if any(row.get(field) is None or not str(row[field]).strip() for field in text_fields):
            raise ValueError("trade date, contract, symbol and broker codes must be present")
        try:
            from datetime import date
            date.fromisoformat(str(row["trade_date"]))
        except (TypeError, ValueError) as exc:
            raise ValueError("trade_date must be a valid ISO date") from exc
        try:
            quantity = Decimal(str(row["quantity"]))
            rate = Decimal(str(row["rate"]))
            amount = Decimal(str(row["amount"]))
        except (KeyError, InvalidOperation) as exc:
            raise ValueError("quantity, rate and amount must be valid decimals") from exc
        return cls(source_id, payload_sha256, row_number, str(row["trade_date"]),
                   str(row["contract_id"]), str(row["symbol"]),
                   str(row["buyer_broker_code"]), str(row["seller_broker_code"]),
                   quantity, rate, amount)


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
