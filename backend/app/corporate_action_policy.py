"""Corporate-action evidence ingestion and conservative adjustment eligibility."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal


ACTION_TYPES = {"bonus", "right", "split", "cash_dividend", "merger", "symbol_change", "other"}
APPROVED_POLICIES = {"raw_unadjusted_v1"}


def _time(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("corporate-action timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class CorporateActionEvidence:
    action_id: str
    security_id: str
    action_type: str
    ex_date: date
    announced_at: str
    available_at: str
    source_id: str
    source_tier: str
    evidence_id: str
    factor: str | None = None
    status: str = "confirmed"

    def __post_init__(self):
        if not all((self.action_id.strip(), self.security_id.strip(), self.source_id.strip(),
                    self.source_tier.strip(), self.evidence_id.strip())):
            raise ValueError("corporate action identifiers, source tier and evidence are required")
        if self.action_type not in ACTION_TYPES:
            raise ValueError("unsupported corporate action type")
        if self.status not in {"confirmed", "provisional", "cancelled", "disputed"}:
            raise ValueError("unsupported corporate action status")
        announced, available = _time(self.announced_at), _time(self.available_at)
        if available < announced:
            raise ValueError("available_at cannot precede announced_at")
        if self.factor is not None:
            value = Decimal(self.factor)
            if not value.is_finite() or value <= 0:
                raise ValueError("factor must be a finite positive decimal")


def corporate_action_as_known(actions: list[CorporateActionEvidence], *,
                              security_id: str, decision_time: str) -> dict:
    cutoff = _time(decision_time)
    visible = [a for a in actions if a.security_id == security_id
               and _time(a.available_at) <= cutoff]
    selected = [a for a in visible if a.status == "confirmed"]
    selected.sort(key=lambda a: (a.ex_date, a.action_id))
    excluded = sorted(
        ({"action_id": a.action_id, "status": a.status, "evidence_id": a.evidence_id}
         for a in visible if a.status != "confirmed"),
        key=lambda row: row["action_id"],
    )
    return {
        "security_id": security_id,
        "decision_time": cutoff.isoformat().replace("+00:00", "Z"),
        "actions": selected,
        "visible_action_count": len(visible),
        "excluded_visible_actions": excluded,
        "evidence_ids": sorted({a.evidence_id for a in visible}),
        "all_visible_actions_confirmed": all(a.status == "confirmed" for a in visible),
    }


def evaluate_adjustment_eligibility(action: CorporateActionEvidence, *,
                                    policy_version: str,
                                    decision_time: str,
                                    independently_reviewed: bool = False) -> dict:
    """No adjusted series is emitted; this only records a fail-closed eligibility decision."""
    visible = _time(action.available_at) <= _time(decision_time)
    eligible = (policy_version in APPROVED_POLICIES and visible
                and action.status == "confirmed" and independently_reviewed)
    return {
        "action_id": action.action_id,
        "eligible_for_adjustment_review": eligible,
        "adjustment_applied": False,
        "raw_price_series_mutated": False,
        "reason": ("eligible_for_separate_review" if eligible else
                   "policy_or_visibility_or_confirmation_or_review_gate_not_met"),
        "policy_version": policy_version,
    }
