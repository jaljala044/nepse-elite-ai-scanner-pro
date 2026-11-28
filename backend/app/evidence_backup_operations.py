"""Read-only backup freshness/retention audit and append-only restore-drill log.

This module recommends retention actions but never deletes backups. It verifies
backup bytes through evidence_backup and hash-chains operator-recorded drills.
All results remain non-production-authorizing.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .evidence_backup import BACKUP_MANIFEST, verify_evidence_backup

GENESIS = "0" * 64


def _utc(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return result.astimezone(timezone.utc)


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp_missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp_timezone_missing")
    return parsed.astimezone(timezone.utc)


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _event_hash(event: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(event)).hexdigest()


def audit_restore_drill_log(log_path: str | Path) -> dict[str, Any]:
    """Verify an append-only, hash-chained restore-drill log without mutation."""
    path = Path(log_path).expanduser()
    result: dict[str, Any] = {
        "status": "missing" if not path.is_file() else "invalid",
        "events_checked": 0,
        "latest_success_at_utc": None,
        "latest_drill_id": None,
        "issues": [],
        "production_eligible": False,
    }
    if not path.is_file():
        result["issues"].append("restore_drill_log_missing")
        return result
    previous = GENESIS
    seen: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                raise ValueError(f"blank_line:{number}")
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError(f"event_not_object:{number}")
            supplied_hash = event.pop("event_sha256", None)
            drill_id = event.get("drill_id")
            if not isinstance(drill_id, str) or not drill_id or drill_id in seen:
                raise ValueError(f"duplicate_or_missing_drill_id:{number}")
            if event.get("previous_event_sha256") != previous:
                raise ValueError(f"chain_link_mismatch:{number}")
            if supplied_hash != _event_hash(event):
                raise ValueError(f"event_hash_mismatch:{number}")
            seen.add(drill_id)
            previous = supplied_hash
            result["events_checked"] += 1
            if event.get("status") == "restore_verified":
                result["latest_success_at_utc"] = event.get("recorded_at_utc")
                result["latest_drill_id"] = drill_id
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["issues"].append(f"restore_drill_log_invalid:{exc}")
        return result
    result["status"] = "verified"
    return result


def record_restore_drill(
    *,
    log_path: str | Path,
    drill_id: str,
    backup_id: str,
    restore_result: Mapping[str, Any],
    recorded_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Append a verified restore result under an inter-process exclusive lock.

    The sidecar lock serializes validation, duplicate detection, chain-head
    selection, and append as one critical section. A partial write or a crash
    still leaves the log fail-closed on the next audit.
    """
    if not drill_id or not backup_id:
        raise ValueError("drill_id and backup_id are required")
    restored_audit = restore_result.get("restored_audit")
    if restore_result.get("status") != "restore_verified" or not isinstance(restored_audit, Mapping) or restored_audit.get("status") != "integrity_ok":
        raise ValueError("only a successful isolated restore with integrity_ok may be recorded")

    path = Path(log_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("restore-drill log must not be a symlink")
    lock_path = path.with_name(path.name + ".lock")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | nofollow, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        # Recheck after acquiring the lock to close the pre-lock path race.
        if path.is_symlink():
            raise ValueError("restore-drill log must not be a symlink")
        current = audit_restore_drill_log(path)
        if current["status"] not in {"verified", "missing"}:
            raise ValueError("restore-drill log is invalid; refusing to append")

        previous = GENESIS
        if path.is_file():
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                if json.loads(line).get("drill_id") == drill_id:
                    raise ValueError("drill_id already exists")
            if lines:
                previous_event = json.loads(lines[-1])
                previous = previous_event["event_sha256"]

        event: dict[str, Any] = {
            "schema_version": 1,
            "drill_id": drill_id,
            "backup_id": backup_id,
            "recorded_at_utc": _utc(recorded_at_utc).isoformat().replace("+00:00", "Z"),
            "status": "restore_verified",
            "restored_audit_status": "integrity_ok",
            "production_eligible": False,
            "previous_event_sha256": previous,
        }
        event["event_sha256"] = _event_hash(event)
        payload = (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | nofollow
        log_fd = os.open(path, flags, 0o600)
        try:
            remaining = memoryview(payload)
            while remaining:
                written = os.write(log_fd, remaining)
                if written <= 0:
                    raise OSError("restore-drill log append made no progress")
                remaining = remaining[written:]
            os.fsync(log_fd)
        finally:
            os.close(log_fd)
        return {
            "status": "restore_drill_recorded",
            "drill_id": drill_id,
            "event_sha256": event["event_sha256"],
            "production_eligible": False,
        }
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def audit_backup_retention(
    *,
    backup_root: str | Path,
    now_utc: datetime | None = None,
    max_backup_age_hours: float = 26,
    minimum_valid_backups: int = 1,
    retain_last: int = 7,
    restore_drill_log: str | Path | None = None,
    max_restore_drill_age_days: float = 90,
    require_restore_drill: bool = True,
) -> dict[str, Any]:
    """Audit backup freshness and report (never execute) retention candidates."""
    if max_backup_age_hours <= 0 or minimum_valid_backups < 1 or retain_last < 1 or max_restore_drill_age_days <= 0:
        raise ValueError("retention thresholds must be positive")
    now = _utc(now_utc)
    root = Path(backup_root).expanduser().resolve()
    report: dict[str, Any] = {
        "status": "attention_required",
        "backup_root_exists": root.is_dir(),
        "backups_checked": 0,
        "valid_backups": [],
        "invalid_backups": [],
        "stale_backup_ids": [],
        "retention_review_candidates": [],
        "issues": [],
        "restore_drill": None,
        "production_eligible": False,
        "deletion_performed": False,
    }
    if not root.is_dir():
        report["issues"].append("backup_root_missing")
    else:
        valid: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for candidate in sorted(root.iterdir()):
            if not candidate.is_dir() or candidate.is_symlink():
                continue
            report["backups_checked"] += 1
            verification = verify_evidence_backup(candidate)
            try:
                manifest = json.loads((candidate / BACKUP_MANIFEST).read_text(encoding="utf-8"))
                backup_id = manifest.get("backup_id")
                created = _parse_timestamp(manifest.get("created_at_utc"))
                if not isinstance(backup_id, str) or not backup_id:
                    raise ValueError("backup_id_missing")
                if backup_id in seen_ids:
                    raise ValueError("duplicate_backup_id")
                seen_ids.add(backup_id)
                age_hours = (now - created).total_seconds() / 3600
                if age_hours < 0:
                    raise ValueError("backup_timestamp_in_future")
                if verification["status"] != "verified":
                    raise ValueError("backup_integrity_invalid")
                item = {"backup_id": backup_id, "created_at_utc": created.isoformat().replace("+00:00", "Z"), "age_hours": round(age_hours, 3), "path": str(candidate)}
                valid.append(item)
                if age_hours > max_backup_age_hours:
                    report["stale_backup_ids"].append(backup_id)
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                report["invalid_backups"].append({"path": str(candidate), "reason": str(exc), "verification": verification})
        valid.sort(key=lambda item: item["created_at_utc"], reverse=True)
        report["valid_backups"] = valid
        if len(valid) < minimum_valid_backups:
            report["issues"].append("insufficient_valid_backups")
        if not valid or valid[0]["age_hours"] > max_backup_age_hours:
            report["issues"].append("latest_valid_backup_stale_or_missing")
        if report["invalid_backups"]:
            report["issues"].append("one_or_more_backups_invalid")
        report["retention_review_candidates"] = [item["backup_id"] for item in valid[retain_last:]]
    if restore_drill_log is not None:
        drill = audit_restore_drill_log(restore_drill_log)
        report["restore_drill"] = drill
        if drill["status"] != "verified":
            if require_restore_drill:
                report["issues"].append("restore_drill_log_unverified")
        elif not drill["latest_success_at_utc"]:
            if require_restore_drill:
                report["issues"].append("no_successful_restore_drill")
        else:
            try:
                drill_age = (now - _parse_timestamp(drill["latest_success_at_utc"])).total_seconds() / 86400
                report["restore_drill"]["age_days"] = round(drill_age, 3)
                if drill_age < 0 or drill_age > max_restore_drill_age_days:
                    report["issues"].append("restore_drill_stale_or_future_dated")
            except ValueError:
                report["issues"].append("restore_drill_timestamp_invalid")
    elif require_restore_drill:
        report["issues"].append("restore_drill_log_not_configured")
    report["status"] = "healthy" if not report["issues"] else "attention_required"
    return report
