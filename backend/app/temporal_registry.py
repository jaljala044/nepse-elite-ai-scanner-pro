"""Effective-dated security master and corporate-action reference helpers.

These are evidence-driven lookup primitives, not an official NEPSE registry.
Dates are inclusive. Conflicting overlaps and unverified identities fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from datetime import date, datetime, timezone
import math
from typing import Iterable

ALLOWED_INSTRUMENT_TYPES = {
    "equity", "mutual_fund", "convertible_debenture",
    "non_convertible_debenture", "preference_share", "other",
}
ALLOWED_SECURITY_STATUSES = {
    "active", "suspended", "delisted", "inactive", "pending",
}
ALLOWED_SECURITY_EVIDENCE_TIERS = {
    "primary_nepse_notice",
    "secondary_notice",
    "secondary_first_trade_archive_match",
    "historical_archive_inference",
    "current_snapshot_only",
    "unverified",
}
ALLOWED_ACTION_EVIDENCE_TIERS = {
    "primary_nepse_notice", "secondary_notice", "secondary_archive", "unverified",
}
ALLOWED_ACTION_VERIFICATION_STATUSES = {
    "verified_primary", "verified_secondary", "unverified",
}


@dataclass(frozen=True)
class SecurityMasterRecord:
    security_id: str
    symbol: str
    instrument_type: str
    status: str
    valid_from: date
    valid_to: date | None
    evidence_id: str
    evidence_tier: str = "current_snapshot_only"
    stable_id_verified: bool = False
    effective_date_verified: bool = False

    def __post_init__(self):
        if not all((self.security_id, self.symbol, self.instrument_type, self.status, self.evidence_id)):
            raise ValueError("security identity, type, status and evidence are required")
        if self.instrument_type not in ALLOWED_INSTRUMENT_TYPES:
            raise ValueError(f"unsupported instrument_type: {self.instrument_type}")
        if self.status not in ALLOWED_SECURITY_STATUSES:
            raise ValueError(f"unsupported security status: {self.status}")
        if self.evidence_tier not in ALLOWED_SECURITY_EVIDENCE_TIERS:
            raise ValueError(f"unsupported security evidence tier: {self.evidence_tier}")
        if not isinstance(self.stable_id_verified, bool) or not isinstance(self.effective_date_verified, bool):
            raise ValueError("security identity verification flags must be boolean")
        if (self.stable_id_verified or self.effective_date_verified) and self.evidence_tier != "primary_nepse_notice":
            raise ValueError("historical identity verification requires primary NEPSE evidence")
        if not isinstance(self.valid_from, date) or (self.valid_to is not None and not isinstance(self.valid_to, date)):
            raise ValueError("security lifecycle dates must be date values")
        if self.symbol != self.symbol.strip().upper():
            raise ValueError("security symbol must be uppercase and whitespace-free")
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
    evidence_tier: str = "unverified"
    verification_status: str = "unverified"
    adjustment_factor_verified: bool = False

    def __post_init__(self):
        if not all((self.action_id, self.security_id, self.action_type, self.announced_at,
                    self.available_at, self.evidence_id)):
            raise ValueError("corporate action identifiers, timestamps and evidence are required")
        if not isinstance(self.ex_date, date):
            raise ValueError("corporate-action ex_date must be a date")
        if self.evidence_tier not in ALLOWED_ACTION_EVIDENCE_TIERS:
            raise ValueError(f"unsupported corporate-action evidence tier: {self.evidence_tier}")
        if self.verification_status not in ALLOWED_ACTION_VERIFICATION_STATUSES:
            raise ValueError(f"unsupported corporate-action verification status: {self.verification_status}")
        if self.verification_status == "verified_primary" and self.evidence_tier != "primary_nepse_notice":
            raise ValueError("primary-verified corporate action requires primary NEPSE evidence")
        if self.verification_status == "verified_secondary" and self.evidence_tier not in {"secondary_notice", "secondary_archive"}:
            raise ValueError("secondary-verified corporate action requires a secondary evidence tier")
        if not isinstance(self.adjustment_factor_verified, bool):
            raise ValueError("adjustment_factor_verified must be boolean")
        if self.adjustment_factor_verified and (
            self.verification_status != "verified_primary"
            or self.evidence_tier != "primary_nepse_notice"
            or self.factor is None
        ):
            raise ValueError("adjustment factor use requires a primary-verified factor")
        def parse_aware(value: str, field: str) -> datetime:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
            if parsed.tzinfo is None:
                raise ValueError(f"{field} must be timezone-aware")
            return parsed.astimezone(timezone.utc)
        announced = parse_aware(self.announced_at, "announced_at")
        available = parse_aware(self.available_at, "available_at")
        if available < announced:
            raise ValueError("available_at cannot precede announced_at")
        if self.factor is not None:
            try:
                factor = float(self.factor)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("corporate-action factor must be finite and positive") from exc
            if not math.isfinite(factor) or factor <= 0:
                raise ValueError("corporate-action factor must be finite and positive")


def validate_security_master_snapshot(records: Iterable[SecurityMasterRecord]) -> dict:
    """Validate lifecycle overlaps and report which rows are actually admissible."""
    materialized = list(records)
    if not materialized:
        raise ValueError("security master snapshot is empty")
    security_groups = defaultdict(list)
    symbol_groups = defaultdict(list)
    for record in materialized:
        security_groups[record.security_id].append(record)
        symbol_groups[record.symbol].append(record)

    def overlaps(left: SecurityMasterRecord, right: SecurityMasterRecord) -> bool:
        left_end = left.valid_to or date.max
        right_end = right.valid_to or date.max
        return left.valid_from <= right_end and right.valid_from <= left_end

    for security_id, group in security_groups.items():
        for index, left in enumerate(group):
            for right in group[index + 1:]:
                if overlaps(left, right):
                    left_identity = (left.symbol, left.instrument_type, left.status)
                    right_identity = (right.symbol, right.instrument_type, right.status)
                    if left_identity != right_identity:
                        raise ValueError(f"overlapping conflicting lifecycle rows for security_id {security_id}")
    for symbol, group in symbol_groups.items():
        for index, left in enumerate(group):
            for right in group[index + 1:]:
                if left.security_id != right.security_id and overlaps(left, right):
                    raise ValueError(f"symbol {symbol} overlaps across distinct security IDs")
    primary_verified = sum(
        1 for row in materialized
        if row.evidence_tier == "primary_nepse_notice"
        and row.stable_id_verified and row.effective_date_verified
    )
    return {
        "record_count": len(materialized),
        "unique_security_ids": len(security_groups),
        "unique_symbols": len(symbol_groups),
        "primary_verified_identity_count": primary_verified,
        "unverified_identity_count": len(materialized) - primary_verified,
        "identity_admission_status": "fully_verified" if primary_verified == len(materialized) else "partial_or_unverified",
        "instrument_type_counts": {
            kind: sum(1 for row in materialized if row.instrument_type == kind)
            for kind in sorted({row.instrument_type for row in materialized})
        },
        "status_counts": {
            status: sum(1 for row in materialized if row.status == status)
            for status in sorted({row.status for row in materialized})
        },
        "validation_status": "valid_snapshot",
    }


def security_as_of(records: Iterable[SecurityMasterRecord], on_date: date) -> dict:
    """Resolve only identities with primary proof of both stable ID and effective date."""
    matches = [r for r in records if r.valid_from <= on_date and
               (r.valid_to is None or on_date <= r.valid_to)]
    identities = {(r.security_id, r.symbol, r.instrument_type, r.status) for r in matches}
    if not matches:
        return {"status": "not_found", "record": None}
    if len(identities) != 1:
        return {"status": "ambiguous", "record": None,
                "evidence_ids": sorted({r.evidence_id for r in matches})}
    eligible = [
        row for row in matches
        if row.evidence_tier == "primary_nepse_notice"
        and row.stable_id_verified is True
        and row.effective_date_verified is True
    ]
    if not eligible:
        return {
            "status": "unverified_identity",
            "record": None,
            "evidence_ids": sorted({r.evidence_id for r in matches}),
            "evidence_tiers": sorted({r.evidence_tier for r in matches}),
            "stable_id_verified": False,
            "effective_date_verified": False,
        }
    return {"status": "resolved", "record": eligible[0],
            "evidence_ids": sorted({r.evidence_id for r in eligible}),
            "stable_id_verified": True, "effective_date_verified": True}


def corporate_actions_as_of(records: Iterable[CorporateActionRecord],
                             security_id: str, decision_time: str) -> dict:
    """Return verified actions known by decision_time; only primary factors may adjust OHLCV."""
    def utc(value: str) -> datetime:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("corporate-action timestamps must be timezone-aware")
        return dt.astimezone(timezone.utc)

    cutoff = utc(decision_time)
    matching = [action for action in records if action.security_id == security_id]
    known = [action for action in matching if utc(action.available_at) <= cutoff]
    late = [action for action in matching if utc(action.available_at) > cutoff]
    verified = [action for action in known if action.verification_status in {"verified_primary", "verified_secondary"}]
    unverified = [action for action in known if action.verification_status == "unverified"]
    verified.sort(key=lambda action: (action.ex_date, action.action_id))
    adjustment_actions = [
        action for action in verified
        if action.verification_status == "verified_primary"
        and action.evidence_tier == "primary_nepse_notice"
        and action.adjustment_factor_verified is True
        and action.factor is not None
    ]
    return {
        "security_id": security_id,
        "decision_time": cutoff.isoformat().replace("+00:00", "Z"),
        "actions": verified,
        "adjustment_actions": adjustment_actions,
        "included_count": len(verified),
        "adjustment_eligible_count": len(adjustment_actions),
        "excluded_unverified_count": len(unverified),
        "late_action_count": len(late),
        "excluded_unverified_evidence_ids": sorted({action.evidence_id for action in unverified}),
        "evidence_ids": sorted({action.evidence_id for action in verified}),
        "point_in_time_eligible": not unverified,
        "source_universe_completeness_verified": False,
    }
