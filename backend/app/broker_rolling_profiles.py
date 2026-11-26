"""Point-in-time rolling broker/security behaviour profiles.

Zero activity is inferred only when a verified exchange session also has a
complete, reconciled, identity-complete source manifest. Incomplete sessions
reduce coverage and are never silently treated as zero.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from math import ceil
from typing import Any, Iterable


DEFAULT_WINDOWS = {"weekly": 5, "monthly": 21, "yearly": 252}
DEFAULT_MIN_COVERAGE = Decimal("0.95")


class BrokerProfileError(ValueError):
    """Invalid calendar, timestamp, or observation input."""


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise BrokerProfileError("invalid_as_of_timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BrokerProfileError("as_of_timestamp_must_be_timezone_aware")
    return parsed


def _decimal(value: Any, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise BrokerProfileError(f"invalid_{field}") from None
    if not parsed.is_finite() or parsed < 0:
        raise BrokerProfileError(f"invalid_{field}")
    return parsed


def build_rolling_broker_profiles(
    observations: list[dict], *,
    verified_exchange_sessions: Iterable[str],
    complete_source_sessions: Iterable[str],
    as_of_date: str,
    as_of_timestamp: str,
    windows: dict[str, int] | None = None,
    min_coverage: Decimal = DEFAULT_MIN_COVERAGE,
) -> dict:
    """Build weekly/monthly/yearly profiles from a point-in-time daily ledger.

    verified_exchange_sessions is the independently validated NEPSE calendar.
    complete_source_sessions must come from P4.36 manifests whose source totals,
    identity coverage and session verification all passed.
    """
    try:
        cutoff = date.fromisoformat(as_of_date)
    except (TypeError, ValueError):
        raise BrokerProfileError("as_of_date_must_be_iso") from None
    available_cutoff = _timestamp(as_of_timestamp)
    try:
        threshold = Decimal(str(min_coverage))
    except (InvalidOperation, TypeError, ValueError):
        raise BrokerProfileError("invalid_min_coverage") from None
    if not threshold.is_finite() or not (Decimal("0") < threshold <= Decimal("1")):
        raise BrokerProfileError("invalid_min_coverage")
    policy = DEFAULT_WINDOWS if windows is None else windows
    if not isinstance(policy, dict) or not policy:
        raise BrokerProfileError("windows_must_be_nonempty")
    for name, count in policy.items():
        if not isinstance(name, str) or not name.strip() or isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise BrokerProfileError("window_counts_must_be_positive_integers")

    def normalize_calendar(values: Iterable[str], label: str) -> list[date]:
        parsed = []
        for value in values:
            try:
                item = date.fromisoformat(value)
            except (TypeError, ValueError):
                raise BrokerProfileError(f"invalid_{label}_date") from None
            if item <= cutoff:
                parsed.append(item)
        if len(parsed) != len(set(parsed)):
            raise BrokerProfileError(f"duplicate_{label}_date")
        return sorted(parsed)

    calendar = normalize_calendar(verified_exchange_sessions, "verified_session")
    complete = set(normalize_calendar(complete_source_sessions, "complete_source_session"))
    if not complete.issubset(set(calendar)):
        raise BrokerProfileError("complete_source_session_not_in_verified_exchange_calendar")

    admitted = []
    excluded = []
    required = ("security_id", "broker_id", "session_date", "side", "amount", "quantity",
                "source_id", "evidence_id", "source_payload_sha256", "available_at",
                "status", "coverage_ratio")
    for index, row in enumerate(observations):
        if not isinstance(row, dict) or any(key not in row for key in required):
            excluded.append({"row": index, "reason": "missing_fields_or_not_object"})
            continue
        try:
            session = date.fromisoformat(row["session_date"])
            row_available = _timestamp(row["available_at"])
            amount = _decimal(row["amount"], "amount")
            quantity = _decimal(row["quantity"], "quantity")
            coverage = Decimal(str(row["coverage_ratio"]))
        except (TypeError, ValueError, InvalidOperation, BrokerProfileError):
            excluded.append({"row": index, "reason": "invalid_date_timestamp_or_numeric"})
            continue
        if session > cutoff or row_available > available_cutoff:
            excluded.append({"row": index, "reason": "not_available_as_of_cutoff"})
            continue
        if row["status"] != "descriptive_only":
            excluded.append({"row": index, "reason": "not_descriptive_only"})
            continue
        if row["side"] not in {"BUY", "SELL"}:
            excluded.append({"row": index, "reason": "invalid_side"})
            continue
        if not isinstance(row["security_id"], str) or not row["security_id"].strip() or not isinstance(row["broker_id"], str) or not row["broker_id"].strip():
            excluded.append({"row": index, "reason": "unverified_identity_fields"})
            continue
        if session not in complete:
            excluded.append({"row": index, "reason": "session_source_not_complete"})
            continue
        if not coverage.is_finite() or coverage < threshold or coverage > 1:
            excluded.append({"row": index, "reason": "insufficient_row_coverage"})
            continue
        admitted.append({
            "security_id": row["security_id"], "broker_id": row["broker_id"],
            "session_date": session, "side": row["side"],
            "amount": amount, "quantity": quantity,
            "source_id": row["source_id"], "evidence_id": row["evidence_id"],
            "source_payload_sha256": row["source_payload_sha256"],
        })

    pairs = sorted({(row["security_id"], row["broker_id"]) for row in admitted})
    # Group all verified activity to calculate security-level participation.
    security_daily_gross: dict[tuple[str, date], Decimal] = {}
    pair_daily: dict[tuple[str, str, date], dict[str, Decimal]] = {}
    lineage_seen = set()
    for row in admitted:
        lineage = (row["security_id"], row["broker_id"], row["session_date"],
                   row["side"], row["source_id"], row["evidence_id"])
        if lineage in lineage_seen:
            raise BrokerProfileError("duplicate_daily_observation_natural_key")
        lineage_seen.add(lineage)
        pair_key = (row["security_id"], row["broker_id"], row["session_date"])
        totals = pair_daily.setdefault(pair_key, {
            "buy_amount": Decimal("0"), "sell_amount": Decimal("0"),
            "buy_quantity": Decimal("0"), "sell_quantity": Decimal("0"),
        })
        side = row["side"].lower()
        totals[f"{side}_amount"] += row["amount"]
        totals[f"{side}_quantity"] += row["quantity"]
        sec_key = (row["security_id"], row["session_date"])
        security_daily_gross[sec_key] = security_daily_gross.get(sec_key, Decimal("0")) + row["amount"]

    profiles = []
    for security_id, broker_id in pairs:
        for window_name, requested in policy.items():
            expected_sessions = calendar[-requested:]
            if not expected_sessions:
                continue
            covered_sessions = [day for day in expected_sessions if day in complete]
            coverage_ratio = Decimal(len(covered_sessions)) / Decimal(len(expected_sessions))
            minimum_sessions = ceil(Decimal(len(expected_sessions)) * threshold)
            enough = len(expected_sessions) == requested and len(covered_sessions) >= minimum_sessions
            # Include zero activity only for covered sessions. The denominator is
            # complete source sessions, never merely days on which this broker traded.
            daily = []
            for day in covered_sessions:
                totals = pair_daily.get((security_id, broker_id, day), {
                    "buy_amount": Decimal("0"), "sell_amount": Decimal("0"),
                    "buy_quantity": Decimal("0"), "sell_quantity": Decimal("0"),
                })
                buy = totals["buy_amount"]
                sell = totals["sell_amount"]
                gross = buy + sell
                net = buy - sell
                security_gross = security_daily_gross.get((security_id, day), Decimal("0"))
                daily.append({
                    "session_date": day.isoformat(), "buy_amount": str(buy),
                    "sell_amount": str(sell), "net_amount": str(net),
                    "gross_amount": str(gross),
                    "broker_participation": str(gross / security_gross) if security_gross else None,
                })
            buy_amount = sum((Decimal(x["buy_amount"]) for x in daily), Decimal("0"))
            sell_amount = sum((Decimal(x["sell_amount"]) for x in daily), Decimal("0"))
            buy_quantity = sum((pair_daily.get((security_id, broker_id, day), {}).get(
                "buy_quantity", Decimal("0")) for day in covered_sessions), Decimal("0"))
            sell_quantity = sum((pair_daily.get((security_id, broker_id, day), {}).get(
                "sell_quantity", Decimal("0")) for day in covered_sessions), Decimal("0"))
            net_amount = buy_amount - sell_amount
            gross_amount = buy_amount + sell_amount
            active_sessions = sum(1 for x in daily if Decimal(x["gross_amount"]) > 0)
            positive_sessions = sum(1 for x in daily if Decimal(x["net_amount"]) > 0)
            negative_sessions = sum(1 for x in daily if Decimal(x["net_amount"]) < 0)
            zero_sessions = len(daily) - active_sessions
            shares = [Decimal(x["broker_participation"]) for x in daily if x["broker_participation"] is not None]
            if not enough:
                label = "insufficient_evidence"
            elif net_amount > 0:
                label = "net_buy_dominant"
            elif net_amount < 0:
                label = "net_sell_dominant"
            else:
                label = "balanced_or_no_activity"
            profiles.append({
                "security_id": security_id, "broker_id": broker_id,
                "window": window_name, "requested_sessions": requested,
                "expected_sessions": len(expected_sessions),
                "complete_source_sessions": len(covered_sessions),
                "coverage_ratio": str(coverage_ratio),
                "status": "descriptive_only" if enough else "insufficient_evidence",
                "directional_summary": label,
                "buy_amount": str(buy_amount), "sell_amount": str(sell_amount),
                "net_amount": str(net_amount), "gross_amount": str(gross_amount),
                "buy_quantity": str(buy_quantity), "sell_quantity": str(sell_quantity),
                "net_quantity": str(buy_quantity - sell_quantity),
                "active_sessions": active_sessions,
                "positive_net_sessions": positive_sessions,
                "negative_net_sessions": negative_sessions,
                "zero_activity_sessions": zero_sessions,
                "positive_net_session_ratio": str(Decimal(positive_sessions) / Decimal(len(daily))) if daily else None,
                "negative_net_session_ratio": str(Decimal(negative_sessions) / Decimal(len(daily))) if daily else None,
                "broker_participation_ratio": str(gross_amount / sum(
                    (security_daily_gross.get((security_id, day), Decimal("0")) for day in covered_sessions),
                    Decimal("0"))) if sum((security_daily_gross.get((security_id, day), Decimal("0"))
                        for day in covered_sessions), Decimal("0")) else None,
                "mean_daily_broker_participation": str(sum(shares, Decimal("0")) / Decimal(len(shares))) if shares else None,
                "daily": daily,
                "interpretation": (
                    "Withheld: complete verified exchange-session coverage is insufficient."
                    if not enough else
                    "Descriptive broker-side transaction flow only; not beneficial ownership, accumulation, distribution, operator intent or a trade signal."
                ),
            })

    return {
        "as_of_date": cutoff.isoformat(),
        "as_of_timestamp": available_cutoff.isoformat(),
        "window_policy": dict(policy), "minimum_coverage": str(threshold),
        "verified_exchange_sessions": len(calendar),
        "complete_source_sessions": len(complete),
        "admitted_observation_rows": len(admitted),
        "excluded_observation_rows": len(excluded),
        "exclusions": excluded, "profiles": profiles,
        "policy": "complete_source_sessions_only_no_zero_filling_for_missing_sessions_point_in_time_descriptive_only",
    }
