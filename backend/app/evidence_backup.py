"""Verified, isolated backup and restore for the bronze evidence store.

The caller must quiesce all writers before backup. This module checkpoints
DuckDB, verifies the source, copies the database and raw-object tree, and
records SHA-256 checksums. Restore verifies every byte before rebinding the
catalog's absolute filesystem paths into a new isolated destination.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from .evidence_recovery import audit_evidence_store


BACKUP_MANIFEST = "backup-manifest.json"
DATABASE_NAME = "evidence.duckdb"
RAW_DIRECTORY = "raw"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory(root: Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        entries[relative] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    return entries


def _checkpoint(database: Path) -> None:
    con = duckdb.connect(str(database))
    try:
        con.execute("CHECKPOINT")
    finally:
        con.close()


def create_evidence_backup(
    *, database_path: str | Path, storage_root: str | Path,
    backup_destination: str | Path, backup_id: str,
    writers_quiesced: bool,
) -> dict[str, Any]:
    """Create a new, immutable-by-convention backup directory; never overwrite."""
    database = Path(database_path).expanduser().resolve()
    source_root = Path(storage_root).expanduser().resolve()
    destination = Path(backup_destination).expanduser().resolve()
    if not writers_quiesced:
        raise ValueError("writers_quiesced must be true; pause ingestion before backup")
    if not backup_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for ch in backup_id):
        raise ValueError("backup_id contains unsafe characters")
    if not database.is_file() or not source_root.is_dir():
        raise FileNotFoundError("source database and raw storage root must exist")
    if destination.exists():
        raise FileExistsError("backup destination already exists; backups are never overwritten")
    _checkpoint(database)
    source_audit = audit_evidence_store(database_path=database, storage_root=source_root)
    if source_audit["status"] != "integrity_ok":
        raise ValueError("source evidence store failed integrity audit; backup refused")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{backup_id}-", dir=destination.parent))
    try:
        shutil.copy2(database, staging / DATABASE_NAME)
        shutil.copytree(source_root, staging / RAW_DIRECTORY)
        files = _inventory(staging)
        manifest = {
            "schema_version": 1,
            "backup_id": backup_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "database_file": DATABASE_NAME,
            "raw_directory": RAW_DIRECTORY,
            "source_storage_root": str(source_root),
            "source_audit": {
                "raw_objects_checked": source_audit["raw_objects_checked"],
                "captures_checked": source_audit["captures_checked"],
                "normalized_records_checked": source_audit["normalized_records_checked"],
            },
            "files": files,
            "production_eligible": False,
        }
        manifest_path = staging / BACKUP_MANIFEST
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        with manifest_path.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(staging, destination)
    except Exception:
        # Preserve a failed staging directory for operator inspection.
        raise

    return {
        "status": "backup_created",
        "backup_id": backup_id,
        "backup_path": str(destination),
        "files_checked": len(files),
        "source_audit": source_audit,
        "production_eligible": False,
    }


def verify_evidence_backup(backup_path: str | Path) -> dict[str, Any]:
    """Verify backup inventory and bytes without modifying the backup."""
    root = Path(backup_path).expanduser().resolve()
    manifest_path = root / BACKUP_MANIFEST
    result: dict[str, Any] = {
        "status": "invalid",
        "files_checked": 0,
        "issues": [],
        "production_eligible": False,
    }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        result["issues"].append("backup_manifest_missing_or_invalid")
        return result
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), dict):
        result["issues"].append("backup_manifest_schema_invalid")
        return result

    expected = manifest["files"]
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != BACKUP_MANIFEST
    }
    if actual_paths != set(expected):
        result["issues"].append("backup_file_inventory_mismatch")
    for relative, metadata in expected.items():
        candidate = (root / relative).resolve()
        if root not in candidate.parents:
            result["issues"].append("backup_manifest_path_escape")
            continue
        if not candidate.is_file():
            result["issues"].append(f"backup_file_missing:{relative}")
            continue
        result["files_checked"] += 1
        if candidate.stat().st_size != metadata.get("bytes") or _sha256(candidate) != metadata.get("sha256"):
            result["issues"].append(f"backup_file_checksum_mismatch:{relative}")
    result["status"] = "verified" if not result["issues"] else "integrity_issues"
    return result


def restore_evidence_backup(
    *, backup_path: str | Path, restore_destination: str | Path
) -> dict[str, Any]:
    """Restore a verified backup to a new directory and rebind catalog paths."""
    backup = Path(backup_path).expanduser().resolve()
    destination = Path(restore_destination).expanduser().resolve()
    if destination.exists():
        raise FileExistsError("restore destination already exists; live stores are never overwritten")
    verification = verify_evidence_backup(backup)
    if verification["status"] != "verified":
        raise ValueError("backup verification failed; restore refused")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".restore-", dir=destination.parent))
    try:
        shutil.copy2(backup / DATABASE_NAME, staging / DATABASE_NAME)
        shutil.copytree(backup / RAW_DIRECTORY, staging / RAW_DIRECTORY)
        database = staging / DATABASE_NAME
        restored_root = staging / RAW_DIRECTORY
        con = duckdb.connect(str(database))
        transaction_started = False
        try:
            object_rows = con.execute(
                "SELECT source_id, payload_sha256, payload_path FROM raw_source_objects"
            ).fetchall()
            capture_rows = con.execute(
                "SELECT fetch_id, manifest_path FROM source_captures"
            ).fetchall()
            # The source root is recorded in the backup manifest. Do not infer
            # it from directory names: deployments may call the root anything.
            backup_manifest = json.loads((backup / BACKUP_MANIFEST).read_text(encoding="utf-8"))
            old_root = Path(backup_manifest["source_storage_root"]).resolve()
            for _, _, payload_name in object_rows:
                Path(payload_name).resolve().relative_to(old_root)
            for _, manifest_name in capture_rows:
                Path(manifest_name).resolve().relative_to(old_root)
            con.execute("BEGIN TRANSACTION")
            transaction_started = True
            for source_id, digest, payload_name in object_rows:
                old_path = Path(payload_name).resolve()
                relative = old_path.relative_to(old_root)
                new_path = restored_root / relative
                if not new_path.is_file():
                    raise ValueError("backed-up raw payload missing during restore")
                con.execute(
                    "UPDATE raw_source_objects SET payload_path = ? WHERE source_id = ? AND payload_sha256 = ?",
                    [str(new_path), source_id, digest],
                )
            for fetch_id, manifest_name in capture_rows:
                old_path = Path(manifest_name).resolve()
                relative = old_path.relative_to(old_root)
                new_path = restored_root / relative
                if not new_path.is_file():
                    raise ValueError("backed-up capture manifest missing during restore")
                con.execute(
                    "UPDATE source_captures SET manifest_path = ? WHERE fetch_id = ?",
                    [str(new_path), fetch_id],
                )
            con.execute("COMMIT")
            transaction_started = False
            con.execute("CHECKPOINT")
        except Exception:
            if transaction_started:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

        restored_audit = audit_evidence_store(
            database_path=database, storage_root=restored_root
        )
        if restored_audit["status"] != "integrity_ok":
            raise ValueError("restored evidence store failed post-restore integrity audit")
        os.replace(staging, destination)
    except Exception:
        # Keep staging intact for diagnosis; do not silently discard evidence.
        raise

    return {
        "status": "restore_verified",
        "restore_path": str(destination),
        "backup_verification": verification,
        "restored_audit": audit_evidence_store(
            database_path=destination / DATABASE_NAME,
            storage_root=destination / RAW_DIRECTORY,
        ),
        "production_eligible": False,
    }
