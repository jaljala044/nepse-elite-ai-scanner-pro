"""Immutable raw-capture staging and explicit admission gate for P4.33.

This module does not fetch data or parse floorsheets. It preserves supplied bytes,
validates provenance metadata, and records a fail-closed operator workflow.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from contextlib import contextmanager
from typing import Any, Iterator, Mapping

from app.broker_ingestion import IngestionReport


class CaptureRejected(ValueError):
    """Raw capture or admission transition failed its evidence gate."""


class CaptureConflict(ValueError):
    """A capture identity was reused with changed immutable evidence."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _aware(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise CaptureRejected(f"invalid_{field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise CaptureRejected(f"invalid_{field}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CaptureRejected(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)



@dataclass(frozen=True)
class SourceRightsEvidence:
    """Reviewable source-terms attestation; not a publisher signature."""
    source_id: str
    evidence_id: str
    decision: str
    terms_url: str
    terms_sha256: str
    retrieved_at: str
    permitted_uses: tuple[str, ...]
    reviewer_id: str
    expires_at: str | None = None

    def validate(self, *, manifest_source_id: str, manifest_evidence_id: str,
                 captured_at: datetime) -> dict[str, Any]:
        if self.source_id != manifest_source_id:
            raise CaptureRejected("rights_evidence_source_mismatch")
        if self.evidence_id != manifest_evidence_id:
            raise CaptureRejected("rights_evidence_id_mismatch")
        if self.decision not in {"cleared", "denied", "unknown"}:
            raise CaptureRejected("invalid_rights_evidence_decision")
        if not isinstance(self.terms_url, str) or not self.terms_url.startswith("https://"):
            raise CaptureRejected("rights_terms_url_must_be_https")
        digest = self.terms_sha256
        if (not isinstance(digest, str) or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest.lower())):
            raise CaptureRejected("invalid_rights_terms_sha256")
        retrieved = _aware(self.retrieved_at, "rights_retrieved_at")
        if retrieved > captured_at:
            raise CaptureRejected("rights_evidence_retrieved_after_capture")
        if not isinstance(self.reviewer_id, str) or not self.reviewer_id.strip():
            raise CaptureRejected("rights_reviewer_required")
        if not isinstance(self.permitted_uses, (tuple, list)) or not all(
                isinstance(item, str) and item.strip() for item in self.permitted_uses):
            raise CaptureRejected("invalid_rights_permitted_uses")
        expires = None
        if self.expires_at is not None:
            expires = _aware(self.expires_at, "rights_expires_at")
            if expires <= retrieved:
                raise CaptureRejected("invalid_rights_expiry")
            if captured_at > expires:
                raise CaptureRejected("rights_evidence_expired_at_capture")
        if self.decision == "cleared" and "broker_aggregation" not in self.permitted_uses:
            raise CaptureRejected("broker_aggregation_not_permitted")
        return {
            "source_id": self.source_id, "evidence_id": self.evidence_id,
            "decision": self.decision, "terms_url": self.terms_url,
            "terms_sha256": digest.lower(), "retrieved_at": retrieved.isoformat(),
            "permitted_uses": sorted(set(self.permitted_uses)),
            "reviewer_id": self.reviewer_id.strip(),
            "expires_at": expires.isoformat() if expires else None,
        }


@dataclass(frozen=True)
class RawCaptureManifest:
    """Versioned evidence describing one immutable source capture."""

    manifest_version: int
    trade_date: str
    source_id: str
    capture_id: str
    captured_at: str
    available_at: str
    source_rights_status: str
    source_rights_evidence_id: str
    source_rights_evidence: SourceRightsEvidence | None
    raw_sha256: str
    raw_byte_count: int
    parser_name: str
    parser_version: str
    session_complete: bool

    def validate(self, raw_bytes: bytes) -> dict[str, Any]:
        if self.manifest_version != 1:
            raise CaptureRejected("unsupported_manifest_version")
        try:
            date.fromisoformat(self.trade_date)
        except (TypeError, ValueError):
            raise CaptureRejected("invalid_trade_date") from None
        for field in ("source_id", "capture_id", "source_rights_evidence_id",
                      "parser_name", "parser_version"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise CaptureRejected("missing_" + field)
        captured = _aware(self.captured_at, "captured_at")
        available = _aware(self.available_at, "available_at")
        if available < captured:
            raise CaptureRejected("available_before_capture")
        if not isinstance(raw_bytes, bytes) or not raw_bytes:
            raise CaptureRejected("empty_or_invalid_raw_capture")
        if isinstance(self.raw_byte_count, bool) or self.raw_byte_count != len(raw_bytes):
            raise CaptureRejected("raw_byte_count_mismatch")
        digest = _sha256(raw_bytes)
        if self.raw_sha256 != digest:
            raise CaptureRejected("raw_sha256_mismatch")
        if not isinstance(self.session_complete, bool):
            raise CaptureRejected("invalid_session_completeness")
        if self.source_rights_status not in {"cleared", "denied", "unknown"}:
            raise CaptureRejected("invalid_source_rights_status")
        if not isinstance(self.source_rights_evidence, SourceRightsEvidence):
            raise CaptureRejected("structured_source_rights_evidence_required")
        rights = self.source_rights_evidence.validate(
            manifest_source_id=self.source_id,
            manifest_evidence_id=self.source_rights_evidence_id,
            captured_at=captured,
        )
        if rights["decision"] != self.source_rights_status:
            raise CaptureRejected("rights_decision_manifest_mismatch")
        return {
            "manifest_version": self.manifest_version,
            "trade_date": self.trade_date, "source_id": self.source_id,
            "capture_id": self.capture_id, "captured_at": captured.isoformat(),
            "available_at": available.isoformat(),
            "source_rights_status": self.source_rights_status,
            "source_rights_evidence_id": self.source_rights_evidence_id,
            "source_rights_evidence": rights,
            "raw_sha256": digest, "raw_byte_count": len(raw_bytes),
            "parser_name": self.parser_name, "parser_version": self.parser_version,
            "session_complete": self.session_complete,
        }


class BrokerRawCaptureRegistry:
    """Content-addressed raw bytes plus append-only state-transition audit."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.database = self.root / "capture_registry.sqlite3"
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS captures (
                    batch_id TEXT PRIMARY KEY,
                    identity_key TEXT NOT NULL UNIQUE,
                    manifest_json TEXT NOT NULL,
                    raw_object_path TEXT NOT NULL,
                    state TEXT NOT NULL,
                    dry_run_sha256 TEXT,
                    operator_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS capture_audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_at TEXT NOT NULL,
                    actor_id TEXT,
                    detail_json TEXT NOT NULL
                )
            """)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.database)
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _event(self, con, batch_id: str, event: str, detail: Mapping[str, Any],
               actor_id: str | None = None) -> None:
        con.execute(
            "INSERT INTO capture_audit_events(batch_id,event_type,event_at,actor_id,detail_json) "
            "VALUES(?,?,?,?,?)",
            [batch_id, event, datetime.now(timezone.utc).isoformat(), actor_id,
             _canonical(dict(detail))],
        )

    def stage(self, manifest: RawCaptureManifest, raw_bytes: bytes) -> dict[str, Any]:
        """Persist original bytes before parsing; exact replay returns same batch."""
        normalized = manifest.validate(raw_bytes)
        identity = [normalized["source_id"], normalized["trade_date"],
                    normalized["capture_id"]]
        identity_key = _canonical(identity)
        manifest_json = _canonical(normalized)
        batch_id = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
        object_path = self.objects / normalized["raw_sha256"][:2] / (
            normalized["raw_sha256"] + ".bin")
        object_path.parent.mkdir(parents=True, exist_ok=True)
        if not object_path.exists():
            fd, temporary = tempfile.mkstemp(prefix=".capture-", dir=object_path.parent)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(raw_bytes)
                    handle.flush()
                    os.fsync(handle.fileno())
                try:
                    os.link(temporary, object_path)
                except FileExistsError:
                    pass
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        if object_path.read_bytes() != raw_bytes:
            raise CaptureConflict("content_addressed_object_mismatch")

        now = datetime.now(timezone.utc).isoformat()
        state = ("rejected" if normalized["source_rights_status"] != "cleared"
                 or not normalized["session_complete"] else "staged")
        with self._connect() as con:
            old = con.execute(
                "SELECT batch_id, manifest_json, state FROM captures WHERE identity_key=?",
                [identity_key],
            ).fetchone()
            if old:
                if old[1] != manifest_json:
                    raise CaptureConflict("capture_identity_reused_with_changed_evidence")
                return {"batch_id": old[0], "state": old[2], "idempotent_replay": True,
                        "raw_sha256": normalized["raw_sha256"]}
            con.execute(
                "INSERT INTO captures VALUES(?,?,?,?,?,?,?,?,?)",
                [batch_id, identity_key, manifest_json, str(object_path), state,
                 None, None, now, now],
            )
            self._event(con, batch_id, state, {
                "raw_sha256": normalized["raw_sha256"],
                "raw_byte_count": normalized["raw_byte_count"],
                "reason": ("rights_not_cleared" if normalized["source_rights_status"] != "cleared"
                           else "session_incomplete" if not normalized["session_complete"] else None),
            })
        return {"batch_id": batch_id, "state": state, "idempotent_replay": False,
                "raw_sha256": normalized["raw_sha256"], "raw_object_path": str(object_path)}

    @staticmethod
    def _reconciliation_payload(report: IngestionReport) -> dict[str, Any]:
        if not isinstance(report, IngestionReport):
            raise CaptureRejected("typed_ingestion_report_required")
        return {
            "batch_id": report.batch_id,
            "coverage_status": report.coverage_status,
            "coverage_ratio": report.coverage_ratio,
            "accepted": report.accepted,
            "quarantined": report.quarantined,
            "duplicates_skipped": report.duplicates_skipped,
            "conflicts": report.conflicts,
            "reconciliation": report.reconciliation,
            "memory_eligible": report.memory_eligible,
        }

    @staticmethod
    def _bind_row_lineage(report: IngestionReport, manifest: Mapping[str, Any]) -> None:
        """Bind P4.35 contract-row lineage to the immutable staged capture."""
        raw_hash = manifest.get("raw_sha256")
        if not isinstance(raw_hash, str) or len(raw_hash) != 64:
            raise CaptureRejected("invalid_staged_capture_hash")
        for index, row in enumerate(report.accepted):
            if row.get("source_id") != manifest.get("source_id"):
                raise CaptureRejected(f"row_source_capture_mismatch:{index}")
            if row.get("session_date") != manifest.get("trade_date"):
                raise CaptureRejected(f"row_trade_date_capture_mismatch:{index}")
            supplied_capture_hash = row.get("raw_capture_sha256")
            if supplied_capture_hash is not None and supplied_capture_hash != raw_hash:
                raise CaptureRejected(f"row_raw_capture_hash_mismatch:{index}")
            lineage = row.get("raw_record_lineage")
            if not isinstance(lineage, list) or not lineage:
                raise CaptureRejected(f"raw_record_lineage_required:{index}")
            normalized = []
            for record_index, record in enumerate(lineage):
                if not isinstance(record, Mapping):
                    raise CaptureRejected(f"invalid_raw_record_lineage:{index}:{record_index}")
                digest = record.get("raw_record_sha256")
                locator = record.get("raw_record_locator")
                if (not isinstance(digest, str) or len(digest) != 64
                        or any(ch not in "0123456789abcdef" for ch in digest.lower())):
                    raise CaptureRejected(f"invalid_raw_record_sha256:{index}:{record_index}")
                if not isinstance(locator, str) or not locator.strip():
                    raise CaptureRejected(f"missing_raw_record_locator:{index}:{record_index}")
                normalized.append({
                    "raw_record_sha256": digest.lower(),
                    "raw_record_locator": locator.strip(),
                    **({"contract_id": str(record["contract_id"])}
                       if record.get("contract_id") is not None else {}),
                })
            row["raw_record_lineage"] = normalized
            row["raw_capture_sha256"] = raw_hash.lower()

    def record_dry_run(self, batch_id: str, report: IngestionReport) -> str:
        """Bind dry-run approval to the complete typed reconciler output."""
        if not isinstance(report, IngestionReport):
            raise CaptureRejected("typed_ingestion_report_required")
        if report.batch_id != batch_id:
            raise CaptureRejected("reconciliation_batch_id_mismatch")
        if not report.memory_eligible or report.coverage_status != "complete":
            raise CaptureRejected("reconciliation_not_memory_eligible")
        if report.quarantined or report.conflicts:
            raise CaptureRejected("reconciliation_contains_quarantine_or_conflicts")
        with self._connect() as con:
            row = con.execute("SELECT state,manifest_json FROM captures WHERE batch_id=?", [batch_id]).fetchone()
            if not row:
                raise CaptureRejected("unknown_batch")
            if row[0] != "staged":
                raise CaptureRejected("dry_run_requires_staged_batch")
            self._bind_row_lineage(report, json.loads(row[1]))
            payload = self._reconciliation_payload(report)
            report_json = _canonical(payload)
            report_hash = hashlib.sha256(report_json.encode("utf-8")).hexdigest()
            con.execute("UPDATE captures SET state='dry_run_passed', dry_run_sha256=?, updated_at=? WHERE batch_id=?",
                        [report_hash, datetime.now(timezone.utc).isoformat(), batch_id])
            self._event(con, batch_id, "dry_run_passed", {
                "report_sha256": report_hash,
                "accepted_count": len(report.accepted),
                "quarantined_count": len(report.quarantined),
                "duplicates_skipped": report.duplicates_skipped,
                "conflicts": report.conflicts,
                "coverage_status": report.coverage_status,
            })
        return report_hash

    def approve(self, batch_id: str, *, operator_id: str, dry_run_sha256: str) -> None:
        """Explicit human approval bound to the exact dry-run report hash."""
        if not isinstance(operator_id, str) or not operator_id.strip():
            raise CaptureRejected("operator_identity_required")
        with self._connect() as con:
            row = con.execute("SELECT state,dry_run_sha256 FROM captures WHERE batch_id=?",
                              [batch_id]).fetchone()
            if not row:
                raise CaptureRejected("unknown_batch")
            if row[0] != "dry_run_passed":
                raise CaptureRejected("clean_dry_run_required")
            if row[1] != dry_run_sha256:
                raise CaptureRejected("dry_run_hash_mismatch")
            con.execute("UPDATE captures SET state='approved',operator_id=?,updated_at=? WHERE batch_id=?",
                        [operator_id.strip(), datetime.now(timezone.utc).isoformat(), batch_id])
            self._event(con, batch_id, "approved", {"dry_run_sha256": dry_run_sha256},
                        operator_id.strip())

    def admit_to_daily_history(self, batch_id: str, report: IngestionReport, *,
                                coverage_manifest: Mapping[str, Any],
                                history_store: Any) -> dict[str, Any]:
        """Append to the existing P4.35 ledger only after approved exact-report replay.

        The ledger's own validation remains authoritative. If the append succeeds but
        the registry update is interrupted, retrying is safe because the ledger is
        append-only/idempotent and the registry records the same receipt.
        """
        with self._connect() as con:
            row = con.execute(
                "SELECT state,dry_run_sha256,operator_id FROM captures WHERE batch_id=?",
                [batch_id]).fetchone()
        if not row:
            raise CaptureRejected("unknown_batch")
        stored_capture = self.get(batch_id)
        self._bind_row_lineage(report, stored_capture["manifest"])
        payload = self._reconciliation_payload(report)
        report_hash = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
        if row[0] not in {"approved", "admitted"} or not row[2]:
            raise CaptureRejected("explicit_operator_approval_required")
        if report.batch_id != batch_id or row[1] != report_hash:
            raise CaptureRejected("approved_reconciliation_report_mismatch")
        if not report.memory_eligible:
            raise CaptureRejected("reconciler_batch_not_memory_eligible")

        receipt = history_store.append_validated_daily_batch(
            report, coverage_manifest=dict(coverage_manifest),
            raw_capture_manifest=stored_capture["manifest"],
            reconciliation_sha256=report_hash)
        receipt_payload = dict(receipt)
        with self._connect() as con:
            current = con.execute("SELECT state FROM captures WHERE batch_id=?",
                                  [batch_id]).fetchone()
            if not current:
                raise CaptureRejected("unknown_batch")
            if current[0] == "admitted":
                return receipt_payload
            if current[0] != "approved":
                raise CaptureRejected("admission_requires_approved_batch")
            con.execute("UPDATE captures SET state='admitted',updated_at=? WHERE batch_id=?",
                        [datetime.now(timezone.utc).isoformat(), batch_id])
            self._event(con, batch_id, "admitted", {
                "descriptive_only": True,
                "reconciliation_sha256": report_hash,
                "daily_history_receipt": receipt_payload,
            }, row[2])
        return receipt_payload

    def get(self, batch_id: str) -> dict[str, Any]:
        with self._connect() as con:
            row = con.execute(
                "SELECT manifest_json,raw_object_path,state,dry_run_sha256,operator_id "
                "FROM captures WHERE batch_id=?", [batch_id]).fetchone()
            if not row:
                raise CaptureRejected("unknown_batch")
            return {"manifest": json.loads(row[0]), "raw_object_path": row[1],
                    "state": row[2], "dry_run_sha256": row[3], "operator_id": row[4]}

    def events(self, batch_id: str) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT event_type,event_at,actor_id,detail_json FROM capture_audit_events "
                "WHERE batch_id=? ORDER BY event_id", [batch_id]).fetchall()
        return [{"event_type": r[0], "event_at": r[1], "actor_id": r[2],
                 "detail": json.loads(r[3])} for r in rows]
