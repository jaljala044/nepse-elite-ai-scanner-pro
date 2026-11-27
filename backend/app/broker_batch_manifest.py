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
from typing import Any, Mapping


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
        return {
            "manifest_version": self.manifest_version,
            "trade_date": self.trade_date, "source_id": self.source_id,
            "capture_id": self.capture_id, "captured_at": captured.isoformat(),
            "available_at": available.isoformat(),
            "source_rights_status": self.source_rights_status,
            "source_rights_evidence_id": self.source_rights_evidence_id,
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

    def _connect(self):
        con = sqlite3.connect(self.database)
        con.execute("PRAGMA foreign_keys=ON")
        return con

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

    def record_dry_run(self, batch_id: str, report: Mapping[str, Any]) -> str:
        """Record reconciliation output; any flagged/quarantined row rejects the batch."""
        if not isinstance(report, Mapping):
            raise CaptureRejected("dry_run_report_required")
        report_json = _canonical(dict(report))
        report_hash = hashlib.sha256(report_json.encode("utf-8")).hexdigest()
        clean = report.get("passed") is True and report.get("quarantined_count", 0) == 0
        with self._connect() as con:
            row = con.execute("SELECT state FROM captures WHERE batch_id=?", [batch_id]).fetchone()
            if not row:
                raise CaptureRejected("unknown_batch")
            if row[0] != "staged":
                raise CaptureRejected("dry_run_requires_staged_batch")
            state = "dry_run_passed" if clean else "rejected"
            con.execute("UPDATE captures SET state=?, dry_run_sha256=?, updated_at=? WHERE batch_id=?",
                        [state, report_hash, datetime.now(timezone.utc).isoformat(), batch_id])
            self._event(con, batch_id, state, {"report_sha256": report_hash,
                         "quarantined_count": report.get("quarantined_count")})
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

    def mark_admitted(self, batch_id: str, *, reconciler_memory_eligible: bool) -> None:
        """Mark downstream admission only after approval and a clean reconciler result."""
        if reconciler_memory_eligible is not True:
            raise CaptureRejected("reconciler_batch_not_memory_eligible")
        with self._connect() as con:
            row = con.execute("SELECT state,operator_id FROM captures WHERE batch_id=?",
                              [batch_id]).fetchone()
            if not row:
                raise CaptureRejected("unknown_batch")
            if row[0] != "approved" or not row[1]:
                raise CaptureRejected("explicit_operator_approval_required")
            con.execute("UPDATE captures SET state='admitted',updated_at=? WHERE batch_id=?",
                        [datetime.now(timezone.utc).isoformat(), batch_id])
            self._event(con, batch_id, "admitted",
                        {"descriptive_only": True}, row[1])

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
