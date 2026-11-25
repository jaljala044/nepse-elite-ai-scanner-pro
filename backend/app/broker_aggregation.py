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
        if not isinstance(row, dict):
            raise ValueError(f"row {index}: expected object")
        side = row.get("side")
        if not isinstance(side, str) or side not in {"buy", "sell"}:
            raise ValueError(f"row {index}: side must be buy or sell")
        status = row.get("identity_status")
        if not isinstance(status, str) or status not in {"verified", "unmapped", "ambiguous", "rejected"}:
            raise ValueError(f"row {index}: unsupported identity_status")
        broker_id = row.get("broker_entity_id")
        if status == "verified" and (not isinstance(broker_id, str) or not broker_id.strip()):
            raise ValueError(f"row {index}: verified identity requires a nonblank broker_entity_id")
        if status != "verified" and broker_id is not None:
            raise ValueError(f"row {index}: unresolved identity cannot carry broker_entity_id")
        try:
            amount, quantity = Decimal(str(row["amount"])), Decimal(str(row["quantity"]))
        except (KeyError, InvalidOperation) as exc:
            raise ValueError(f"row {index}: amount and quantity must be decimals") from exc
        if not amount.is_finite() or not quantity.is_finite() or amount < 0 or quantity < 0:
            raise ValueError(f"row {index}: amount and quantity must be finite and non-negative")
        required = ("trade_date", "symbol", "source_id", "contract_id", "source_payload_sha256")
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required):
            raise ValueError(f"row {index}: missing grouping or lineage field")
        if not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", row["trade_date"]):
            raise ValueError(f"row {index}: trade_date must be ISO date")
        try:
            date.fromisoformat(row["trade_date"])
        except ValueError as exc:
            raise ValueError(f"row {index}: trade_date must be ISO date") from exc
        if row["symbol"] != row["symbol"].strip().upper():
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
        if not isinstance(identity_evidence, list) or any(not isinstance(value, str) or not value.strip() for value in identity_evidence):
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


def reconcile_source_control_totals(rows: list[dict], controls: list[dict]) -> dict:
    """Compare party rows to source controls without double-counting buyer/seller sides.

    A contract contributes its gross amount and quantity once only when exactly
    one buy-side and one sell-side observation agree on both values.
    """
    from collections import defaultdict

    contracts = defaultdict(list)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"row {index}: expected object")
        required = ("source_id", "trade_date", "contract_id", "side", "amount", "quantity")
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in required[:3]):
            raise ValueError(f"row {index}: missing source control reconciliation field")
        if not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", row["trade_date"]):
            raise ValueError(f"row {index}: trade_date must be ISO date")
        try:
            date.fromisoformat(row["trade_date"])
        except ValueError as exc:
            raise ValueError(f"row {index}: trade_date must be ISO date") from exc
        if not isinstance(row["side"], str) or row["side"] not in {"buy", "sell"}:
            raise ValueError(f"row {index}: side must be buy or sell")
        try:
            amount = Decimal(str(row["amount"]))
            quantity = Decimal(str(row["quantity"]))
        except InvalidOperation as exc:
            raise ValueError(f"row {index}: invalid amount or quantity") from exc
        if not amount.is_finite() or not quantity.is_finite() or amount < 0 or quantity < 0:
            raise ValueError(f"row {index}: amount and quantity must be finite and non-negative")
        contracts[(row["source_id"], row["trade_date"], row["contract_id"])].append(
            {"side": row["side"], "amount": amount, "quantity": quantity}
        )

    actual = defaultdict(lambda: {
        "party_observation_count": 0, "contract_count": 0,
        "gross_amount": Decimal("0"), "quantity": Decimal("0"),
        "contract_anomalies": [],
    })
    for (source_id, trade_date, contract_id), parties in sorted(contracts.items()):
        summary = actual[(source_id, trade_date)]
        summary["party_observation_count"] += len(parties)
        sides = [party["side"] for party in parties]
        amounts = {party["amount"] for party in parties}
        quantities = {party["quantity"] for party in parties}
        if len(parties) != 2 or sorted(sides) != ["buy", "sell"] or len(amounts) != 1 or len(quantities) != 1:
            summary["contract_anomalies"].append({
                "contract_id": contract_id,
                "party_count": len(parties),
                "sides": sorted(sides),
                "amount_values": sorted(str(value) for value in amounts),
                "quantity_values": sorted(str(value) for value in quantities),
            })
            continue
        summary["contract_count"] += 1
        summary["gross_amount"] += next(iter(amounts))
        summary["quantity"] += next(iter(quantities))

    expected = {}
    for index, control in enumerate(controls):
        key = (control.get("source_id"), control.get("trade_date"))
        if (
            not isinstance(control.get("source_id"), str) or not control["source_id"].strip()
            or not isinstance(control.get("trade_date"), str)
            or not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", control["trade_date"])
            or key in expected
        ):
            raise ValueError(f"control {index}: missing or duplicate source/date control key")
        try:
            date.fromisoformat(control["trade_date"])
            contract_count = control["contract_count"]
            party_count = control["party_observation_count"]
            if (isinstance(contract_count, bool) or not isinstance(contract_count, int)
                    or contract_count < 0 or isinstance(party_count, bool)
                    or not isinstance(party_count, int) or party_count < 0):
                raise ValueError("control counts must be non-negative integers")
            expected[key] = {
                "contract_count": contract_count,
                "gross_amount": Decimal(str(control["gross_amount"])),
                "party_observation_count": party_count,
            }
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise ValueError(f"control {index}: invalid source control totals") from exc
        if not expected[key]["gross_amount"].is_finite() or expected[key]["gross_amount"] < 0:
            raise ValueError(f"control {index}: gross_amount must be finite and non-negative")

    results = []
    for key in sorted(set(actual) | set(expected)):
        observed = actual.get(key, {
            "party_observation_count": 0, "contract_count": 0,
            "gross_amount": Decimal("0"), "quantity": Decimal("0"),
            "contract_anomalies": [],
        })
        target = expected.get(key)
        differences = []
        if target is None:
            differences.append("missing_source_control")
        else:
            for field in ("contract_count", "gross_amount", "party_observation_count"):
                actual_value = observed[field]
                expected_value = target[field]
                if actual_value != expected_value:
                    differences.append(field)
        if observed["contract_anomalies"]:
            differences.append("contract_party_anomalies")
        results.append({
            "source_id": key[0], "trade_date": key[1],
            "observed_contract_count": observed["contract_count"],
            "observed_party_observation_count": observed["party_observation_count"],
            "observed_gross_amount": str(observed["gross_amount"]),
            "observed_quantity": str(observed["quantity"]),
            "contract_anomalies": observed["contract_anomalies"],
            "differences": differences,
            "status": "passed" if not differences else "failed",
        })
    return {
        "source_date_count": len(results),
        "passed_source_dates": sum(row["status"] == "passed" for row in results),
        "failed_source_dates": sum(row["status"] == "failed" for row in results),
        "results": results,
        "policy": "count_each_contract_once_only_when_buyer_and_seller_party_rows_agree",
    }
