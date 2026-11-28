"""Deterministic, Decimal-based portfolio lot accounting.

This pure domain calculator does not persist data, infer ownership, apply corporate
actions, calculate taxes, or authorize valuation from unverified market marks.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be a finite decimal")
    return result


def _trade_date(value: Any, field: str = "trade_date") -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must be canonical YYYY-MM-DD")
    return parsed


def calculate_position(transactions: list[dict[str, Any]], *, market_mark: dict[str, Any] | None = None) -> dict[str, Any]:
    """Calculate weighted-average-cost position and realized/unrealized P&L.

    Transaction order is authoritative and must be chronological. Purchase fees
    are capitalized into cost basis; sale fees reduce net proceeds. Sells that
    exceed available shares fail closed. Market marks are optional and only
    accepted when explicitly verified, sourced, and not older than the last
    transaction date.
    """
    if not isinstance(transactions, list):
        raise ValueError("transactions must be a list")

    shares = Decimal("0")
    cost_basis = Decimal("0")
    realized = Decimal("0")
    invested_total = Decimal("0")
    sold_quantity = Decimal("0")
    seen_ids: set[str] = set()
    previous_day: date | None = None

    for index, tx in enumerate(transactions):
        if not isinstance(tx, dict):
            raise ValueError(f"transaction {index} must be a mapping")
        tx_id = tx.get("id")
        if not isinstance(tx_id, str) or not tx_id.strip() or tx_id in seen_ids:
            raise ValueError(f"transaction {index} has missing or duplicate id")
        seen_ids.add(tx_id)
        day = _trade_date(tx.get("trade_date"))
        if previous_day is not None and day < previous_day:
            raise ValueError("transactions must be chronological")
        previous_day = day

        kind = tx.get("type")
        if kind not in {"buy", "sell"}:
            raise ValueError(f"transaction {tx_id}: type must be buy or sell")
        quantity = _decimal(tx.get("quantity"), f"{tx_id}.quantity")
        price = _decimal(tx.get("unit_price"), f"{tx_id}.unit_price")
        fees = _decimal(tx.get("fees", "0"), f"{tx_id}.fees")
        if quantity <= 0 or quantity != quantity.to_integral_value():
            raise ValueError(f"transaction {tx_id}: quantity must be a positive whole share count")
        if price <= 0 or fees < 0:
            raise ValueError(f"transaction {tx_id}: price must be positive and fees non-negative")

        gross = quantity * price
        if kind == "buy":
            purchase_cost = gross + fees
            shares += quantity
            cost_basis += purchase_cost
            invested_total += purchase_cost
        else:
            if quantity > shares:
                raise ValueError(f"transaction {tx_id}: sell exceeds available shares")
            average_cost = cost_basis / shares
            allocated_cost = average_cost * quantity
            net_proceeds = gross - fees
            realized += net_proceeds - allocated_cost
            shares -= quantity
            cost_basis -= allocated_cost
            sold_quantity += quantity
            if shares == 0:
                cost_basis = Decimal("0")

    average_cost = cost_basis / shares if shares else Decimal("0")
    result: dict[str, Any] = {
        "status": "unvalued",
        "share_quantity": shares,
        "remaining_cost_basis": cost_basis,
        "average_cost_per_share": average_cost,
        "realized_pnl": realized,
        "cumulative_purchase_cost": invested_total,
        "sold_quantity": sold_quantity,
        "market_value": None,
        "unrealized_pnl": None,
        "total_pnl": None,
        "market_mark_status": "UNKNOWN",
        "as_of": None,
    }

    if market_mark is None:
        return result
    if not isinstance(market_mark, dict):
        raise ValueError("market_mark must be a mapping")
    try:
        mark_day = _trade_date(market_mark.get("as_of"), "market_mark.as_of")
        mark_price = _decimal(market_mark.get("price"), "market_mark.price")
    except ValueError:
        result["market_mark_status"] = "UNKNOWN_INVALID_MARK"
        return result
    source_ref = market_mark.get("source_ref")
    if (market_mark.get("verified") is not True or not isinstance(source_ref, str)
            or not source_ref.strip() or mark_price <= 0):
        result["market_mark_status"] = "UNKNOWN_UNVERIFIED_MARK"
        return result
    if previous_day is not None and mark_day < previous_day:
        result["market_mark_status"] = "UNKNOWN_STALE_MARK"
        return result

    market_value = shares * mark_price
    unrealized = market_value - cost_basis
    result.update({
        "status": "valued",
        "market_value": market_value,
        "unrealized_pnl": unrealized,
        "total_pnl": realized + unrealized,
        "market_mark_status": "VERIFIED_MARK",
        "as_of": mark_day.isoformat(),
        "market_mark_source_ref": source_ref,
    })
    return result
