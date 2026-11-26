"""Cross-source floorsheet comparison without inferring source independence.

The report compares transaction observations only. It never labels either
publisher canonical, complete, or independent and never admits coverage cells.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from app.floorsheet_contract import FloorsheetContract


COMPARE_FIELDS = (
    "trade_date", "symbol", "buyer_broker_code", "seller_broker_code",
    "quantity", "rate", "amount",
)


def compare_floorsheet_sources(
    left_rows: Iterable[FloorsheetContract],
    right_rows: Iterable[FloorsheetContract],
) -> dict:
    """Compare unique transaction IDs across two separately parsed sources."""
    left = list(left_rows)
    right = list(right_rows)
    if not left or not right:
        raise ValueError("both sources must contain at least one parsed contract")

    def index(rows, label):
        result = {}
        for row in rows:
            if not isinstance(row, FloorsheetContract):
                raise ValueError(f"{label} rows must be FloorsheetContract objects")
            key = (row.trade_date, row.contract_id)
            if key in result:
                raise ValueError(f"{label} contains duplicate date/contract key: {key}")
            result[key] = row
        return result

    left_index = index(left, "left")
    right_index = index(right, "right")
    left_keys, right_keys = set(left_index), set(right_index)
    shared = sorted(left_keys & right_keys)
    conflicts = []
    exact = []
    for key in shared:
        a, b = left_index[key], right_index[key]
        differing = [field for field in COMPARE_FIELDS
                     if getattr(a, field) != getattr(b, field)]
        if differing:
            conflicts.append({
                "trade_date": key[0], "contract_id": key[1],
                "differing_fields": differing,
            })
        else:
            exact.append({"trade_date": key[0], "contract_id": key[1]})

    def totals(rows):
        return {
            "contract_count": len(rows),
            "unique_contract_count": len({(r.trade_date, r.contract_id) for r in rows}),
            "quantity": str(sum((r.quantity for r in rows), Decimal("0"))),
            "gross_amount": str(sum((r.amount for r in rows), Decimal("0"))),
        }

    return {
        "comparison_status": "compared_review_only",
        "left_source_ids": sorted({r.source_id for r in left}),
        "right_source_ids": sorted({r.source_id for r in right}),
        "left_totals": totals(left),
        "right_totals": totals(right),
        "shared_contract_count": len(shared),
        "exact_shared_contract_count": len(exact),
        "conflicting_shared_contract_count": len(conflicts),
        "left_only_contract_keys": [
            {"trade_date": d, "contract_id": c} for d, c in sorted(left_keys - right_keys)
        ],
        "right_only_contract_keys": [
            {"trade_date": d, "contract_id": c} for d, c in sorted(right_keys - left_keys)
        ],
        "exact_shared_contracts": exact,
        "conflicts": conflicts,
        "source_independence_verified": False,
        "daily_capture_completeness_verified": False,
        "canonical_promotion_allowed": False,
        "coverage_admission_allowed": False,
        "policy": "compare_only_no_source_trust_or_completeness_inference",
    }
