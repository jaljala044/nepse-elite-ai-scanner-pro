"""Convert reconciled, identity-resolved floorsheet party rows into P4.33 batches.

No vendor acquisition occurs here. The caller must provide normalized contracts,
effective-dated verified security mappings, broker-identity join output, independent
source controls, source inventory and exchange-session finality.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from app.broker_aggregation import aggregate_broker_observations, reconcile_source_control_totals
from app.broker_ingestion import payload_hash, reconcile_broker_batch


class FloorsheetBrokerAdapterError(ValueError):
    """Invalid source evidence or adapter configuration."""


def _threshold(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise FloorsheetBrokerAdapterError("invalid_identity_coverage_threshold") from None
    if not result.is_finite() or not (Decimal("0") < result <= Decimal("1")):
        raise FloorsheetBrokerAdapterError("invalid_identity_coverage_threshold")
    return result


def _security_id(symbol: str, trade_date: str, registry: list[dict]) -> str:
    day = date.fromisoformat(trade_date)
    matches = []
    for row in registry:
        if not isinstance(row, dict) or row.get("symbol") != symbol or row.get("status") != "verified":
            continue
        try:
            start = date.fromisoformat(row["effective_from"])
            end = date.fromisoformat(row["effective_to"]) if row.get("effective_to") else None
        except (KeyError, TypeError, ValueError):
            continue
        if start <= day and (end is None or day <= end):
            matches.append(row)
    if len(matches) != 1:
        raise FloorsheetBrokerAdapterError(
            f"security_mapping_not_unique_and_verified:{symbol}:{trade_date}"
        )
    security_id = matches[0].get("security_id")
    if not isinstance(security_id, str) or not security_id.strip():
        raise FloorsheetBrokerAdapterError(f"invalid_security_id_mapping:{symbol}:{trade_date}")
    return security_id.strip()


def adapt_floorsheet_parties_to_broker_batch(
    join_result: Mapping[str, Any],
    *,
    source_controls: list[dict],
    security_registry: list[dict],
    verified_sessions: set[str],
    verified_session_finality: Mapping[str, str],
    expected_source_ids: set[str],
    received_source_ids: set[str],
    available_at: str,
    source_rights_evidence: Mapping[str, Mapping[str, Any]] | None = None,
    capture_batch_id: str | None = None,
    identity_coverage_threshold: Decimal = Decimal("0.95"),
) -> dict:
    """Return P4.33 IngestionReport plus source/identity audit metrics.

    Identity coverage is measured separately by party-row count, gross amount and
    quantity for each date/security/side. Unresolved identities remain in the
    coverage denominator and are never assigned a fabricated broker entity.
    """
    threshold = _threshold(identity_coverage_threshold)
    if not isinstance(join_result, Mapping):
        raise FloorsheetBrokerAdapterError("join_result_must_be_a_mapping")
    rows = join_result.get("rows")
    if not isinstance(rows, list) or not rows:
        raise FloorsheetBrokerAdapterError("joined_party_rows_required")
    if join_result.get("party_observation_rows") != len(rows):
        raise FloorsheetBrokerAdapterError("party_observation_row_count_mismatch")
    contract_count = join_result.get("input_contract_rows")
    if isinstance(contract_count, bool) or not isinstance(contract_count, int) or contract_count < 1:
        raise FloorsheetBrokerAdapterError("invalid_input_contract_count")
    if len(rows) != contract_count * 2:
        raise FloorsheetBrokerAdapterError("each_contract_must_have_buy_and_sell_party_rows")

    # A source contract must appear once per source/date/contract and have one row per side.
    contracts: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            raise FloorsheetBrokerAdapterError("party_row_must_be_an_object")
        key = (row.get("source_id"), row.get("trade_date"), row.get("contract_id"))
        contracts[key].append(row)
    for key, parties in contracts.items():
        if len(parties) != 2 or sorted(p.get("side") for p in parties) != ["buy", "sell"]:
            raise FloorsheetBrokerAdapterError(f"invalid_contract_party_pair:{key}")

    source_control = reconcile_source_control_totals(rows, source_controls)
    party_aggregates = aggregate_broker_observations(rows)
    coverage_rows = party_aggregates["coverage"]
    coverage_failures = []
    for item in coverage_rows:
        metrics = {
            "observation_coverage": item["observation_coverage"],
            "amount_coverage": item["amount_coverage"],
            "quantity_coverage": item["quantity_coverage"],
        }
        for metric, raw_value in metrics.items():
            try:
                value = Decimal(str(raw_value))
            except (InvalidOperation, TypeError):
                value = Decimal("-1")
            if not value.is_finite() or value < threshold:
                coverage_failures.append({
                    "trade_date": item["trade_date"], "symbol": item["symbol"],
                    "side": item["side"], "metric": metric, "value": raw_value,
                    "required": str(threshold),
                })

    grouped: dict[tuple, dict] = {}
    mapping_errors = []
    for row in rows:
        if row.get("identity_status") != "verified":
            continue
        try:
            security = _security_id(row["symbol"], row["trade_date"], security_registry)
        except (KeyError, FloorsheetBrokerAdapterError) as exc:
            mapping_errors.append({"symbol": row.get("symbol"),
                "trade_date": row.get("trade_date"), "reason": str(exc)})
            continue
        key = (row["source_id"], row["trade_date"], security,
               row["broker_entity_id"], row["side"])
        item = grouped.setdefault(key, {
            "source_id": row["source_id"], "session_date": row["trade_date"],
            "security_id": security, "broker_id": row["broker_entity_id"],
            "side": row["side"].upper(), "quantity": Decimal("0"),
            "amount": Decimal("0"), "source_row_numbers": [],
            "contract_ids": [], "source_payload_hashes": [],
            "identity_evidence_ids": [],
        })
        try:
            quantity, amount = Decimal(str(row["quantity"])), Decimal(str(row["amount"]))
        except (InvalidOperation, TypeError, ValueError):
            raise FloorsheetBrokerAdapterError("invalid_party_amount_or_quantity") from None
        if not quantity.is_finite() or not amount.is_finite() or quantity < 0 or amount < 0:
            raise FloorsheetBrokerAdapterError("invalid_party_amount_or_quantity")
        item["quantity"] += quantity
        item["amount"] += amount
        item["source_row_numbers"].append(int(row["source_row_number"]))
        item["contract_ids"].append(row["contract_id"])
        item["source_payload_hashes"].append(row["source_payload_sha256"])
        item["identity_evidence_ids"].extend(row.get("identity_evidence_ids", []))

    expected_ids = set(expected_source_ids or set())
    received_ids = set(received_source_ids or set())
    source_ratio = (Decimal(len(expected_ids & received_ids)) / Decimal(len(expected_ids))
                    if expected_ids else Decimal("0"))
    ingestion_rows = []
    for key, item in sorted(grouped.items()):
        lineage = sorted(zip(item["source_row_numbers"], item["contract_ids"],
                             item["source_payload_hashes"]))
        source_payload = {
            "source_id": item["source_id"], "trade_date": item["session_date"],
            "security_id": item["security_id"], "broker_entity_id": item["broker_id"],
            "side": item["side"], "quantity": str(item["quantity"]),
            "amount": str(item["amount"]), "contract_lineage": [
                {"source_row_number": n, "contract_id": c, "source_payload_sha256": h}
                for n, c, h in lineage
            ],
            "identity_evidence_ids": sorted(set(item["identity_evidence_ids"])),
        }
        digest = payload_hash(source_payload)
        evidence_id = "derived-floorsheet-party:" + digest[:32]
        ingestion_rows.append({
            "security_id": item["security_id"], "broker_id": item["broker_id"],
            "session_date": item["session_date"], "side": item["side"],
            "quantity": str(item["quantity"]), "amount": str(item["amount"]),
            "source_id": item["source_id"], "evidence_id": evidence_id,
            "source_payload": source_payload, "source_payload_sha256": digest,
            "source_row_count": len(lineage), "coverage_ratio": str(source_ratio),
            "raw_record_lineage": [
                {"raw_record_sha256": h, "raw_record_locator": f"csv:row:{n}",
                 "contract_id": c}
                for n, c, h in lineage
            ],
        })

    verified_brokers = {row["broker_id"] for row in ingestion_rows}
    if capture_batch_id is not None and (
        not isinstance(capture_batch_id, str) or not capture_batch_id.strip()
    ):
        raise FloorsheetBrokerAdapterError("invalid_capture_batch_id")
    report = reconcile_broker_batch(
        batch_id=(capture_batch_id.strip() if capture_batch_id is not None else
                  "floorsheet:" + ":".join(sorted(expected_ids)) + ":" + str(available_at)),
        rows=ingestion_rows, verified_brokers=verified_brokers,
        verified_sessions=set(verified_sessions or set()),
        expected_source_ids=expected_ids, received_source_ids=received_ids,
        available_at=available_at,
        verified_session_finality=verified_session_finality,
        source_rights_evidence=source_rights_evidence,
    )

    adapter_failures = []
    if source_control["failed_source_dates"]:
        adapter_failures.append({"reason": "source_control_reconciliation_failed",
                                 "results": source_control["results"]})
    if coverage_failures:
        adapter_failures.append({"reason": "identity_coverage_below_threshold",
                                 "failures": coverage_failures})
    if mapping_errors:
        adapter_failures.append({"reason": "effective_dated_security_mapping_failed",
                                 "failures": mapping_errors})
    if adapter_failures:
        report.quarantined.extend(adapter_failures)
        report.accepted = []

    return {
        "report": report,
        "memory_eligible": report.memory_eligible,
        "source_control": source_control,
        "party_aggregation": party_aggregates,
        "identity_coverage_threshold": str(threshold),
        "identity_coverage_failures": coverage_failures,
        "security_mapping_failures": mapping_errors,
        "unresolved_party_rows": sum(1 for row in rows if row.get("identity_status") != "verified"),
        "derived_ingestion_rows": len(ingestion_rows),
        "policy": "verified_effective_dated_identity_only_explicit_coverage_source_controls_and_session_finality",
    }
