"""Fail-closed promotion boundary for validated broker-ingestion batches.

This module deliberately does not fetch data, infer broker intent, or emit trades.
The caller must supply a P4.33 reconciliation result and a transactional store
adapter. The adapter owns durable atomicity and idempotency enforcement.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Protocol, Sequence


class PromotionStatus(str, Enum):
    PROMOTED = "PROMOTED"
    REPLAYED = "REPLAYED"
    BLOCKED = "BLOCKED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class ReconciliationEvidence:
    batch_id: str
    source_payload_sha256: str
    session_date: str
    available_at: str
    coverage_status: str
    accepted_row_count: int
    quarantined_row_count: int
    validation_passed: bool
    source_rights_cleared: bool
    session_verified: bool
    point_in_time_valid: bool
    source_manifest_sha256: str


@dataclass(frozen=True)
class PromotionReceipt:
    status: PromotionStatus
    batch_id: str
    payload_sha256: str
    snapshot_count: int
    reason_codes: tuple[str, ...]


class AppendOnlyBrokerMemoryStore(Protocol):
    """Transactional adapter contract; implementations must commit atomically."""

    def append_batch(
        self,
        *,
        idempotency_key: str,
        payload_sha256: str,
        session_date: str,
        available_at: str,
        records: Sequence[dict],
    ) -> str:
        """Return 'APPENDED', 'REPLAYED', or 'CONFLICT'.

        A repeated key with the same digest is a no-op. The same key with a
        different digest must return CONFLICT. Partial writes are forbidden.
        """
        ...


def _canonical_digest(records: Sequence[dict]) -> str:
    payload = json.dumps(
        list(records), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def promote_reconciled_batch(
    evidence: ReconciliationEvidence,
    records: Sequence[dict],
    store: AppendOnlyBrokerMemoryStore,
) -> PromotionReceipt:
    """Promote only a fully reconciled, rights-cleared, point-in-time batch."""
    reasons: list[str] = []
    if not evidence.batch_id.strip():
        reasons.append("MISSING_BATCH_ID")
    if len(evidence.source_payload_sha256) != 64:
        reasons.append("INVALID_SOURCE_PAYLOAD_DIGEST")
    if len(evidence.source_manifest_sha256) != 64:
        reasons.append("INVALID_SOURCE_MANIFEST_DIGEST")
    if evidence.coverage_status != "COMPLETE":
        reasons.append("COVERAGE_NOT_COMPLETE")
    if evidence.accepted_row_count != len(records) or not records:
        reasons.append("ROW_COUNT_MISMATCH_OR_EMPTY_BATCH")
    if evidence.quarantined_row_count != 0:
        reasons.append("QUARANTINE_PRESENT")
    if not evidence.validation_passed:
        reasons.append("RECONCILIATION_NOT_PASSED")
    if not evidence.source_rights_cleared:
        reasons.append("SOURCE_RIGHTS_NOT_CLEARED")
    if not evidence.session_verified:
        reasons.append("SESSION_NOT_VERIFIED")
    if not evidence.point_in_time_valid:
        reasons.append("POINT_IN_TIME_GATE_FAILED")
    if not evidence.session_date or not evidence.available_at:
        reasons.append("MISSING_AS_OF_METADATA")

    digest = _canonical_digest(records)
    if reasons:
        return PromotionReceipt(
            PromotionStatus.BLOCKED, evidence.batch_id, digest, 0, tuple(reasons)
        )

    # The storage adapter must make this operation atomic and enforce key/digest
    # uniqueness. No in-memory success is reported before it returns.
    result = store.append_batch(
        idempotency_key=evidence.batch_id,
        payload_sha256=digest,
        session_date=evidence.session_date,
        available_at=evidence.available_at,
        records=records,
    )
    if result == "APPENDED":
        status = PromotionStatus.PROMOTED
    elif result == "REPLAYED":
        status = PromotionStatus.REPLAYED
    elif result == "CONFLICT":
        status = PromotionStatus.CONFLICT
    else:
        raise RuntimeError("Store adapter returned an unsupported result")

    return PromotionReceipt(status, evidence.batch_id, digest,
                            len(records) if status == PromotionStatus.PROMOTED else 0,
                            ())
