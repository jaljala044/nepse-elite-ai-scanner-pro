"""Exact Decimal aggregation and identity-coverage accounting for broker parties."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from datetime import date
import re


def aggregate_broker_observations(rows: list[dict]) -> dict:
    """Aggregate date/security/broker/side while retaining unknown identity buckets.

    Coverage denominators are party observations, gross amount and quantity.
    Unresolved rows remain in the totals under a null canonical broker ID.
    """
    groups = {}
    coverage = defaultdict(lambda: {
        "party_observation_count": 0, "verified_observation_count": 0,
        "unresolved_observation_count": 0, "total_amount": Decimal("0"),
        "verified_amount": Decimal("0"), "unresolved_amount": Decimal("0"),
        "total_quantity": Decimal("0"), "verified_quantity": Decimal("0"),
        "unresolved_quantity": Decimal("0"),
    })
    seen_lineages = set()
    for index, row in enumerate(rows):
        side = row.get("side")
        if side not in {"buy", "sell"}:
            raise ValueError(f"row {index}: side must be buy or sell")
        status = row.get("identity_status")
        if status not in {"verified", "unmapped", "ambiguous", "rejected"}:
            raise ValueError(f"row {index}: unsupported identity_status")
        broker_id = row.get("broker_entity_id")
        if status == "verified" and not broker_id:
            raise ValueError(f"row {index}: verified identity requires broker_entity_id")
        if status != "verified" and broker_id is not None:
            raise ValueError(f"row {index}: unresolved identity cannot carry broker_entity_id")
        try:
            amount, quantity = Decimal(str(row["amount"])), Decimal(str(row["quantity"]))
        except (KeyError, InvalidOperation) as exc:
            raise ValueError(f"row {index}: amount and quantity must be decimals") from exc
        if not amount.is_finite() or not quantity.is_finite() or amount < 0 or quantity < 0:
            raise ValueError(f"row {index}: amount and quantity must be finite and non-negative")
        required = ("trade_date", "symbol", "source_id", "contract_id", "source_payload_sha256", "source_row_number")
        if any(row.get(k) in (None, "") for k in required):
            raise ValueError(f"row {index}: missing grouping or lineage field")
        try:
            date.fromisoformat(str(row["trade_date"]))
        except ValueError as exc:
            raise ValueError(f"row {index}: trade_date must be ISO date") from exc
        if str(row["symbol"]) != str(row["symbol"]).strip().upper():
            raise ValueError(f"row {index}: symbol must be uppercase")
        payload_hash = str(row["source_payload_sha256"]).lower()
        if not re.fullmatch(r"[0-9a-f]{64}", payload_hash):
            raise ValueError(f"row {index}: source_payload_sha256 must be a 64-character hex digest")
        try:
            source_row_number = int(row["source_row_number"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"row {index}: source_row_number must be a positive integer") from exc
        if source_row_number < 1 or str(source_row_number) != str(row["source_row_number"]):
            raise ValueError(f"row {index}: source_row_number must be a positive integer")
        identity_evidence = row.get("identity_evidence_ids", [])
        if not isinstance(identity_evidence, list) or any(not str(value).strip() for value in identity_evidence):
            raise ValueError(f"row {index}: identity_evidence_ids must be a list of nonblank IDs")
        if status == "verified" and not identity_evidence:
            raise ValueError(f"row {index}: verified identity requires identity evidence IDs")
        group_key = (row["trade_date"], row["symbol"], broker_id, side, status)
        item = groups.setdefault(group_key, {
            "trade_date": row["trade_date"], "symbol": row["symbol"],
            "broker_entity_id": broker_id, "side": side, "identity_status": status,
            "contract_count": 0, "quantity": Decimal("0"), "amount": Decimal("0"),
            "source_ids": set(), "evidence_ids": set(),
        })
        lineage = (payload_hash, source_row_number, side)
        if lineage in seen_lineages:
            raise ValueError(f"duplicate party observation lineage: {lineage}")
        seen_lineages.add(lineage)
        item["contract_count"] += 1
        item["quantity"] += quantity
        item["amount"] += amount
        item["source_ids"].add(row["source_id"])
        item["evidence_ids"].update(identity_evidence)

        c = coverage[(row["trade_date"], row["symbol"], side)]
        c["party_observation_count"] += 1
        c["total_amount"] += amount
        c["total_quantity"] += quantity
        if status == "verified":
            c["verified_observation_count"] += 1
            c["verified_amount"] += amount
            c["verified_quantity"] += quantity
        else:
            c["unresolved_observation_count"] += 1
            c["unresolved_amount"] += amount
            c["unresolved_quantity"] += quantity

    def serialize(item):
        return {k: (str(v) if isinstance(v, Decimal) else sorted(v) if isinstance(v, set) else v)
                for k, v in item.items()}

    aggregates = [serialize(groups[k]) for k in sorted(groups, key=lambda x: tuple("" if v is None else str(v) for v in x))]
    coverage_rows = []
    for key in sorted(coverage):
        c = coverage[key]
        coverage_rows.append({
            "trade_date": key[0], "symbol": key[1], "side": key[2],
            "party_observation_count": c["party_observation_count"],
            "verified_observation_count": c["verified_observation_count"],
            "unresolved_observation_count": c["unresolved_observation_count"],
            "observation_coverage": str(Decimal(c["verified_observation_count"]) / Decimal(c["party_observation_count"])),
            "total_amount": str(c["total_amount"]),
            "verified_amount": str(c["verified_amount"]),
            "unresolved_amount": str(c["unresolved_amount"]),
            "amount_coverage": str(c["verified_amount"] / c["total_amount"]) if c["total_amount"] else None,
            "total_quantity": str(c["total_quantity"]),
            "verified_quantity": str(c["verified_quantity"]),
            "unresolved_quantity": str(c["unresolved_quantity"]),
            "quantity_coverage": str(c["verified_quantity"] / c["total_quantity"]) if c["total_quantity"] else None,
        })
    return {
        "input_party_observation_rows": len(rows),
        "aggregate_rows": len(aggregates),
        "coverage_rows": len(coverage_rows),
        "aggregates": aggregates,
        "coverage": coverage_rows,
        "policy": "exact_decimal_totals_and_explicit_unresolved_denominators",
    }
