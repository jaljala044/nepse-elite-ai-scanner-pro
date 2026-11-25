"""Evidence-backed NEPSE session-state resolution with point-in-time visibility."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone


SESSION_STATES = {"confirmed_trading_session", "confirmed_exchange_closure",
                  "exceptional_session", "unknown"}
PRIMARY_TIERS = {"exchange", "official_regulator"}


def _utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("session evidence timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class SessionEvidence:
    session_date: date
    state: str
    source_id: str
    source_tier: str
    evidence_id: str
    available_at: str
    detail: str = ""

    def __post_init__(self):
        if self.state not in SESSION_STATES:
            raise ValueError("unsupported session state")
        if not all((self.source_id.strip(), self.evidence_id.strip())):
            raise ValueError("session evidence source and ID are required")
        _utc(self.available_at)


def resolve_session_state(session_date: date, evidence: list[SessionEvidence],
                          decision_time: str, *, require_primary: bool = True) -> dict:
    cutoff = _utc(decision_time)
    visible = [item for item in evidence if item.session_date == session_date
               and _utc(item.available_at) <= cutoff
               and (not require_primary or item.source_tier in PRIMARY_TIERS)]
    states = {item.state for item in visible if item.state != "unknown"}
    if len(states) > 1:
        status, resolved = "conflicting_evidence", "unknown"
    elif len(states) == 1:
        resolved = next(iter(states))
        status = "verified" if resolved != "unknown" else "unknown"
    else:
        resolved, status = "unknown", "unknown"
    return {
        "session_date": session_date.isoformat(), "status": status,
        "session_state": resolved,
        "evidence_ids": sorted({x.evidence_id for x in visible}),
        "visible_evidence_count": len(visible),
        "decision_time": cutoff.isoformat().replace("+00:00", "Z"),
        "is_confirmed_trading_session": status == "verified" and resolved in {
            "confirmed_trading_session", "exceptional_session"},
        "is_confirmed_closed": status == "verified" and resolved == "confirmed_exchange_closure",
        "missing_evidence_means_closed": False,
    }
