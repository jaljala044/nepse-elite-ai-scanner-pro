"""Fail-closed adapter from rolling broker profiles to scanner context.

Outputs descriptive breadth only. It is intentionally excluded from weighted
scores until a separately reviewed, calibrated broker component is approved.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


_ALLOWED = {"net_buy_dominant", "net_sell_dominant", "balanced_or_no_activity"}
_REQUIRED_POLICY = "complete_source_sessions_only_no_zero_filling_for_missing_sessions_point_in_time_descriptive_only"


def _aware(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise ValueError(f"{field}_invalid") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed


def build_broker_profile_scanner_context(
    profile_snapshot: dict | None,
    *,
    decision_time: str,
    expected_security_ids: list[str],
    minimum_brokers: int = 3,
    minimum_coverage: Decimal = Decimal("0.95"),
) -> dict:
    """Summarize broker directional breadth by security and rolling window.

    A profile snapshot is admitted only when it was generated under the P4.37
    complete-session policy and is not later than the scanner decision time.
    No aggregate net-money total is used: buyer and seller sides are two sides
    of the same matched trades, so summing broker net amounts is misleading.
    """
    decision = _aware(decision_time, "decision_time")
    if isinstance(minimum_brokers, bool) or not isinstance(minimum_brokers, int) or minimum_brokers < 1:
        raise ValueError("minimum_brokers_must_be_positive_integer")
    try:
        threshold = Decimal(str(minimum_coverage))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("minimum_coverage_invalid") from None
    if not threshold.is_finite() or not (Decimal("0") < threshold <= Decimal("1")):
        raise ValueError("minimum_coverage_invalid")

    expected = sorted({str(item).strip() for item in expected_security_ids if str(item).strip()})
    empty = {
        security: {"status": "insufficient_evidence", "score": None,
                   "windows": {}, "interpretation": "No eligible rolling broker profile supplied."}
        for security in expected
    }
    if not isinstance(profile_snapshot, dict):
        return {"status": "insufficient_evidence", "score_eligible": False,
                "securities": empty, "reason": "rolling_broker_profile_snapshot_missing",
                "interpretation": "Broker profiles are context only and do not alter weighted scanner scores."}
    if profile_snapshot.get("policy") != _REQUIRED_POLICY:
        return {"status": "insufficient_evidence", "score_eligible": False,
                "securities": empty, "reason": "rolling_profile_policy_unrecognized",
                "interpretation": "Broker profiles are context only and do not alter weighted scanner scores."}
    try:
        snapshot_time = _aware(profile_snapshot.get("as_of_timestamp"), "profile_as_of_timestamp")
        snapshot_date = date.fromisoformat(profile_snapshot.get("as_of_date"))
    except (ValueError, TypeError):
        return {"status": "insufficient_evidence", "score_eligible": False,
                "securities": empty, "reason": "rolling_profile_as_of_invalid",
                "interpretation": "Broker profiles are context only and do not alter weighted scanner scores."}
    if snapshot_time > decision:
        return {"status": "withheld", "score_eligible": False, "securities": empty,
                "reason": "rolling_profile_is_after_scanner_decision_time",
                "interpretation": "Future or late-arriving broker evidence is excluded."}

    rows = profile_snapshot.get("profiles")
    if not isinstance(rows, list):
        rows = []
    grouped: dict[str, dict[str, list[dict]]] = {}
    rejected = 0
    for row in rows:
        if not isinstance(row, dict):
            rejected += 1
            continue
        security = row.get("security_id")
        window = row.get("window")
        if security not in expected or not isinstance(window, str) or not window:
            rejected += 1
            continue
        try:
            coverage = Decimal(str(row.get("coverage_ratio")))
            requested = row.get("requested_sessions")
            expected_sessions = row.get("expected_sessions")
            covered = row.get("complete_source_sessions")
            valid_counts = (
                isinstance(requested, int) and not isinstance(requested, bool) and requested > 0
                and isinstance(expected_sessions, int) and expected_sessions == requested
                and isinstance(covered, int) and 0 <= covered <= requested
            )
        except (InvalidOperation, TypeError, ValueError):
            rejected += 1
            continue
        if (row.get("status") != "descriptive_only" or row.get("directional_summary") not in _ALLOWED
                or not coverage.is_finite() or coverage < threshold or coverage > 1 or not valid_counts
                or not isinstance(row.get("broker_id"), str) or not row["broker_id"].strip()):
            rejected += 1
            continue
        grouped.setdefault(security, {}).setdefault(window, []).append(row)

    securities = {}
    for security in expected:
        windows = {}
        for window, items in sorted(grouped.get(security, {}).items()):
            broker_ids = [item["broker_id"] for item in items]
            if len(broker_ids) != len(set(broker_ids)):
                windows[window] = {"status": "insufficient_evidence", "broker_count": len(set(broker_ids)),
                                   "reason": "duplicate_broker_window_profile"}
                continue
            counts = {label: sum(1 for item in items if item["directional_summary"] == label)
                      for label in sorted(_ALLOWED)}
            enough = len(items) >= minimum_brokers
            if not enough:
                label = "insufficient_evidence"
                status = "insufficient_evidence"
            elif counts["net_buy_dominant"] > counts["net_sell_dominant"]:
                label, status = "buy_side_breadth", "descriptive_only"
            elif counts["net_sell_dominant"] > counts["net_buy_dominant"]:
                label, status = "sell_side_breadth", "descriptive_only"
            else:
                label, status = "mixed_or_balanced", "descriptive_only"
            windows[window] = {
                "status": status, "directional_breadth": label, "broker_count": len(items),
                "minimum_brokers": minimum_brokers, "broker_direction_counts": counts,
                "coverage_minimum": str(threshold), "score": None,
                "interpretation": "Descriptive broker directional breadth; not ownership, operator intent, accumulation/distribution proof, or a trade signal.",
            }
        securities[security] = {
            "status": "descriptive_only" if windows else "insufficient_evidence",
            "score": None, "windows": windows,
            "interpretation": "Separate scanner context; excluded from weighted component scoring and BUY/SELL decisions.",
        }
    return {
        "status": "descriptive_only" if any(item["windows"] for item in securities.values()) else "insufficient_evidence",
        "score_eligible": False, "as_of_date": snapshot_date.isoformat(),
        "as_of_timestamp": snapshot_time.isoformat(), "minimum_brokers": minimum_brokers,
        "minimum_coverage": str(threshold), "rejected_profile_rows": rejected,
        "securities": securities,
        "interpretation": "Broker profile breadth is contextual evidence only; no probability, score, BUY, SELL or HOLD action is produced.",
    }
