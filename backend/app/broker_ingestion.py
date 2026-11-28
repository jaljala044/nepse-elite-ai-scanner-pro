"""Fail-closed reconciliation of externally acquired broker aggregates.

This module does not fetch data. Callers must provide source extracts and independently
verified broker/session registries. Only complete, reconciled batches are memory-eligible.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

COVERAGE_THRESHOLD = Decimal("0.95")
SIDES = {"BUY", "SELL"}

class IngestionError(ValueError):
    """Invalid batch-level input."""

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)

def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise IngestionError(f"invalid_{field_name}") from None
    if not result.is_finite() or result < 0:
        raise IngestionError(f"invalid_{field_name}")
    return result


def _canonical_session_date(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise IngestionError(f"invalid_{field_name}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise IngestionError(f"invalid_{field_name}") from None
    if parsed.isoformat() != value:
        raise IngestionError(f"noncanonical_{field_name}")
    return value

def payload_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _approved_rights(source_id: str, evidence: Any, available_by: datetime) -> tuple[bool, str | None]:
    """Require dated, pre-available evidence covering storage and aggregation."""
    if not isinstance(evidence, Mapping):
        return False, "missing_source_rights_evidence"
    required = ("source_id", "evidence_id", "status", "document_sha256",
                "effective_from", "available_at")
    if any(not isinstance(evidence.get(key), str) or not evidence[key].strip()
           for key in required):
        return False, "incomplete_source_rights_evidence"
    if evidence["source_id"] != source_id or evidence["status"] != "approved":
        return False, "source_rights_not_approved"
    if not re.fullmatch(r"[0-9a-f]{64}", evidence["document_sha256"]):
        return False, "invalid_source_rights_document_hash"
    scope = evidence.get("scope")
    if (not isinstance(scope, (list, tuple, set, frozenset)) or
            not {"electronic_storage", "aggregation"}.issubset(set(scope))):
        return False, "source_rights_scope_insufficient"
    try:
        start = _canonical_session_date(evidence["effective_from"], "rights_effective_from")
        end = evidence.get("effective_to")
        if end is not None:
            end = _canonical_session_date(end, "rights_effective_to")
            if end < start:
                return False, "invalid_source_rights_effective_range"
        captured = datetime.fromisoformat(evidence["available_at"].replace("Z", "+00:00"))
        if captured.tzinfo is None or captured.utcoffset() is None:
            return False, "source_rights_timestamp_not_timezone_aware"
        if captured > available_by:
            return False, "source_rights_evidence_not_yet_available"
    except (IngestionError, TypeError, ValueError):
        return False, "invalid_source_rights_evidence"
    return True, None

@dataclass(frozen=True)
class ContractTotal:
    security_id: str
    broker_id: str
    session_date: str
    side: str
    quantity: Decimal
    amount: Decimal

@dataclass
class IngestionReport:
    batch_id: str
    coverage_status: str
    coverage_ratio: str | None
    accepted: list[dict[str, Any]] = field(default_factory=list)
    quarantined: list[dict[str, Any]] = field(default_factory=list)
    duplicates_skipped: int = 0
    conflicts: int = 0
    reconciliation: list[dict[str, Any]] = field(default_factory=list)

    @property
    def memory_eligible(self) -> bool:
        return self.coverage_status == "complete" and not self.quarantined and bool(self.accepted)

def reconcile_broker_batch(
    *, batch_id: str, rows: Iterable[Mapping[str, Any]], verified_brokers: set[str],
    verified_sessions: set[str], expected_source_ids: set[str] | None,
    received_source_ids: set[str], available_at: str,
    verified_session_finality: Mapping[str, str] | None = None,
    source_rights_evidence: Mapping[str, Mapping[str, Any]] | None = None,
    contracts: Iterable[ContractTotal] | None = None,
    seen_natural_keys: Mapping[str, str] | None = None,
    coverage_threshold: Decimal = COVERAGE_THRESHOLD,
) -> IngestionReport:
    """Validate a batch; availability must be timezone-aware ISO-8601.

    Exact natural-key replays are skipped; changed payloads are quarantined.
    Contract totals, when supplied, must match exactly by security/broker/session/side.
    Missing inventory or empty extracts are UNKNOWN, never zero flow.
    """
    try:
        availability = datetime.fromisoformat(available_at.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        raise IngestionError("invalid_available_at") from None
    if availability.tzinfo is None or availability.utcoffset() is None:
        raise IngestionError("available_at_must_be_timezone_aware")

    if not isinstance(batch_id, str) or not batch_id.strip():
        raise IngestionError("batch_id_must_be_nonblank")
    try:
        threshold = Decimal(str(coverage_threshold))
    except (InvalidOperation, TypeError, ValueError):
        raise IngestionError("invalid_coverage_threshold") from None
    if not threshold.is_finite() or not (Decimal("0") < threshold <= Decimal("1")):
        raise IngestionError("invalid_coverage_threshold")

    if not isinstance(verified_sessions, (set, frozenset)):
        raise IngestionError("invalid_verified_session_inventory")
    try:
        for item in verified_sessions:
            _canonical_session_date(item, "verified_session")
    except IngestionError:
        raise IngestionError("invalid_verified_session_inventory") from None

    expected = set(expected_source_ids or set())
    received = set(received_source_ids or set())
    if any(not isinstance(item, str) or not item.strip() for item in expected | received):
        raise IngestionError("invalid_source_inventory")
    if not expected or not received:
        coverage_status, ratio = "unknown", None
    else:
        ratio_decimal = Decimal(len(expected & received)) / Decimal(len(expected))
        ratio = str(ratio_decimal)
        coverage_status = "complete" if ratio_decimal >= threshold else "partial"

    report = IngestionReport(batch_id, coverage_status, ratio)
    rights = source_rights_evidence if isinstance(source_rights_evidence, Mapping) else {}
    approved_rights = set()
    for source_id in sorted(expected):
        valid, reason = _approved_rights(source_id, rights.get(source_id), availability)
        if valid:
            approved_rights.add(source_id)
        else:
            report.quarantined.append({
                "batch_id": batch_id,
                "reasons": [f"source_rights_unverified:{source_id}:{reason}"],
            })

    prior = dict(seen_natural_keys or {})
    staged: list[dict[str, Any]] = []
    batch_keys: dict[str, str] = {}

    for index, source_row in enumerate(rows):
        raw = dict(source_row)
        required = ("security_id", "broker_id", "session_date", "side", "quantity", "amount",
                    "source_id", "evidence_id", "source_payload", "source_payload_sha256",
                    "source_row_count", "coverage_ratio")
        missing = [key for key in required if key not in raw]
        reasons: list[str] = []
        if missing:
            reasons.append("missing_fields:" + ",".join(missing))
        if reasons:
            report.quarantined.append({"row_index": index, "raw": raw, "reasons": reasons})
            continue

        try:
            session_text = _canonical_session_date(raw["session_date"], "session_date")
            session = date.fromisoformat(session_text)
        except IngestionError:
            session_text = None
            session = None
        for identity_field in ("security_id", "broker_id", "source_id", "evidence_id"):
            if not isinstance(raw[identity_field], str) or not raw[identity_field].strip():
                reasons.append("blank_required_identity:" + identity_field)
        if session is None or session_text not in verified_sessions:
            reasons.append("unverified_or_invalid_session")
        if str(raw["broker_id"]) not in verified_brokers:
            reasons.append("unverified_broker_identity")
        if str(raw["source_id"]) not in expected or str(raw["source_id"]) not in received:
            reasons.append("source_not_in_verified_inventory")
        elif str(raw["source_id"]) not in approved_rights:
            reasons.append("source_rights_not_approved")
        else:
            rights_item = rights[str(raw["source_id"])]
            try:
                session_day = date.fromisoformat(session_text)
                rights_start = date.fromisoformat(rights_item["effective_from"])
                rights_end = date.fromisoformat(rights_item["effective_to"]) if rights_item.get("effective_to") else None
                if session_day < rights_start or (rights_end is not None and session_day > rights_end):
                    reasons.append("source_rights_not_effective_for_session")
            except (TypeError, ValueError):
                reasons.append("invalid_source_rights_effective_range")
        side = str(raw["side"]).upper()
        if side not in SIDES:
            reasons.append("invalid_side")
        try:
            quantity = _decimal(raw["quantity"], "quantity")
            amount = _decimal(raw["amount"], "amount")
            row_count = int(raw["source_row_count"])
            row_coverage = Decimal(str(raw["coverage_ratio"]))
            if row_count <= 0 or not row_coverage.is_finite() or not (0 <= row_coverage <= 1):
                raise IngestionError("invalid_source_coverage_metadata")
        except (IngestionError, InvalidOperation, TypeError, ValueError) as exc:
            reasons.append(str(exc) or "invalid_numeric_metadata")
            quantity, amount, row_count, row_coverage = Decimal(0), Decimal(0), 0, Decimal(0)

        payload = raw.get("source_payload")
        if not isinstance(payload, Mapping):
            reasons.append("missing_source_payload")
        elif str(raw["source_payload_sha256"]).lower() != payload_hash(payload):
            reasons.append("source_payload_hash_mismatch")
        finality_raw = (verified_session_finality or {}).get(str(raw["session_date"]))
        if finality_raw is None:
            reasons.append("missing_verified_session_finality")
        else:
            try:
                finality = datetime.fromisoformat(str(finality_raw).replace("Z", "+00:00"))
                if finality.tzinfo is None or finality.utcoffset() is None:
                    raise ValueError("finality_timestamp_must_be_timezone_aware")
                if availability < finality:
                    reasons.append("available_before_session_finality")
            except (TypeError, ValueError):
                reasons.append("invalid_verified_session_finality")

        if reasons:
            report.quarantined.append({"row_index": index, "raw": raw, "reasons": reasons})
            continue

        natural_key = "|".join((str(raw["security_id"]), str(raw["broker_id"]),
                                str(raw["session_date"]), side, str(raw["source_id"]),
                                str(raw["evidence_id"])))
        digest = str(raw["source_payload_sha256"]).lower()
        if natural_key in prior or natural_key in batch_keys:
            old_digest = prior.get(natural_key, batch_keys.get(natural_key))
            if old_digest == digest:
                report.duplicates_skipped += 1
                continue
            report.conflicts += 1
            report.quarantined.append({"row_index": index, "raw": raw,
                                       "reasons": ["conflicting_duplicate_payload"]})
            continue
        batch_keys[natural_key] = digest
        staged.append({
            "security_id": str(raw["security_id"]), "broker_id": str(raw["broker_id"]),
            "session_date": str(raw["session_date"]), "side": side,
            "quantity": str(quantity), "amount": str(amount), "source_id": str(raw["source_id"]),
            "evidence_id": str(raw["evidence_id"]), "source_payload_sha256": digest,
            "source_row_count": row_count, "coverage_ratio": str(row_coverage),
            "raw_record_lineage": raw.get("raw_record_lineage", []),
            "available_at": availability.isoformat(), "batch_id": batch_id,
            "status": "descriptive_only",
        })

    if contracts is not None:
        expected_totals: dict[tuple[str, str, str, str], tuple[Decimal, Decimal]] = {}
        for c in contracts:
            key = (c.security_id, c.broker_id, c.session_date, c.side.upper())
            q, a = expected_totals.get(key, (Decimal(0), Decimal(0)))
            expected_totals[key] = (q + c.quantity, a + c.amount)
        actual_totals: dict[tuple[str, str, str, str], tuple[Decimal, Decimal]] = {}
        for item in staged:
            key = (item["security_id"], item["broker_id"], item["session_date"], item["side"])
            q, a = actual_totals.get(key, (Decimal(0), Decimal(0)))
            actual_totals[key] = (q + Decimal(item["quantity"]), a + Decimal(item["amount"]))
        for key in sorted(set(expected_totals) | set(actual_totals)):
            expected_value = expected_totals.get(key, (Decimal(0), Decimal(0)))
            actual_value = actual_totals.get(key, (Decimal(0), Decimal(0)))
            matched = expected_value == actual_value
            report.reconciliation.append({
                "key": key, "expected_quantity": str(expected_value[0]),
                "actual_quantity": str(actual_value[0]), "expected_amount": str(expected_value[1]),
                "actual_amount": str(actual_value[1]), "matched": matched,
            })
            if not matched:
                report.quarantined.append({"key": key, "reasons": ["contract_reconciliation_mismatch"]})

    if coverage_status != "complete":
        report.quarantined.append({"batch_id": batch_id, "reasons": ["source_coverage_" + coverage_status]})
    report.accepted = [] if report.quarantined else staged
    return report
