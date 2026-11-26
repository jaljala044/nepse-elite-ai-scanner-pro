"""Append-only DuckDB catalog for immutable raw market-data evidence.

This is a bronze/evidence layer, not a canonical price store. Parsed records are
always provisional until a separate source-trust and human-review process
promotes them. The caller's row-level status claims are never trusted.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from .raw_capture import persist_capture


RECORD_TYPES = {
    "ohlcv", "index_ohlcv", "market_summary", "floorsheet",
    "sector_membership", "sector_price", "corporate_action",
    "broker_observation", "broker",
}


def _utc(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _database_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path).expanduser()
    return Path(os.getenv(
        "NEPSE_EVIDENCE_DATABASE",
        str(Path(__file__).resolve().parents[1] / "data" / "evidence.duckdb"),
    )).expanduser()


def _connect(path: str | Path | None):
    target = _database_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(target))
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_source_objects (
            source_id VARCHAR NOT NULL,
            payload_sha256 VARCHAR NOT NULL,
            payload_bytes BIGINT NOT NULL,
            payload_path VARCHAR NOT NULL,
            first_captured_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (source_id, payload_sha256)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS source_captures (
            fetch_id VARCHAR PRIMARY KEY,
            source_id VARCHAR NOT NULL,
            source_url VARCHAR NOT NULL,
            payload_sha256 VARCHAR NOT NULL,
            requested_at TIMESTAMPTZ NOT NULL,
            received_at TIMESTAMPTZ NOT NULL,
            parser_version VARCHAR NOT NULL,
            rights_status VARCHAR NOT NULL,
            manifest_json VARCHAR NOT NULL,
            manifest_path VARCHAR NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS normalized_evidence_records (
            record_id VARCHAR PRIMARY KEY,
            fetch_id VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            payload_sha256 VARCHAR NOT NULL,
            source_row_number BIGINT NOT NULL,
            record_type VARCHAR NOT NULL,
            session_date DATE,
            available_at TIMESTAMPTZ NOT NULL,
            source_validation_status VARCHAR NOT NULL,
            finality_status VARCHAR NOT NULL,
            parser_version VARCHAR NOT NULL,
            record_json VARCHAR NOT NULL,
            UNIQUE (fetch_id, source_row_number)
        )
    """)
    return con


def persist_evidence_batch(
    payload: bytes,
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    storage_root: str | Path,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    """Persist exact raw bytes, capture metadata and provisional parsed rows.

    Availability is assigned from server-side capture receipt time. Any supplied
    row availability later than receipt is rejected; embedded trust/finality
    labels are discarded and replaced with review_required/provisional.
    """
    if not isinstance(payload, bytes):
        raise TypeError("payload must be exact bytes")
    if not isinstance(manifest, dict) or not isinstance(records, list):
        raise ValueError("manifest and records have invalid types")
    digest = hashlib.sha256(payload).hexdigest()
    if manifest.get("payload_sha256") != digest:
        raise ValueError("manifest payload_sha256 does not match exact payload bytes")
    if manifest.get("payload_bytes") != len(payload):
        raise ValueError("manifest payload_bytes does not match exact payload bytes")

    source_id = manifest.get("source_id")
    fetch_id = manifest.get("fetch_id")
    source_url = manifest.get("source_url")
    parser_version = manifest.get("parser_version") or "unassigned"
    if not all(isinstance(v, str) and v.strip() for v in (source_id, fetch_id, source_url, parser_version)):
        raise ValueError("manifest source_id, fetch_id, source_url and parser_version are required")
    requested_at = _utc(manifest.get("requested_at_utc"), "requested_at_utc")
    received_at = _utc(manifest.get("received_at_utc"), "received_at_utc")
    if datetime.fromisoformat(requested_at.replace("Z", "+00:00")) > datetime.fromisoformat(received_at.replace("Z", "+00:00")):
        raise ValueError("requested_at_utc cannot follow received_at_utc")

    stored = persist_capture(storage_root, payload, manifest)
    normalized = []
    seen_rows = set()
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise ValueError(f"record {index} must be an object")
        row_number = row.get("source_row_number")
        if isinstance(row_number, bool) or not isinstance(row_number, int) or row_number < 1:
            raise ValueError(f"record {index} source_row_number must be a positive integer")
        if row_number in seen_rows:
            raise ValueError(f"duplicate source_row_number: {row_number}")
        seen_rows.add(row_number)
        record_type = row.get("record_type")
        if record_type not in RECORD_TYPES:
            raise ValueError(f"record {index} has unsupported record_type")
        session_value = row.get("session_date")
        session = None
        if session_value not in (None, ""):
            try:
                session = date.fromisoformat(str(session_value)).isoformat()
            except ValueError as exc:
                raise ValueError(f"record {index} session_date must be YYYY-MM-DD") from exc
            if session != session_value:
                raise ValueError(f"record {index} session_date must be YYYY-MM-DD")
        if row.get("available_at") is not None:
            supplied = _utc(row["available_at"], f"record {index} available_at")
            if datetime.fromisoformat(supplied.replace("Z", "+00:00")) > datetime.fromisoformat(received_at.replace("Z", "+00:00")):
                raise ValueError(f"record {index} available_at cannot follow capture receipt")
        record_body = dict(row)
        record_body.pop("source_validation_status", None)
        record_body.pop("finality_status", None)
        record_body.pop("available_at", None)
        record_body.update({
            "fetch_id": fetch_id,
            "source_id": source_id,
            "source_payload_sha256": digest,
            "source_row_number": row_number,
            "available_at": received_at,
            "source_validation_status": "review_required",
            "finality_status": "provisional",
            "parser_version": parser_version,
        })
        record_json = json.dumps(record_body, sort_keys=True, separators=(",", ":"), default=str)
        record_id = hashlib.sha256(
            f"{fetch_id}:{source_id}:{digest}:{row_number}:{parser_version}".encode("utf-8")
        ).hexdigest()
        normalized.append((
            record_id, fetch_id, source_id, digest, row_number, record_type,
            session, received_at, "review_required", "provisional",
            parser_version, record_json,
        ))

    manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    con = _connect(database_path)
    try:
        con.execute("BEGIN TRANSACTION")
        existing = con.execute(
            "SELECT source_id, payload_sha256, manifest_json FROM source_captures WHERE fetch_id = ?",
            [fetch_id],
        ).fetchone()
        if existing and (existing[0] != source_id or existing[1] != digest or existing[2] != manifest_json):
            raise ValueError("fetch_id already exists with different immutable capture metadata")
        if existing:
            stored_rows = con.execute(
                "SELECT source_row_number, record_json FROM normalized_evidence_records "
                "WHERE fetch_id = ? ORDER BY source_row_number",
                [fetch_id],
            ).fetchall()
            expected_rows = sorted((item[4], item[11]) for item in normalized)
            if stored_rows != expected_rows:
                raise ValueError(
                    "fetch_id already exists with different immutable normalized record batch"
                )
            # An exact replay is a read-only confirmation, not a second insert.
        else:
            con.execute("""
                INSERT INTO raw_source_objects
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (source_id, payload_sha256) DO NOTHING
            """, [source_id, digest, len(payload), stored["payload_path"], received_at])
            con.execute("""
                INSERT INTO source_captures
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [fetch_id, source_id, source_url, digest, requested_at, received_at,
                  parser_version, str(manifest.get("rights_status") or "unknown"),
                  manifest_json, stored["manifest_path"]])
            for item in normalized:
                con.execute("""
                    INSERT INTO normalized_evidence_records
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, list(item))
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()

    return {
        "fetch_id": fetch_id,
        "source_id": source_id,
        "payload_sha256": digest,
        "raw_object_path": stored["payload_path"],
        "manifest_path": stored["manifest_path"],
        "normalized_records": len(normalized),
        "status": "stored_review_required",
        "production_eligible": False,
        "idempotent": stored["idempotent"],
    }


def load_evidence_records(
    *, database_path: str | Path | None = None,
    record_type: str | None = None,
    include_provisional: bool = True,
) -> list[dict[str, Any]]:
    """Read records without silently promoting provisional observations."""
    con = _connect(database_path)
    try:
        clauses = []
        params: list[Any] = []
        if record_type:
            if record_type not in RECORD_TYPES:
                raise ValueError("unsupported record_type")
            clauses.append("record_type = ?")
            params.append(record_type)
        if not include_provisional:
            clauses.append("source_validation_status = 'verified' AND finality_status = 'final'")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = con.execute(
            "SELECT record_json FROM normalized_evidence_records" + where +
            " ORDER BY session_date, source_id, source_row_number",
            params,
        ).fetchall()
        return [json.loads(row[0]) for row in rows]
    finally:
        con.close()
