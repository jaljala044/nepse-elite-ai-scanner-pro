"""Convert canonical floorsheet contracts to conservative broker-party observations."""
from __future__ import annotations

from typing import Iterable

from app.broker_aggregation import aggregate_broker_observations
from app.floorsheet_contract import FloorsheetContract


def build_broker_party_observations(
    contracts: Iterable[FloorsheetContract],
    *,
    identity_links: dict[tuple[str, str], dict] | None = None,
) -> list[dict]:
    """Emit one buy and one sell party observation per contract.

    Identity links are keyed by (source_id, source_broker_code). Missing links are
    explicitly unmapped. The source code is preserved in every row so different
    unresolved codes cannot be collapsed into one unknown broker bucket.
    """
    if identity_links is None:
        identity_links = {}
    if not isinstance(identity_links, dict):
        raise ValueError("identity_links must be a mapping keyed by source and broker code")

    output = []
    for index, contract in enumerate(contracts):
        if not isinstance(contract, FloorsheetContract):
            raise ValueError(f"contract {index} must be a FloorsheetContract")
        parties = (
            ("buy", contract.buyer_broker_code),
            ("sell", contract.seller_broker_code),
        )
        for side, source_code in parties:
            link = identity_links.get((contract.source_id, source_code))
            if link is None:
                status = "unmapped"
                entity_id = None
                evidence_ids = []
            else:
                if not isinstance(link, dict):
                    raise ValueError("identity link values must be objects")
                status = link.get("status")
                entity_id = link.get("broker_entity_id")
                evidence_ids = link.get("evidence_ids", [])
                if status not in {"verified", "unmapped", "ambiguous", "rejected"}:
                    raise ValueError("identity link status is unsupported")
                if status == "verified":
                    if not isinstance(entity_id, str) or not entity_id.strip():
                        raise ValueError("verified identity requires broker_entity_id")
                    if not isinstance(evidence_ids, list) or not evidence_ids:
                        raise ValueError("verified identity requires evidence_ids")
                elif entity_id is not None:
                    raise ValueError("unresolved identity cannot carry broker_entity_id")
                if not isinstance(evidence_ids, list) or any(
                    not isinstance(value, str) or not value.strip() for value in evidence_ids
                ):
                    raise ValueError("evidence_ids must be a list of nonblank strings")
            output.append({
                "trade_date": contract.trade_date,
                "symbol": contract.symbol,
                "broker_entity_id": entity_id,
                "source_broker_code": source_code,
                "identity_status": status,
                "side": side,
                "amount": str(contract.amount),
                "quantity": str(contract.quantity),
                "source_id": contract.source_id,
                "contract_id": contract.contract_id,
                "source_payload_sha256": contract.source_payload_sha256,
                "source_row_number": contract.source_row_number,
                "identity_evidence_ids": list(evidence_ids),
            })
    return output


def aggregate_floorsheet_broker_parties(
    contracts: Iterable[FloorsheetContract],
    *,
    identity_links: dict[tuple[str, str], dict] | None = None,
) -> dict:
    """Build source-code-preserving party observations and aggregate them."""
    observations = build_broker_party_observations(contracts, identity_links=identity_links)
    return aggregate_broker_observations(observations)
