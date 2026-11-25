"""Effective-dated broker identity registry primitives.

Source broker codes are never globally merged by name similarity. Identity links
must be explicit and evidence-backed; unresolved codes remain unresolved.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_as_of(value: date | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        raise ValueError("as_of must be a date or YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("as_of must be a valid calendar date") from exc


@dataclass(frozen=True)
class BrokerNameObservation:
    source_id: str
    source_broker_code: str
    observed_name: str
    observed_at: date
    evidence_id: str

    def __post_init__(self):
        if not all(_nonblank(value) for value in (
            self.source_id, self.source_broker_code, self.observed_name, self.evidence_id
        )):
            raise ValueError("broker name observations require source, code, name and evidence")
        if not isinstance(self.observed_at, date) or isinstance(self.observed_at, datetime):
            raise ValueError("observed_at must be a date")


@dataclass(frozen=True)
class BrokerEntityName:
    broker_entity_id: str
    name: str
    valid_from: date | None
    valid_to: date | None
    evidence_id: str

    def __post_init__(self):
        if not all(_nonblank(value) for value in (self.broker_entity_id, self.name, self.evidence_id)):
            raise ValueError("broker entity names require ID, name and evidence")
        if self.valid_from is not None and (not isinstance(self.valid_from, date) or isinstance(self.valid_from, datetime)):
            raise ValueError("valid_from must be a date or None")
        if self.valid_to is not None and (not isinstance(self.valid_to, date) or isinstance(self.valid_to, datetime)):
            raise ValueError("valid_to must be a date or None")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to must be on or after valid_from")


def _normalized_name(value: str) -> str:
    """Conservative exact normalization; deliberately no fuzzy matching."""
    return " ".join(value.casefold().replace(".", " ").replace(",", " ").split())


def reconcile_broker_source_name(observed_name: str, as_of: date,
                                 known_names: list[BrokerEntityName]) -> dict:
    """Return review candidates only; a name match never creates a verified link."""
    if not _nonblank(observed_name):
        raise ValueError("observed_name is required")
    if not isinstance(as_of, date):
        raise ValueError("as_of must be a date")
    if not isinstance(known_names, list) or any(not isinstance(item, BrokerEntityName) for item in known_names):
        raise ValueError("known_names must be a list of BrokerEntityName records")
    candidates = [item for item in known_names
                  if (item.valid_from is None or item.valid_from <= as_of)
                  and (item.valid_to is None or as_of <= item.valid_to)
                  and _normalized_name(item.name) == _normalized_name(observed_name)]
    entities = sorted({item.broker_entity_id for item in candidates})
    if len(entities) == 1:
        return {"status": "candidate_requires_evidence", "broker_entity_id": entities[0],
                "evidence_ids": sorted({item.evidence_id for item in candidates}),
                "auto_verified": False}
    if len(entities) > 1:
        return {"status": "ambiguous", "broker_entity_id": None,
                "candidate_entity_ids": entities,
                "evidence_ids": sorted({item.evidence_id for item in candidates}),
                "auto_verified": False}
    return {"status": "unmapped", "broker_entity_id": None,
            "evidence_ids": [], "auto_verified": False}


def broker_name_history(observations: list[BrokerNameObservation]) -> list[dict]:
    """Preserve observed source names by source/code/date; never collapse history."""
    if not isinstance(observations, list) or any(not isinstance(item, BrokerNameObservation) for item in observations):
        raise ValueError("observations must be a list of BrokerNameObservation records")
    return [
        {"source_id": item.source_id, "source_broker_code": item.source_broker_code,
         "observed_name": item.observed_name, "observed_at": item.observed_at.isoformat(),
         "evidence_id": item.evidence_id}
        for item in sorted(observations, key=lambda x: (x.source_id, x.source_broker_code, x.observed_at, x.evidence_id))
    ]


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
    if not isinstance(link, BrokerIdentityLink):
        raise ValueError("link must be a BrokerIdentityLink record")
    if not _nonblank(link.source_id) or not _nonblank(link.source_broker_code):
        raise ValueError("source_id and source_broker_code are required")
    if not isinstance(link.link_status, str) or link.link_status not in VALID_LINK_STATUSES:
        raise ValueError(f"invalid link_status: {link.link_status}")
    if link.link_status == "verified":
        if not _nonblank(link.broker_entity_id) or not _nonblank(link.evidence_id):
            raise ValueError("verified links require broker_entity_id and evidence_id")
    elif link.broker_entity_id is not None:
        raise ValueError("non-verified links must not assign broker_entity_id")
    if link.valid_from is not None and (not isinstance(link.valid_from, date) or isinstance(link.valid_from, datetime)):
        raise ValueError("valid_from must be a date or None")
    if link.valid_to is not None and (not isinstance(link.valid_to, date) or isinstance(link.valid_to, datetime)):
        raise ValueError("valid_to must be a date or None")
    if link.valid_from and link.valid_to and link.valid_to < link.valid_from:
        raise ValueError("valid_to must be on or after valid_from")


def resolve_broker_identity(
    source_id: str,
    source_broker_code: str,
    links: list[BrokerIdentityLink],
    as_of: date | str | None = None,
) -> dict:
    """Resolve one explicit verified link valid on as_of; never fuzzy-match."""
    if not _nonblank(source_id) or not _nonblank(source_broker_code):
        raise ValueError("source_id and source_broker_code are required")
    if not isinstance(links, list) or any(not isinstance(link, BrokerIdentityLink) for link in links):
        raise ValueError("links must be a list of BrokerIdentityLink records")
    as_of = _parse_as_of(as_of)
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
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    totals: dict[tuple, dict] = {}
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise ValueError(f"row {index}: expected object")
        side = row.get("side")
        if not isinstance(side, str) or side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        try:
            quantity_decimal = Decimal(str(row["quantity"]))
            amount = Decimal(str(row["amount"]))
        except (KeyError, InvalidOperation, TypeError) as exc:
            raise ValueError("quantity and amount must be valid decimals") from exc
        if (not quantity_decimal.is_finite() or not amount.is_finite()
                or quantity_decimal < 0 or amount < 0
                or quantity_decimal != quantity_decimal.to_integral_value()):
            raise ValueError("quantity must be a non-negative integer and amount a finite non-negative decimal")
        quantity = int(quantity_decimal)
        status = row.get("identity_status", "unmapped")
        if not isinstance(status, str) or status not in VALID_LINK_STATUSES:
            raise ValueError("unsupported identity_status")
        entity = row.get("broker_entity_id") if status == "verified" else None
        if status == "verified" and not _nonblank(entity):
            raise ValueError("verified identity requires broker_entity_id")
        if status != "verified" and row.get("broker_entity_id") is not None:
            raise ValueError("unresolved identity cannot carry broker_entity_id")
        session_date = row.get("session_date")
        security_id = row.get("security_id")
        if not _nonblank(session_date) or not _nonblank(security_id):
            raise ValueError("session_date and security_id are required")
        _parse_as_of(session_date)
        key = (session_date, security_id, entity, side, status)
        item = totals.setdefault(key, {
            "session_date": key[0], "security_id": key[1],
            "broker_entity_id": entity, "side": side,
            "identity_status": status, "quantity": 0, "amount": Decimal("0"),
            "trade_count": 0,
        })
        item["quantity"] += quantity
        item["amount"] += amount
        item["trade_count"] += 1
    output = [totals[k] for k in sorted(totals, key=lambda x: tuple("" if v is None else str(v) for v in x))]
    for item in output:
        item["amount"] = str(item["amount"])
    return output
