"""Fail-closed bridge from reconciled broker extracts to persistent memory."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping

from app.broker_behavior_memory import build_broker_behavior_memory
from app.broker_ingestion import ContractTotal, reconcile_broker_batch
from app.broker_memory_store import BrokerMemoryStore


def ingest_and_persist_broker_batch(
    *,
    store: BrokerMemoryStore,
    batch_id: str,
    rows: Iterable[Mapping[str, Any]],
    verified_brokers: set[str],
    verified_sessions: set[str],
    verified_session_finality: Mapping[str, str],
    expected_source_ids: set[str] | None,
    received_source_ids: set[str],
    available_at: str,
    as_of_date: str,
    available_by: datetime | str,
    contracts: Iterable[ContractTotal] | None = None,
    seen_natural_keys: Mapping[str, str] | None = None,
    coverage_threshold: Any = "0.95",
    methodology_version: str = "p4.34-v1",
) -> dict[str, Any]:
    """Reconcile first, derive all windows, then persist the complete memory batch.

    No writes occur for an ineligible ingestion batch or if any accepted observation
    fails the memory admission stage. Persistence uses the store's single-transaction
    append_many operation, so a conflicting idempotency key rolls back the whole batch.
    """
    ingestion = reconcile_broker_batch(
        batch_id=batch_id,
        rows=rows,
        verified_brokers=verified_brokers,
        verified_sessions=verified_sessions,
        verified_session_finality=verified_session_finality,
        expected_source_ids=expected_source_ids,
        received_source_ids=received_source_ids,
        available_at=available_at,
        contracts=contracts,
        seen_natural_keys=seen_natural_keys,
        coverage_threshold=coverage_threshold,
    )
    base = {
        "batch_id": batch_id,
        "ingestion_eligible": ingestion.memory_eligible,
        "ingestion_accepted_rows": len(ingestion.accepted),
        "ingestion_quarantined_rows": len(ingestion.quarantined),
        "duplicates_skipped": ingestion.duplicates_skipped,
        "coverage_status": ingestion.coverage_status,
        "production_eligible": False,
    }
    if not ingestion.memory_eligible:
        return {**base, "status": "ingestion_rejected", "memory": None, "persistence": None}

    observations = [{
        "security_id": item["security_id"],
        "broker_entity_id": item["broker_id"],
        "identity_status": "verified",
        "session_status": "verified",
        "trade_date": item["session_date"],
        "available_at": item["available_at"],
        "side": item["side"].lower(),
        "amount": item["amount"],
        "quantity": item["quantity"],
        "coverage_ratio": item["coverage_ratio"],
        "source_row_count": item["source_row_count"],
        "source_id": item["source_id"],
        "evidence_id": item["evidence_id"],
        "source_payload_sha256": item["source_payload_sha256"],
    } for item in ingestion.accepted]

    memory = build_broker_behavior_memory(
        observations,
        as_of_date=as_of_date,
        available_by=available_by,
    )
    if memory["excluded_observation_rows"] or memory["admitted_observation_rows"] != len(observations) or not memory["memory_rows"]:
        return {
            **base,
            "status": "memory_admission_rejected",
            "memory": memory,
            "persistence": None,
        }

    available_cutoff = available_by
    if isinstance(available_cutoff, str):
        available_cutoff = datetime.fromisoformat(available_cutoff.replace("Z", "+00:00"))
    persistence = store.append_many(
        memory["memory_rows"],
        key_prefix=batch_id,
        methodology_version=methodology_version,
        available_at=available_cutoff,
    )
    return {
        **base,
        "status": "persisted",
        "memory_rows": len(memory["memory_rows"]),
        "memory": memory,
        "persistence": persistence,
    }
