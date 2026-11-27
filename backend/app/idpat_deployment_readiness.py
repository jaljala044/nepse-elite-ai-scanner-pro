"""Load deployment-owned IDPAT evidence configuration for API readiness.

The HTTP caller supplies only a decision cutoff. Registry paths, registry hash,
and artifact root are deployment configuration; client JSON cannot attest data.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from app.idpat_trusted_gate_bridge import derive_idpat_gates_from_trusted_store
from app.trusted_artifact_store import TrustedArtifactStore


def load_deployment_idpat_gate_readiness(*, decision_date, decision_time, environ=None):
    env = os.environ if environ is None else environ
    required = (
        "NEPSE_TRUSTED_ARTIFACT_ROOT",
        "NEPSE_TRUSTED_ARTIFACT_REGISTRY",
        "NEPSE_TRUSTED_ARTIFACT_REGISTRY_SHA256",
    )
    missing = [key for key in required if not str(env.get(key, "")).strip()]
    if missing:
        return {
            "status": "blocked",
            "reason": "trusted_artifact_deployment_configuration_missing",
            "missing_configuration": missing,
            "blocked_gates": ["all:trusted_deployment_configuration_unavailable"],
            "gates": {},
            "production_enabled": False,
        }
    try:
        root = Path(env["NEPSE_TRUSTED_ARTIFACT_ROOT"]).resolve()
        registry_path = Path(env["NEPSE_TRUSTED_ARTIFACT_REGISTRY"]).resolve()
        if not root.is_dir():
            raise ValueError("trusted_artifact_root_not_directory")
        if not registry_path.is_file():
            raise ValueError("trusted_artifact_registry_not_file")
        raw = registry_path.read_bytes()
        expected = str(env["NEPSE_TRUSTED_ARTIFACT_REGISTRY_SHA256"]).lower()
        actual = hashlib.sha256(raw).hexdigest()
        if len(expected) != 64 or actual != expected:
            raise ValueError("trusted_artifact_registry_sha256_mismatch")
        registry = json.loads(raw.decode("utf-8"))
        if not isinstance(registry, dict):
            raise ValueError("trusted_artifact_registry_must_be_object")
        store = TrustedArtifactStore(
            root, registry,
            max_age_days=int(env.get("NEPSE_TRUSTED_ARTIFACT_MAX_AGE_DAYS", "7")),
        )
        result = derive_idpat_gates_from_trusted_store(
            store, decision_date=str(decision_date), decision_time=decision_time,
        )
        result["deployment_registry_sha256"] = actual
        result["deployment_configured"] = True
        return result
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "status": "blocked",
            "reason": str(exc) or "trusted_artifact_configuration_invalid",
            "blocked_gates": ["all:trusted_artifact_configuration_invalid"],
            "gates": {},
            "production_enabled": False,
            "deployment_configured": False,
        }
