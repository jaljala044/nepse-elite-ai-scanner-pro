"""Point-in-time broker/security behaviour memory descriptors.

These are descriptive aggregates, not evidence of beneficial ownership or intent.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import re


DEFAULT_WINDOWS = {"daily": 1, "weekly": 5, "monthly": 21, "yearly": 252}


def build_broker_behavior_memory(
    observations: list[dict], *, as_of_date: str,
    windows: dict[str, int] | None = None,
) -> dict:
    """Build as-of broker/security descriptors from verified daily observations.

    Input rows are party-side aggregates. A row is admitted only when identity,
    session, provenance, availability and coverage are explicit and valid.
    Unknown/ineligible rows are counted and excluded, never treated as zero.
    """
    try:
        cutoff = date.fromisoformat(as_of_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("as_of_date must be an ISO date") from exc
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    windows = DEFAULT_WINDOWS if windows is None else windows
    if not isinstance(windows, dict) or not windows:
        raise ValueError("windows must be a non-empty mapping")
    for name, size in windows.items():
        if not isinstance(name, str) or not name.strip() or isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise ValueError("window names and positive integer session counts are required")

    admitted, excluded = [], []
    required_text = ("security_id", "broker_entity_id", "source_id", "evidence_id", "source_payload_sha256")
    for index, row in enumerate(observations):
        reason = None
        if not isinstance(row, dict):
            excluded.append({"row": index, "reason": "not_an_object"})
            continue
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required_text):
            reason = "missing_identity_or_provenance"
        elif row.get("identity_status") != "verified":
            reason = "broker_identity_not_verified"
        elif row.get("session_status") != "verified":
            reason = "session_not_verified"
        elif not re.fullmatch(r"[0-9a-f]{64}", row["source_payload_sha256"].lower()):
            reason = "invalid_payload_hash"
        else:
            try:
                event_date = date.fromisoformat(row["trade_date"])
                available_date = date.fromisoformat(row["available_at"][:10])
                amount = Decimal(str(row["amount"]))
                quantity = Decimal(str(row["quantity"]))
                coverage = Decimal(str(row["coverage_ratio"]))
            except (KeyError, TypeError, ValueError, InvalidOperation):
                reason = "invalid_date_or_numeric_field"
            else:
                if event_date > cutoff:
                    reason = "future_event"
                elif available_date > cutoff:
                    reason = "not_yet_available_as_of"
                elif row.get("side") not in {"buy", "sell"}:
                    reason = "invalid_side"
                elif not amount.is_finite() or not quantity.is_finite() or amount < 0 or quantity < 0:
                    reason = "invalid_amount_or_quantity"
                elif not coverage.is_finite() or coverage < Decimal("0.95") or coverage > 1:
                    reason = "insufficient_coverage"
                elif not isinstance(row.get("source_row_count"), int) or isinstance(row.get("source_row_count"), bool) or row["source_row_count"] < 1:
                    reason = "invalid_source_row_count"
        if reason:
            excluded.append({"row": index, "reason": reason})
        else:
            admitted.append({
                "security_id": row["security_id"], "broker_entity_id": row["broker_entity_id"],
                "trade_date": event_date, "available_at": available_date,
                "side": row["side"], "amount": amount, "quantity": quantity,
                "coverage_ratio": coverage, "source_id": row["source_id"],
                "evidence_id": row["evidence_id"], "source_payload_sha256": row["source_payload_sha256"].lower(),
                "source_row_count": row["source_row_count"],
            })

    groups = defaultdict(list)
    for row in admitted:
        groups[(row["security_id"], row["broker_entity_id"])].append(row)

    memories = []
    for (security_id, broker_id), rows in sorted(groups.items()):
        for window_name, session_count in windows.items():
            # The input must already be constrained to verified exchange sessions;
            # retain the most recent N distinct event dates, not calendar days.
            dates = sorted({r["trade_date"] for r in rows if r["trade_date"] <= cutoff}, reverse=True)[:session_count]
            selected = [r for r in rows if r["trade_date"] in dates]
            if not selected:
                continue
            buy_amount = sum((r["amount"] for r in selected if r["side"] == "buy"), Decimal("0"))
            sell_amount = sum((r["amount"] for r in selected if r["side"] == "sell"), Decimal("0"))
            buy_qty = sum((r["quantity"] for r in selected if r["side"] == "buy"), Decimal("0"))
            sell_qty = sum((r["quantity"] for r in selected if r["side"] == "sell"), Decimal("0"))
            memories.append({
                "security_id": security_id, "broker_entity_id": broker_id,
                "window": window_name, "requested_sessions": session_count,
                "observed_sessions": len(dates), "first_session": min(dates).isoformat(),
                "last_session": max(dates).isoformat(), "as_of_date": cutoff.isoformat(),
                "buy_amount": str(buy_amount), "sell_amount": str(sell_amount),
                "net_amount": str(buy_amount - sell_amount),
                "buy_quantity": str(buy_qty), "sell_quantity": str(sell_qty),
                "net_quantity": str(buy_qty - sell_qty),
                "observation_rows": len(selected),
                "source_ids": sorted({r["source_id"] for r in selected}),
                "evidence_ids": sorted({r["evidence_id"] for r in selected}),
                "payload_hashes": sorted({r["source_payload_sha256"] for r in selected}),
                "max_available_at": max(r["available_at"] for r in selected).isoformat(),
                "coverage_min": str(min(r["coverage_ratio"] for r in selected)),
                "status": "descriptive_only",
                "interpretation": "Net broker flow is not proof of beneficial ownership, accumulation, distribution or intent.",
            })
    return {
        "as_of_date": cutoff.isoformat(), "window_policy": dict(windows),
        "admitted_observation_rows": len(admitted), "excluded_observation_rows": len(excluded),
        "exclusions": excluded, "memory_rows": memories,
        "policy": "point_in_time_verified_identity_and_provenance_descriptive_only_no_intent_inference",
    }
