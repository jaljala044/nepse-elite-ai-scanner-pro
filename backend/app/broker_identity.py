"""Effective-dated broker identity registry primitives.

Source broker codes are never globally merged by name similarity. Identity links
must be explicit and evidence-backed; unresolved codes remain unresolved.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


VALID_LINK_STATUSES = {"verified", "ambiguous", "unmapped", "rejected"}


@dataclass(frozen=True)
class BrokerSourceCode:
    source_id: str
    source_broker_code: str
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass(frozen=True)
class BrokerIdentityLink:
    source_id: str
    source_broker_code: str
    broker_entity_id: str | None
    link_status: str
    evidence_id: str | None
    reviewed_at: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


def validate_identity_link(link: BrokerIdentityLink) -> None:
    if not link.source_id.strip() or not link.source_broker_code.strip():
        raise ValueError("source_id and source_broker_code are required")
    if link.link_status not in VALID_LINK_STATUSES:
        raise ValueError(f"invalid link_status: {link.link_status}")
    if link.link_status == "verified":
        if not link.broker_entity_id or not link.evidence_id:
            raise ValueError("verified links require broker_entity_id and evidence_id")
    elif link.broker_entity_id is not None:
        raise ValueError("non-verified links must not assign broker_entity_id")
    if link.valid_from and link.valid_to and link.valid_to < link.valid_from:
        raise ValueError("valid_to must be on or after valid_from")


def resolve_broker_identity(
    source_id: str,
    source_broker_code: str,
    links: list[BrokerIdentityLink],
    as_of: date | str | None = None,
) -> dict:
    """Resolve one explicit verified link valid on as_of; never fuzzy-match."""
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    matches = [
        link for link in links
        if link.source_id == source_id and link.source_broker_code == source_broker_code
    ]
    for link in matches:
        validate_identity_link(link)
    if as_of is None:
        matches = [x for x in matches if x.valid_from is None and x.valid_to is None]
    else:
        matches = [x for x in matches
                   if (x.valid_from is None or x.valid_from <= as_of)
                   and (x.valid_to is None or as_of <= x.valid_to)]
    if not matches:
        return {"status": "unmapped", "broker_entity_id": None, "evidence_ids": []}
    verified = [x for x in matches if x.link_status == "verified"]
    if len(verified) == 1 and len(matches) == 1:
        x = verified[0]
        return {"status": "verified", "broker_entity_id": x.broker_entity_id,
                "evidence_ids": [x.evidence_id]}
    if any(x.link_status == "ambiguous" for x in matches) or len(matches) > 1:
        return {"status": "ambiguous", "broker_entity_id": None,
                "evidence_ids": sorted({x.evidence_id for x in matches if x.evidence_id})}
    return {"status": "unmapped", "broker_entity_id": None,
            "evidence_ids": sorted({x.evidence_id for x in matches if x.evidence_id})}


def aggregate_broker_side(records: list[dict]) -> list[dict]:
    """Aggregate contract rows at date/security/broker/side grain.

    Rows without verified broker identity are retained in explicit unknown
    buckets; callers must not treat them as mapped entities.
    """
    totals: dict[tuple, dict] = {}
    for row in records:
        side = row.get("side")
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        quantity = int(row["quantity"])
        amount = float(row["amount"])
        if quantity < 0 or amount < 0:
            raise ValueError("quantity and amount must be non-negative")
        status = row.get("identity_status", "unmapped")
        entity = row.get("broker_entity_id") if status == "verified" else None
        key = (row["session_date"], row["security_id"], entity, side, status)
        item = totals.setdefault(key, {
            "session_date": key[0], "security_id": key[1],
            "broker_entity_id": entity, "side": side,
            "identity_status": status, "quantity": 0, "amount": 0.0,
            "trade_count": 0,
        })
        item["quantity"] += quantity
        item["amount"] += amount
        item["trade_count"] += 1
    return [totals[k] for k in sorted(totals, key=lambda x: tuple("" if v is None else str(v) for v in x))]
