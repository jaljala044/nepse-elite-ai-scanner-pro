"""Fail-closed configuration checks for durable bronze evidence storage.

A writable directory is not proof of durability. Production readiness requires
an operator-attested persistent volume and colocated raw-object/catalog paths.
This module never promotes evidence or changes scanner eligibility.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Mapping, Any


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def inspect_evidence_storage(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Inspect storage configuration and perform a non-destructive fsync probe.

    Required environment:
      NEPSE_EVIDENCE_STORAGE_ROOT: persistent mounted volume root
      NEPSE_EVIDENCE_DATABASE: DuckDB catalog path inside that root
      NEPSE_EVIDENCE_RAW_ROOT: immutable raw-object root inside that root
      NEPSE_EVIDENCE_PERSISTENT_VOLUME: explicit operator attestation ('true')

    The attestation is a deployment assertion, not independently verified cloud
    infrastructure metadata. Missing configuration always returns not-ready.
    """
    values = os.environ if env is None else env
    configured = {
        "storage_root": values.get("NEPSE_EVIDENCE_STORAGE_ROOT", "").strip(),
        "database_path": values.get("NEPSE_EVIDENCE_DATABASE", "").strip(),
        "raw_root": values.get("NEPSE_EVIDENCE_RAW_ROOT", "").strip(),
    }
    missing = [key for key, value in configured.items() if not value]
    attested = values.get("NEPSE_EVIDENCE_PERSISTENT_VOLUME", "").strip().lower() == "true"
    result: dict[str, Any] = {
        "status": "not_ready",
        "storage_mode": "unconfigured",
        "configured": {key: bool(value) for key, value in configured.items()},
        "persistent_volume_attested": attested,
        "deployment_persistence_verified": False,
        "atomic_write_probe": "not_run",
        "same_filesystem": None,
        "production_eligible": False,
        "reasons": [],
        "note": (
            "A successful filesystem probe cannot prove that the deployment volume "
            "survives host loss or is backed up. The persistent-volume flag is an "
            "operator attestation and must be independently checked in deployment."
        ),
    }
    if missing:
        result["reasons"].append("missing_configuration:" + ",".join(missing))
    if not attested:
        result["reasons"].append("persistent_volume_not_operator_attested")
    if missing:
        return result

    root = Path(configured["storage_root"]).expanduser().resolve()
    database = Path(configured["database_path"]).expanduser().resolve()
    raw_root = Path(configured["raw_root"]).expanduser().resolve()
    if not _inside(database, root) or not _inside(raw_root, root):
        result["reasons"].append("database_and_raw_root_must_be_inside_storage_root")
        return result

    try:
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise OSError("storage root is not a directory")
        database.parent.mkdir(parents=True, exist_ok=True)
        raw_root.mkdir(parents=True, exist_ok=True)
        root_device = root.stat().st_dev
        same_filesystem = database.parent.stat().st_dev == root_device and raw_root.stat().st_dev == root_device
        result["same_filesystem"] = same_filesystem
        if not same_filesystem:
            result["reasons"].append("catalog_and_raw_objects_must_share_storage_filesystem")
            return result

        fd, probe_name = tempfile.mkstemp(prefix=".nepse-evidence-probe-", dir=root)
        probe = Path(probe_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(b"nepse-evidence-storage-probe-v1")
                stream.flush()
                os.fsync(stream.fileno())
            # Directory fsync makes the create durable on filesystems that
            # implement POSIX directory synchronization.
            if hasattr(os, "O_DIRECTORY"):
                dir_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            result["atomic_write_probe"] = "passed"
        finally:
            try:
                probe.unlink()
                if hasattr(os, "O_DIRECTORY"):
                    dir_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
            except FileNotFoundError:
                pass
    except OSError as exc:
        result["atomic_write_probe"] = "failed"
        result["reasons"].append("storage_probe_failed:" + type(exc).__name__)
        return result

    result.update({
        "status": "configured_operator_attested",
        "storage_mode": "persistent_mounted_volume",
        "atomic_write_probe": "passed",
        "production_eligible": False,
        "reasons": [],
    })
    return result
