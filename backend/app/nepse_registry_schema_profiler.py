"""Profile a captured NEPSE/SEBON JSON registry without assigning field meaning.

This is a schema-discovery aid only. It reports object-array paths, key names,
JSON value types and counts. It never maps fields to security identity or
promotes records into a security master.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def profile_registry_json(
    raw_payload: bytes,
    *,
    max_payload_bytes: int = 50 * 1024 * 1024,
    max_depth: int = 12,
    max_nodes: int = 100_000,
) -> dict[str, Any]:
    """Return structural observations for an exact captured JSON payload."""
    if not isinstance(raw_payload, bytes) or not raw_payload:
        raise ValueError("raw_payload_must_be_nonempty_bytes")
    if (isinstance(max_payload_bytes, bool) or not isinstance(max_payload_bytes, int)
            or max_payload_bytes < 1):
        raise ValueError("max_payload_bytes_must_be_positive_integer")
    if len(raw_payload) > max_payload_bytes:
        raise ValueError("registry_payload_exceeds_max_payload_bytes")
    if (isinstance(max_depth, bool) or not isinstance(max_depth, int)
            or max_depth < 0 or max_depth > 32):
        raise ValueError("max_depth_must_be_between_0_and_32")
    if (isinstance(max_nodes, bool) or not isinstance(max_nodes, int)
            or max_nodes < 1 or max_nodes > 1_000_000):
        raise ValueError("max_nodes_must_be_between_1_and_1000000")
    try:
        document = json.loads(raw_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("registry_payload_is_not_valid_json") from exc
    if not isinstance(document, (dict, list)):
        raise ValueError("registry_json_root_must_be_object_or_array")

    arrays: list[dict[str, Any]] = []
    nodes_visited = 0
    truncated = False

    def visit(value: Any, path: str, depth: int) -> None:
        nonlocal nodes_visited, truncated
        if nodes_visited >= max_nodes:
            truncated = True
            return
        nodes_visited += 1
        if depth > max_depth:
            truncated = True
            return
        if isinstance(value, dict):
            for key, child in sorted(value.items(), key=lambda item: str(item[0])):
                child_path = f"{path}.{key}" if path else str(key)
                visit(child, child_path, depth + 1)
        elif isinstance(value, list):
            object_rows = [row for row in value if isinstance(row, dict)]
            if object_rows:
                field_types: dict[str, set[str]] = defaultdict(set)
                field_presence: dict[str, int] = defaultdict(int)
                for row in object_rows:
                    for key, field_value in row.items():
                        field_name = str(key)
                        field_types[field_name].add(_json_type(field_value))
                        field_presence[field_name] += 1
                arrays.append({
                    "path": path or "$",
                    "array_length": len(value),
                    "object_row_count": len(object_rows),
                    "non_object_item_count": len(value) - len(object_rows),
                    "fields": [
                        {
                            "name": name,
                            "observed_types": sorted(field_types[name]),
                            "present_in_object_rows": field_presence[name],
                        }
                        for name in sorted(field_types)
                    ],
                })
            for index, child in enumerate(value):
                if nodes_visited >= max_nodes:
                    truncated = True
                    break
                visit(child, f"{path}[{index}]", depth + 1)

    visit(document, "$", 0)
    arrays.sort(key=lambda item: item["path"])
    return {
        "schema_version": 1,
        "profile_type": "structural_schema_observation_only",
        "payload_sha256": hashlib.sha256(raw_payload).hexdigest(),
        "payload_byte_count": len(raw_payload),
        "json_root_type": _json_type(document),
        "object_array_candidates": arrays,
        "nodes_visited": nodes_visited,
        "truncated": truncated,
        "field_semantics_assigned": False,
        "security_identity_verified": False,
        "membership_admission_allowed": False,
        "production_sector_signals_allowed": False,
        "limitations": [
            "Field names and JSON types are observations, not semantic mappings.",
            "An object array is not assumed to be a complete security universe.",
            "No security ID, symbol, company name, instrument type or sector field is inferred.",
            "No records are normalized, reconciled, admitted or promoted.",
        ],
    }
