"""Effective-dated security master and corporate-action reference helpers.

These are evidence-driven lookup primitives, not an official NEPSE registry.
Dates are inclusive. Overlapping conflicting records fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class SecurityMasterRecord:
    security_id: str
    symbol: str
    instrument_type: str
    status: str
    valid_from: date
    valid_to: date | None
    evidence_id: str

    def __post_init__(self):
        if not all((self.security_id, self.symbol, self.instrument_type, self.status, self.evidence_id)):
            raise ValueError("security identity, type, status and evidence are required")
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must be on or after valid_from")


@dataclass(frozen=True)
class CorporateActionRecord:
    action_id: str
    security_id: str
    action_type: str
    ex_date: date
    announced_at: str
    available_at: str
    factor: float | None
    evidence_id: str

    def __post_init__(self):
        if not all((self.action_id, self.security_id, self.action_type, self.announced_at,
                    self.available_at, self.evidence_id)):
            raise ValueError("corporate action identifiers, timestamps and evidence are required")
        if self.factor is not None and self.factor <= 0:
            raise ValueError("corporate-action factor must be positive")


def security_as_of(records: Iterable[SecurityMasterRecord], on_date: date) -> dict:
    matches = [r for r in records if r.valid_from <= on_date and
               (r.valid_to is None or on_date <= r.valid_to)]
    identities = {(r.security_id, r.symbol, r.instrument_type, r.status) for r in matches}
    if not matches:
        return {"status": "not_found", "record": None}
    if len(identities) != 1:
        return {"status": "ambiguous", "record": None,
                "evidence_ids": sorted({r.evidence_id for r in matches})}
    return {"status": "resolved", "record": matches[0],
            "evidence_ids": sorted({r.evidence_id for r in matches})}


def corporate_actions_as_of(records: Iterable[CorporateActionRecord],
                             security_id: str, decision_time: str) -> dict:
    """Return actions known by decision_time; ex-date alone never grants hindsight."""
    from datetime import datetime, timezone

    def utc(value: str) -> datetime:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("corporate-action timestamps must be timezone-aware")
        return dt.astimezone(timezone.utc)

    cutoff = utc(decision_time)
    selected = []
    for action in records:
        if action.security_id != security_id:
            continue
        available = utc(action.available_at)
        if available <= cutoff:
            selected.append(action)
    selected.sort(key=lambda a: (a.ex_date, a.action_id))
    return {"security_id": security_id, "decision_time": cutoff.isoformat().replace("+00:00", "Z"),
            "actions": selected, "included_count": len(selected),
            "point_in_time_eligible": all(utc(a.available_at) <= cutoff for a in selected)}
