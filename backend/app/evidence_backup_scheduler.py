"""Scheduled backup runner and receipt monitor.

Scheduling is external (systemd timer/cron). This runner serializes execution,
runs explicit writer-quiesce/resume hooks without a shell, invokes the existing
verified backup CLI, and appends hash-chained receipts. It does not establish
that hooks truly stop every writer or survive SIGKILL/host failure.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

GENESIS = "0" * 64


def _utc(value: datetime | None = None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return result.astimezone(timezone.utc)


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_argv(name: str, value: Any, *, optional: bool = False) -> list[str] | None:
    if optional and value in (None, []):
        return None
    if not isinstance(value, list) or not value or any(not isinstance(part, str) or not part for part in value):
        raise ValueError(f"{name} must be a non-empty string argument array")
    executable = Path(value[0])
    if not executable.is_absolute():
        raise ValueError(f"{name} executable must be an absolute path")
    return value


def _append_receipt(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    previous = GENESIS
    if path.exists() and path.stat().st_size:
        audit = audit_backup_schedule(path)
        if audit["status"] != "verified":
            raise ValueError("backup receipt ledger invalid; refusing append")
        previous = audit["latest_event_sha256"]
    event["previous_event_sha256"] = previous
    event["event_sha256"] = _hash(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event


def audit_backup_schedule(
    receipt_path: str | Path,
    *,
    now_utc: datetime | None = None,
    expected_interval_hours: float = 26,
    grace_hours: float = 2,
) -> dict[str, Any]:
    """Verify receipt chain and detect missing, failed, or overdue backup runs."""
    if expected_interval_hours <= 0 or grace_hours < 0:
        raise ValueError("schedule interval must be positive and grace non-negative")
    now = _utc(now_utc)
    path = Path(receipt_path).expanduser()
    result: dict[str, Any] = {
        "status": "attention_required",
        "events_checked": 0,
        "latest_event_sha256": GENESIS,
        "latest_success_at_utc": None,
        "latest_run_status": None,
        "latest_run_id": None,
        "age_hours": None,
        "issues": [],
        "production_eligible": False,
    }
    if not path.is_file():
        result["issues"].append("backup_receipt_ledger_missing")
        return result
    previous = GENESIS
    try:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise ValueError(f"blank_line:{number}")
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError(f"event_not_object:{number}")
            supplied = event.pop("event_sha256", None)
            if event.get("previous_event_sha256") != previous or supplied != _hash(event):
                raise ValueError(f"receipt_chain_or_hash_mismatch:{number}")
            previous = supplied
            result["events_checked"] += 1
            result["latest_run_status"] = event.get("status")
            result["latest_run_id"] = event.get("run_id")
            if event.get("status") == "backup_verified":
                result["latest_success_at_utc"] = event.get("finished_at_utc")
            result["latest_event_sha256"] = supplied
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["issues"].append(f"backup_receipt_ledger_invalid:{exc}")
        return result
    if not result["events_checked"]:
        result["issues"].append("backup_receipt_ledger_empty")
        return result
    if result["latest_run_status"] != "backup_verified":
        result["issues"].append("latest_backup_run_failed")
    if not result["latest_success_at_utc"]:
        result["issues"].append("no_successful_backup_receipt")
    else:
        try:
            finished = datetime.fromisoformat(result["latest_success_at_utc"].replace("Z", "+00:00"))
            if finished.tzinfo is None or finished.utcoffset() is None:
                raise ValueError("timestamp_timezone_missing")
            age = (now - finished.astimezone(timezone.utc)).total_seconds() / 3600
            result["age_hours"] = round(age, 3)
            if age < 0:
                result["issues"].append("latest_backup_receipt_future_dated")
            elif age > expected_interval_hours + grace_hours:
                result["issues"].append("scheduled_backup_overdue")
        except (ValueError, AttributeError):
            result["issues"].append("latest_backup_receipt_timestamp_invalid")
    result["status"] = "healthy" if not result["issues"] else "attention_required"
    return result


def run_scheduled_backup(
    *,
    config: Mapping[str, Any],
    receipt_path: str | Path,
    lock_path: str | Path,
    run_id: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Run pre-hook, verified backup command, and resume hook under an OS lock."""
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id is required")
    pre = _validate_argv("quiesce_argv", config.get("quiesce_argv"))
    backup = _validate_argv("backup_argv", config.get("backup_argv"))
    resume = _validate_argv("resume_argv", config.get("resume_argv"))
    timeout = config.get("command_timeout_seconds", 1800)
    if not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("command_timeout_seconds must be a positive integer")
    receipt = Path(receipt_path).expanduser()
    lock = Path(lock_path).expanduser()
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    started = _utc(now_utc)
    status = "backup_failed"
    issue: str | None = None
    backup_report: dict[str, Any] | None = None
    output_digest: str | None = None
    pre_ok = False
    resume_ok = False
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another scheduled backup is already running") from exc
        try:
            pre_result = subprocess.run(pre, capture_output=True, text=True, timeout=timeout, check=False)
            if pre_result.returncode != 0:
                issue = f"writer_quiesce_failed:{pre_result.returncode}"
            else:
                pre_ok = True
                backup_result = subprocess.run(backup, capture_output=True, text=True, timeout=timeout, check=False)
                output_digest = hashlib.sha256(backup_result.stdout.encode("utf-8")).hexdigest()
                try:
                    backup_report = json.loads(backup_result.stdout)
                except (ValueError, TypeError):
                    backup_report = None
                if backup_result.returncode == 0 and isinstance(backup_report, dict) and backup_report.get("status") == "backup_verified" and backup_report.get("verification", {}).get("status") == "verified":
                    status = "backup_verified"
                else:
                    issue = f"backup_command_failed_or_unverified:{backup_result.returncode}"
        except subprocess.TimeoutExpired:
            issue = "backup_operation_timeout"
        except OSError as exc:
            issue = f"backup_command_start_failed:{type(exc).__name__}"
        finally:
            if pre_ok:
                try:
                    resume_result = subprocess.run(resume, capture_output=True, text=True, timeout=timeout, check=False)
                    resume_ok = resume_result.returncode == 0
                    if not resume_ok:
                        status = "backup_failed"
                        issue = f"writer_resume_failed:{resume_result.returncode}"
                except (subprocess.TimeoutExpired, OSError) as exc:
                    status = "backup_failed"
                    issue = f"writer_resume_failed:{type(exc).__name__}"
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)
    finished = _utc()
    event = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at_utc": started.isoformat().replace("+00:00", "Z"),
        "finished_at_utc": finished.isoformat().replace("+00:00", "Z"),
        "status": status,
        "quiesce_succeeded": pre_ok,
        "resume_succeeded": resume_ok if pre_ok else None,
        "backup_stdout_sha256": output_digest,
        "issue": issue,
        "production_eligible": False,
    }
    try:
        _append_receipt(receipt, event)
    except Exception as exc:
        return {"status": "receipt_write_failed", "issue": str(exc), "backup_status": status, "production_eligible": False}
    return {"status": status, "run_id": run_id, "issue": issue, "receipt_sha256": event["event_sha256"], "production_eligible": False}
