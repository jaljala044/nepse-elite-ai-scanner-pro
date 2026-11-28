"""Read-only restart/recovery audit for the bronze evidence store.

The audit never repairs, deletes, promotes, or rewrites evidence. It compares
DuckDB catalog lineage with immutable payload and capture-manifest files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb


def audit_evidence_store(
    *, database_path: str | Path, storage_root: str | Path
) -> dict[str, Any]:
    """Verify catalog-to-filesystem lineage without creating or mutating files."""
    database = Path(database_path).expanduser()
    root = Path(storage_root).expanduser()
    result: dict[str, Any] = {
        "status": "unavailable",
        "database_exists": database.is_file(),
        "storage_root_exists": root.is_dir(),
        "raw_objects_checked": 0,
        "captures_checked": 0,
        "normalized_records_checked": 0,
        "orphan_raw_objects": [],
        "orphan_manifests": [],
        "issues": [],
        "production_eligible": False,
        "mutated_storage": False,
    }
    if not database.is_file():
        result["issues"].append({"code": "database_missing"})
        return result
    if not root.is_dir():
        result["issues"].append({"code": "storage_root_missing"})
        return result

    con = None
    try:
        con = duckdb.connect(str(database), read_only=True)
        objects = con.execute(
            "SELECT source_id, payload_sha256, payload_bytes, payload_path "
            "FROM raw_source_objects ORDER BY source_id, payload_sha256"
        ).fetchall()
        captures = con.execute(
            "SELECT fetch_id, source_id, payload_sha256, manifest_json, manifest_path "
            "FROM source_captures ORDER BY fetch_id"
        ).fetchall()
        records = con.execute(
            "SELECT record_id, fetch_id, source_id, payload_sha256 "
            "FROM normalized_evidence_records ORDER BY record_id"
        ).fetchall()
    except Exception as exc:
        result["issues"].append({
            "code": "catalog_unreadable",
            "detail": type(exc).__name__,
        })
        if con is not None:
            con.close()
        return result
    finally:
        if con is not None:
            con.close()

    object_keys: set[tuple[str, str]] = set()
    for source_id, digest, expected_bytes, payload_name in objects:
        key = (source_id, digest)
        object_keys.add(key)
        result["raw_objects_checked"] += 1
        payload_path = Path(payload_name)
        try:
            payload = payload_path.read_bytes()
        except OSError:
            result["issues"].append({"code": "raw_payload_missing", "source_id": source_id, "sha256": digest})
            continue
        actual = hashlib.sha256(payload).hexdigest()
        if len(payload) != expected_bytes:
            result["issues"].append({"code": "raw_payload_size_mismatch", "source_id": source_id, "sha256": digest})
        if actual != digest:
            result["issues"].append({"code": "raw_payload_hash_mismatch", "source_id": source_id, "sha256": digest})

    capture_keys: set[tuple[str, str, str]] = set()
    known_manifest_paths: set[Path] = set()
    for fetch_id, source_id, digest, manifest_json, manifest_name in captures:
        result["captures_checked"] += 1
        capture_keys.add((fetch_id, source_id, digest))
        manifest_path = Path(manifest_name)
        known_manifest_paths.add(manifest_path.resolve())
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            result["issues"].append({"code": "capture_manifest_missing_or_invalid", "fetch_id": fetch_id})
            continue
        try:
            catalog_manifest = json.loads(manifest_json)
        except ValueError:
            result["issues"].append({"code": "catalog_manifest_invalid", "fetch_id": fetch_id})
            continue
        if manifest != catalog_manifest:
            result["issues"].append({"code": "capture_manifest_catalog_mismatch", "fetch_id": fetch_id})
        if (
            manifest.get("fetch_id") != fetch_id
            or manifest.get("source_id") != source_id
            or manifest.get("payload_sha256") != digest
        ):
            result["issues"].append({"code": "capture_manifest_lineage_mismatch", "fetch_id": fetch_id})
        if (source_id, digest) not in object_keys:
            result["issues"].append({"code": "capture_without_catalogued_raw_object", "fetch_id": fetch_id})

    for record_id, fetch_id, source_id, digest in records:
        result["normalized_records_checked"] += 1
        if (fetch_id, source_id, digest) not in capture_keys:
            result["issues"].append({"code": "normalized_record_orphaned", "record_id": record_id})

    indexed_payload_paths = {
        Path(row[3]).resolve() for row in objects
    }
    if root.exists():
        for payload_path in root.rglob("payload.bin"):
            if payload_path.resolve() not in indexed_payload_paths:
                result["orphan_raw_objects"].append(str(payload_path))
        for manifest_path in root.rglob("*.json"):
            if manifest_path.name == "manifest.json" or "captures" in manifest_path.parts:
                if manifest_path.resolve() not in known_manifest_paths:
                    result["orphan_manifests"].append(str(manifest_path))

    if result["orphan_raw_objects"]:
        result["issues"].append({
            "code": "unindexed_raw_objects",
            "count": len(result["orphan_raw_objects"]),
        })
    if result["orphan_manifests"]:
        result["issues"].append({
            "code": "unindexed_capture_manifests",
            "count": len(result["orphan_manifests"]),
        })
    result["status"] = "integrity_ok" if not result["issues"] else "integrity_issues"
    return result
