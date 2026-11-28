#!/usr/bin/env python3
"""Operator-invoked, fail-closed bronze evidence backup and verification.

The destination should be a separately managed, access-controlled backup
mount. This script does not schedule jobs, encrypt data, or delete old backups.
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


def validate_backup_destination(database: str | Path, storage_root: str | Path, destination_root: str | Path) -> dict[str, str]:
    database_path = Path(database).expanduser().resolve()
    storage_path = Path(storage_root).expanduser().resolve()
    destination_path = Path(destination_root).expanduser().resolve()
    if not database_path.is_file():
        raise ValueError('database_file_must_exist')
    if not storage_path.is_dir() or not destination_path.is_dir():
        raise ValueError('storage_and_destination_directories_must_exist')
    destination_device = os.stat(destination_path).st_dev
    source_devices = {os.stat(database_path.parent).st_dev, os.stat(storage_path).st_dev}
    if destination_device in source_devices:
        raise ValueError('backup_destination_must_be_separate_filesystem')
    if destination_path == storage_path or storage_path in destination_path.parents:
        raise ValueError('backup_destination_must_not_be_inside_raw_storage')
    if destination_path == database_path.parent or database_path.parent in destination_path.parents:
        raise ValueError('backup_destination_must_not_be_inside_database_directory')
    return {'destination': str(destination_path), 'filesystem_separation': 'verified_distinct_device',
            'off_host_status': 'not_verified_operator_confirmation_required'}

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

    destination_root = Path(args.destination_root).expanduser().resolve()
    if not destination_root.is_dir():
        parser.error("destination root must already exist as a mounted directory")
    try:
        destination_check = validate_backup_destination(args.database, args.storage_root, destination_root)
    except ValueError as exc:
        parser.error(f'refusing backup: {exc}')
    backup_path = destination_root / backup_id

    created = create_evidence_backup(
        database_path=args.database,
        storage_root=args.storage_root,
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
        "destination_check": destination_check,
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


if __name__ == "__main__":
    raise SystemExit(main())
