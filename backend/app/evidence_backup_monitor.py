"""Read-only backup inventory, freshness and retention monitoring.

This module reports recovery readiness and non-destructive retention candidates.
It never deletes, rewrites, promotes or repairs a backup.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .evidence_backup import BACKUP_MANIFEST, verify_evidence_backup


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("created_at_utc is missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("created_at_utc must include a timezone")
    return parsed.astimezone(timezone.utc)


def inspect_backup_retention(
    *,
    backup_root: str | Path,
    now: datetime | None = None,
    max_age_hours: float = 26.0,
    expected_interval_hours: float = 24.0,
    grace_hours: float = 4.0,
    keep_last: int = 7,
) -> dict[str, Any]:
    """Inspect backups without modifying them; all age calculations are UTC."""
    if max_age_hours <= 0 or expected_interval_hours <= 0 or grace_hours < 0:
        raise ValueError("backup age and interval must be positive; grace cannot be negative")
    if keep_last < 1:
        raise ValueError("keep_last must be at least 1")

    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    checked_at = checked_at.astimezone(timezone.utc)
    root = Path(backup_root).expanduser().resolve()

    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    if root.is_dir():
        candidates = sorted(path for path in root.iterdir() if path.is_dir())
    else:
        candidates = []

    for path in candidates:
        manifest_path = path / BACKUP_MANIFEST
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("schema_version") != 1:
                raise ValueError("unsupported backup manifest schema")
            backup_id = manifest.get("backup_id")
            if not isinstance(backup_id, str) or not backup_id.strip():
                raise ValueError("backup_id is missing")
            created_at = _parse_utc(manifest.get("created_at_utc"))
            if created_at > checked_at:
                raise ValueError("backup timestamp is in the future")
            verification = verify_evidence_backup(path)
            if verification["status"] != "verified":
                invalid.append({
                    "backup_id": backup_id,
                    "path": str(path),
                    "reason": "backup_integrity_failed",
                    "issues": verification["issues"],
                })
                continue
            valid.append({
                "backup_id": backup_id,
                "path": str(path),
                "created_at_utc": created_at.isoformat().replace("+00:00", "Z"),
                "age_hours": round((checked_at - created_at).total_seconds() / 3600, 3),
                "files_checked": verification["files_checked"],
            })
        except (OSError, ValueError, TypeError) as exc:
            invalid.append({
                "backup_id": path.name,
                "path": str(path),
                "reason": "backup_manifest_invalid",
                "detail": str(exc),
            })

    valid.sort(key=lambda item: item["created_at_utc"], reverse=True)
    latest_valid = valid[0] if valid else None
    latest_observed_invalid = None
    if invalid:
        # Invalid records are retained as evidence; do not infer their timestamps
        # if their manifests cannot be parsed safely.
        latest_observed_invalid = len(invalid)

    age_limit = timedelta(hours=max_age_hours)
    missed_after = timedelta(hours=expected_interval_hours + grace_hours)
    no_valid_backup = latest_valid is None
    stale = bool(latest_valid and latest_valid["age_hours"] > max_age_hours)
    schedule_missed = bool(latest_valid and latest_valid["age_hours"] > missed_after.total_seconds() / 3600)

    if no_valid_backup or stale or schedule_missed:
        status = "critical"
    elif invalid:
        status = "degraded"
    else:
        status = "ready"

    retained_ids = {item["backup_id"] for item in valid[:keep_last]}
    retention_candidates = [
        {"backup_id": item["backup_id"], "path": item["path"], "reason": "older_than_keep_last"}
        for item in valid[keep_last:]
        if item["backup_id"] not in retained_ids
    ]

    return {
        "status": status,
        "checked_at_utc": checked_at.isoformat().replace("+00:00", "Z"),
        "backup_root_exists": root.is_dir(),
        "valid_backup_count": len(valid),
        "invalid_backup_count": len(invalid),
        "latest_valid_backup": latest_valid,
        "latest_valid_backup_age_limit_hours": max_age_hours,
        "expected_interval_hours": expected_interval_hours,
        "grace_hours": grace_hours,
        "scheduled_backup_overdue": schedule_missed or no_valid_backup,
        "stale_latest_valid_backup": stale,
        "invalid_backups": invalid,
        "retention_policy": {"keep_last": keep_last, "automatic_deletion": False},
        "retention_candidates": retention_candidates,
        "operator_action_required": status != "ready",
        "production_eligible": False,
    }
