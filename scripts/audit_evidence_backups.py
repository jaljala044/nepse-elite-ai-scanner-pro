#!/usr/bin/env python3
"""Read-only audit of evidence backup freshness and integrity."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.evidence_backup import BACKUP_MANIFEST, verify_evidence_backup  # noqa: E402


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("backup timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def audit(root: Path, max_age_hours: float, minimum_verified: int) -> dict:
    now = datetime.now(timezone.utc)
    records = []
    invalid = []
    for candidate in sorted(root.iterdir()):
        if candidate.is_symlink() or not candidate.is_dir():
            continue
        manifest_path = candidate / BACKUP_MANIFEST
        if not manifest_path.is_file():
            continue
        verification = verify_evidence_backup(candidate)
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            created_at = parse_utc(manifest["created_at_utc"])
            backup_id = str(manifest["backup_id"])
            if created_at > now:
                raise ValueError("backup timestamp is in the future")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            invalid.append({
                "path": str(candidate),
                "reason": "manifest_metadata_invalid",
                "detail": str(exc),
                "verification": verification,
            })
            continue
        age_hours = round((now - created_at).total_seconds() / 3600, 2)
        record = {
            "backup_id": backup_id,
            "path": str(candidate),
            "created_at_utc": created_at.isoformat().replace("+00:00", "Z"),
            "age_hours": age_hours,
            "verification": verification,
        }
        if verification.get("status") == "verified":
            records.append(record)
        else:
            invalid.append(record)

    records.sort(key=lambda item: item["created_at_utc"], reverse=True)
    latest = records[0] if records else None
    fresh = latest is not None and latest["age_hours"] <= max_age_hours
    count_ok = len(records) >= minimum_verified
    integrity_ok = not invalid
    ready = bool(fresh and count_ok and integrity_ok)
    return {
        "status": "ready" if ready else "not_ready",
        "audited_at_utc": now.isoformat().replace("+00:00", "Z"),
        "backup_root": str(root),
        "verified_backup_count": len(records),
        "invalid_backup_count": len(invalid),
        "minimum_verified_required": minimum_verified,
        "latest_verified_backup": latest,
        "maximum_age_hours": max_age_hours,
        "freshness_ok": fresh,
        "count_ok": count_ok,
        "integrity_ok": integrity_ok,
        "verified_backups": records,
        "invalid_backups": invalid,
        "offsite_location_verified": False,
        "encryption_verified": False,
        "restore_drill_verified": False,
        "production_eligible": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-root", required=True, help="Existing mounted backup root")
    parser.add_argument("--max-age-hours", type=float, default=30.0)
    parser.add_argument("--minimum-verified", type=int, default=1)
    args = parser.parse_args()
    if args.max_age_hours <= 0 or args.minimum_verified < 1:
        parser.error("max-age-hours must be positive and minimum-verified at least 1")
    root = Path(args.backup_root).expanduser().resolve()
    if not root.is_dir():
        parser.error("backup root must already exist and be a directory")
    result = audit(root, args.max_age_hours, args.minimum_verified)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
