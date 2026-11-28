#!/usr/bin/env python3
"""Operator-invoked, fail-closed bronze evidence backup and verification.

The destination must be an existing mount point, separately managed from the
source store. This script does not schedule jobs, encrypt data, or delete backups.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.evidence_backup import create_evidence_backup, verify_evidence_backup  # noqa: E402


def validate_backup_paths(database_path: str, storage_root: str, destination_root: str) -> tuple[Path, Path, Path]:
    """Validate that the backup mount exists and cannot recurse into its source."""
    database = Path(database_path).expanduser().resolve()
    source_root = Path(storage_root).expanduser().resolve()
    destination = Path(destination_root).expanduser().resolve()
    if not destination.is_dir():
        raise ValueError("destination root must already exist as a mounted directory")
    if not os.path.ismount(destination):
        raise ValueError("destination root is not a mounted filesystem; refusing same-volume backup")
    if destination == source_root or destination in source_root.parents or source_root in destination.parents:
        raise ValueError("destination and raw storage source must not overlap")
    if destination == database or destination in database.parents:
        raise ValueError("database source must not be located inside the backup destination")
    return database, source_root, destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Bronze evidence DuckDB file")
    parser.add_argument("--storage-root", required=True, help="Bronze raw payload root")
    parser.add_argument("--destination-root", required=True, help="Mounted backup destination root")
    parser.add_argument("--backup-id", help="Unique backup ID; defaults to UTC timestamp")
    parser.add_argument(
        "--writers-quiesced", action="store_true",
        help="Explicit operator attestation that all evidence-store writers are stopped",
    )
    args = parser.parse_args()

    if not args.writers_quiesced:
        parser.error("refusing backup: stop all writers, then pass --writers-quiesced")
    backup_id = args.backup_id or datetime.now(timezone.utc).strftime("evidence-%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", backup_id):
        parser.error("backup ID may contain only letters, digits, dot, underscore and hyphen")

    try:
        database, source_root, destination_root = validate_backup_paths(
            args.database, args.storage_root, args.destination_root
        )
    except ValueError as exc:
        parser.error(str(exc))

    backup_path = destination_root / backup_id
    try:
        created = create_evidence_backup(
            database_path=database,
            storage_root=source_root,
            backup_destination=backup_path,
            backup_id=backup_id,
            writers_quiesced=True,
        )
        verified = verify_evidence_backup(backup_path)
        result = {
            "status": "backup_verified" if verified.get("status") == "verified" else "verification_failed",
            "backup": created,
            "verification": verified,
            "destination_root": str(destination_root),
            "operator_checks_required": [
                "confirm destination is off-host and access-controlled",
                "confirm encryption at rest and key recovery procedure",
                "record backup timestamp, host, volume identity and retention class",
                "perform periodic isolated restore and retain audit report",
            ],
            "production_eligible": False,
        }
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
        return 0 if verified.get("status") == "verified" else 2
    except Exception as exc:
        print(json.dumps({
            "status": "backup_failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "backup_path": str(backup_path),
            "production_eligible": False,
        }, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
