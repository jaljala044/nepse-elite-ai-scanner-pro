"""Fixture-oriented raw capture -> normalization -> point-in-time feature pipeline.

The parser contract is deliberately narrow JSON: a top-level list of OHLCV or
broker observation objects. Raw bytes and provisional normalized rows are
persisted before point-in-time features are built. This module does not fetch
network data or imply an official exchange schema.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.evidence_store import persist_evidence_batch
from app.raw_capture import build_capture_manifest
from app.feature_pipeline import build_feature_snapshot


OHLCV_REQUIRED = {"symbol", "session_date", "close", "previous_close", "volume"}
BROKER_REQUIRED = {"side", "amount", "identity_status"}


def normalize_json_payload(payload: bytes, received_at_utc: str) -> list[dict[str, Any]]:
    """Validate JSON fixture rows and assign availability from receipt metadata."""
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("payload must be UTF-8 JSON") from exc
    if not isinstance(decoded, list):
        raise ValueError("payload must be a top-level JSON array")
    normalized = []
    for index, row in enumerate(decoded):
        if not isinstance(row, dict):
            raise ValueError(f"row {index} must be an object")
        record_type = row.get("record_type")
        required = OHLCV_REQUIRED if record_type == "ohlcv" else BROKER_REQUIRED if record_type == "broker" else None
        if required is None:
            raise ValueError(f"row {index} has unsupported record_type")
        missing = sorted(required - row.keys())
        if missing:
            raise ValueError(f"row {index} missing required fields: {missing}")
        item = dict(row)
        # Never trust an embedded available_at value; receipt time is the earliest
        # point at which this capture can be known by this pipeline.
        item["available_at"] = received_at_utc
        item["source_row_number"] = index + 1
        item["record_id"] = hashlib.sha256(
            (str(index) + ":" + json.dumps(row, sort_keys=True, separators=(",", ":"))).encode("utf-8")
        ).hexdigest()
        normalized.append(item)
    return normalized


def capture_normalize_and_build_features(
    payload: bytes, *, storage_root: str | Path, decision_time: str,
    expected_symbols: list[str] | None = None,
    evidence_database_path: str | Path | None = None,
    **manifest_args: Any,
) -> dict[str, Any]:
    """Persist exact bytes and provisional records, then build as-of features."""
    manifest = build_capture_manifest(payload, **manifest_args)
    rows = normalize_json_payload(payload, manifest["received_at_utc"])
    stored = persist_evidence_batch(
        payload, manifest, rows, storage_root=storage_root,
        database_path=evidence_database_path,
    )
    features = build_feature_snapshot(rows, decision_time, expected_symbols)
    return {
        "capture": {
            "payload_sha256": stored["payload_sha256"],
            "payload_bytes": manifest["payload_bytes"],
            "idempotent": stored["idempotent"],
            "manifest_path": stored["manifest_path"],
            "payload_path": stored["raw_object_path"],
            "evidence_status": stored["status"],
            "production_eligible": stored["production_eligible"],
        },
        "normalized_record_count": len(rows),
        "feature_snapshot": features,
    }
