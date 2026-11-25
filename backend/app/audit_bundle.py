"""Deterministic, content-addressed JSON audit bundle for pipeline outputs."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from typing import Any


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        return sorted(_json_safe(v) for v in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported audit bundle value: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    safe = _json_safe(value)
    return json.dumps(safe, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def build_audit_bundle(artifacts: dict[str, Any], *, schema_version: int = 1) -> dict:
    """Hash each named artifact and the complete manifest; does not write files."""
    if not artifacts:
        raise ValueError("at least one named artifact is required")
    if schema_version < 1:
        raise ValueError("schema_version must be positive")
    entries = {}
    for name in sorted(artifacts):
        if not name.strip():
            raise ValueError("artifact names cannot be blank")
        payload = canonical_json_bytes(artifacts[name])
        entries[name] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "byte_length": len(payload),
            "content_utf8": payload.decode("utf-8"),
        }
    manifest_body = {
        "schema_version": schema_version,
        "artifact_count": len(entries),
        "artifacts": {name: {k: v for k, v in item.items() if k != "content_utf8"}
                      for name, item in entries.items()},
    }
    manifest_hash = hashlib.sha256(canonical_json_bytes(manifest_body)).hexdigest()
    return {
        "manifest": {**manifest_body, "manifest_sha256": manifest_hash},
        "artifacts": entries,
        "promotion_allowed": False,
        "policy": "deterministic_hashes_for_audit_not_data_quality_approval",
    }
