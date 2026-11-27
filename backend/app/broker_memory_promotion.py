"""Promote only fully reconciled ingestion batches into persistent broker memory."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from app.broker_behavior_memory import build_broker_behavior_memory
from app.broker_ingestion import IngestionReport
from app.quarantine_guard import is_quarantined
from app.broker_memory_store import BrokerMemoryStore

class PromotionRejected(ValueError):
    """A batch did not satisfy the complete promotion gate."""

def promote_validated_batch(report: IngestionReport, store: BrokerMemoryStore, *,
                            as_of_date: str, methodology_version: str = "p4.34-v1") -> dict[str, Any]:
    """Build descriptors and persist them idempotently only after all admission gates pass."""
    if not isinstance(report, IngestionReport) or not report.memory_eligible:
        raise PromotionRejected("batch is not fully validated and memory-eligible")
    if not isinstance(as_of_date, str) or len(as_of_date) != 10:
        raise PromotionRejected("as_of_date must be ISO YYYY-MM-DD")
    observations, availabilities, batch_ids = [], [], set()
    if report.conflicts:
        raise PromotionRejected("batch contains conflicts")
    for row in report.accepted:
        if is_quarantined(row):
            raise PromotionRejected("quarantined accepted row")
        if row.get("status") != "descriptive_only":
            raise PromotionRejected("non-descriptive row in accepted batch")
        available_at = row.get("available_at")
        try:
            parsed = datetime.fromisoformat(available_at.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError):
            raise PromotionRejected("accepted row has invalid availability timestamp") from None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise PromotionRejected("accepted row availability must be timezone-aware")
        availabilities.append(parsed)
        batch_ids.add(row.get("batch_id"))
        observations.append({
            "trade_date": row["session_date"], "available_at": parsed.isoformat(),
            "security_id": row["security_id"], "broker_entity_id": row["broker_id"],
            "identity_status": "verified", "session_status": "verified",
            "side": row["side"].lower(), "amount": row["amount"], "quantity": row["quantity"],
            "coverage_ratio": row["coverage_ratio"], "source_row_count": row["source_row_count"],
            "source_id": row["source_id"], "evidence_id": row["evidence_id"],
            "source_payload_sha256": row["source_payload_sha256"],
        })
    if len(batch_ids) != 1 or None in batch_ids:
        raise PromotionRejected("accepted rows must belong to exactly one identified batch")
    if any(x.date().isoformat() > as_of_date for x in availabilities):
        raise PromotionRejected("batch contains records unavailable at requested as-of date")
    built = build_broker_behavior_memory(observations, as_of_date=as_of_date)
    if built["excluded_observation_rows"] or not built["memory_rows"]:
        raise PromotionRejected("observation builder excluded rows or produced no descriptors")

    complete, withheld = [], []
    for snap in built["memory_rows"]:
        if snap["observed_sessions"] != snap["requested_sessions"]:
            withheld.append({"security_id": snap["security_id"],
                "broker_entity_id": snap["broker_entity_id"], "window": snap["window"],
                "observed_sessions": snap["observed_sessions"],
                "required_sessions": snap["requested_sessions"],
                "reason": "insufficient_distinct_observation_sessions"})
            continue
        snap["source_batch_ids"] = sorted(batch_ids)
        snap["source_coverage_status"] = report.coverage_status
        snap["source_coverage_ratio"] = report.coverage_ratio
        snap["status"] = "descriptive_only"
        complete.append(snap)
    if not complete:
        raise PromotionRejected("no window has sufficient distinct observation sessions")
    batch_id = next(iter(batch_ids))
    persisted = store.append_many_atomic(
        complete, key_prefix=f"p4.34:{batch_id}:{as_of_date}",
        methodology_version=methodology_version, available_at=max(availabilities))
    return {"batch_id": batch_id, "as_of_date": as_of_date,
        "coverage_status": report.coverage_status, "coverage_ratio": report.coverage_ratio,
        "observation_rows": len(observations), "promoted_snapshots": len(complete),
        "withheld_windows": withheld, "persistence": persisted,
        "interpretation": "descriptive_only_no_ownership_or_intent_inference"}
