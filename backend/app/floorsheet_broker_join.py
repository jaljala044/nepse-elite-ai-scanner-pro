"""Join normalized floorsheet contracts to effective-dated broker identities.

This is an identity-resolution adapter, not a source-file parser. It preserves
both broker codes and every contract; unresolved parties remain explicit.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

from app.broker_identity import BrokerIdentityLink, resolve_broker_identity
from app.floorsheet_contract import FloorsheetContract


def resolve_contract_brokers(
    contracts: Iterable[FloorsheetContract],
    links: list[BrokerIdentityLink],
    *,
    source_id: str,
) -> dict:
    """Emit buy/sell party observations for each contract without dropping rows."""
    if not source_id.strip():
        raise ValueError("source_id is required")
    output = []
    counts = {"verified": 0, "unmapped": 0, "ambiguous": 0}
    for contract in contracts:
        trade_date = date.fromisoformat(contract.trade_date)
        for side, code in (
            ("buy", contract.buyer_broker_code),
            ("sell", contract.seller_broker_code),
        ):
            identity = resolve_broker_identity(source_id, code, links, trade_date)
            status = identity["status"]
            counts[status] = counts.get(status, 0) + 1
            output.append({
                "source_id": source_id,
                "source_payload_sha256": contract.source_payload_sha256,
                "source_row_number": contract.source_row_number,
                "trade_date": contract.trade_date,
                "contract_id": contract.contract_id,
                "symbol": contract.symbol,
                "side": side,
                "source_broker_code": code,
                "broker_entity_id": identity["broker_entity_id"],
                "identity_status": status,
                "identity_evidence_ids": identity["evidence_ids"],
                "quantity": str(contract.quantity),
                "rate": str(contract.rate),
                "amount": str(contract.amount),
            })
    return {
        "input_contract_rows": len({(r["source_payload_sha256"], r["source_row_number"]) for r in output}),
        "party_observation_rows": len(output),
        "counts_by_identity_status": counts,
        "rows": output,
        "unresolved_rows_retained": sum(1 for r in output if r["identity_status"] != "verified"),
        "policy": "resolve_as_of_trade_date_and_retain_unresolved",
    }
