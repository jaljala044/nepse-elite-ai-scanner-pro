"""Immutable raw-response capture primitives for research ingestion.

This module deliberately does not fetch URLs or infer exchange sessions. Callers
must supply already-redacted request metadata and keep TLS verification enabled
in their HTTP client.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CaptureConflictError(RuntimeError):
    """Raised when a content-addressed destination exists with different bytes."""


def _utc_iso(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_capture_manifest(
    payload: bytes,
    *,
    source_id: str,
    source_url: str,
    request_method: str,
    request_metadata: dict[str, Any],
    requested_at: str,
    received_at: str,
    claimed_session_date: str | None = None,
    verified_session_date: str | None = None,
    session_status: str = "unverified",
    session_evidence_ref: str | None = None,
    http_status: int | None = None,
    content_type: str | None = None,
    fetch_id: str,
    parser_version: str = "unassigned",
    rights_status: str = "unknown",
) -> dict[str, Any]:
    """Build a deterministic metadata envelope; payload bytes remain separate."""
    if not isinstance(payload, bytes):
        raise TypeError("payload must be exact response bytes")
    if not source_id.strip() or not source_url.strip() or not fetch_id.strip():
        raise ValueError("source_id, source_url and fetch_id are required")
    allowed_statuses = {
        "unverified", "confirmed_open", "confirmed_closed", "exceptional_session"
    }
    if session_status not in allowed_statuses:
        raise ValueError(f"unsupported session_status: {session_status}")
    if session_status == "confirmed_open" and not verified_session_date:
        raise ValueError("confirmed_open requires verified_session_date")
    if session_status == "confirmed_closed" and not session_evidence_ref:
        raise ValueError("confirmed_closed requires session_evidence_ref")

    return {
        "schema_version": 1,
        "source_id": source_id,
        "source_url": source_url,
        "request_method": request_method.upper(),
        "request_metadata": request_metadata,
        "requested_at_utc": _utc_iso(requested_at),
        "received_at_utc": _utc_iso(received_at),
        "claimed_session_date": claimed_session_date,
        "verified_session_date": verified_session_date,
        "session_status": session_status,
        "session_evidence_ref": session_evidence_ref,
        "http_status": http_status,
        "content_type": content_type,
        "fetch_id": fetch_id,
        "parser_version": parser_version,
        "rights_status": rights_status,
        "payload_bytes": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
    }


def _atomic_create(path: Path, data: bytes) -> bool:
    """Create a file without replacing an existing path; return True if new."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".capture-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # Hard-link is an atomic no-clobber publish on the same filesystem.
            os.link(temp_name, path)
            return True
        except FileExistsError:
            return False
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def persist_capture(root: str | Path, payload: bytes, manifest: dict[str, Any]) -> dict[str, Any]:
    """Persist payload and manifest immutably under source/date/SHA-256.

    Repeating an identical capture returns idempotent=True. Existing content is
    never overwritten. A same-hash/different-bytes condition is treated as fatal.
    """
    digest = hashlib.sha256(payload).hexdigest()
    if manifest.get("payload_sha256") != digest:
        raise ValueError("manifest payload_sha256 does not match exact payload bytes")
    if manifest.get("payload_bytes") != len(payload):
        raise ValueError("manifest payload_bytes does not match exact payload bytes")
    source = str(manifest["source_id"])
    session = manifest.get("verified_session_date") or manifest.get("claimed_session_date") or "unknown-date"
    if any(part in {"", ".", ".."} or "/" in part or "\\\\" in part for part in (source, session)):
        raise ValueError("unsafe source/date path component")

    directory = Path(root) / source / session / digest
    payload_path = directory / "payload.bin"
    manifest_path = directory / "manifest.json"
    created = _atomic_create(payload_path, payload)
    if not created and payload_path.read_bytes() != payload:
        raise CaptureConflictError("existing content-addressed payload differs")
    manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest_created = _atomic_create(manifest_path, manifest_bytes)
    if not manifest_created and manifest_path.read_bytes() != manifest_bytes:
        raise CaptureConflictError("same payload hash has conflicting immutable metadata; retain a separate capture version")
    return {
        "payload_sha256": digest,
        "payload_path": str(payload_path),
        "manifest_path": str(manifest_path),
        "created": created or manifest_created,
        "idempotent": not created and not manifest_created,
    }
