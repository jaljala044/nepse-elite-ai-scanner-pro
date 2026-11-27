"""Deployment-pinned broker dashboard adapter.

Request bodies carry only a decision cutoff. Evidence payloads and registry
entries are loaded from deployment-owned storage and are never caller supplied.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .broker_intelligence_dashboard import build_broker_intelligence_dashboard
from .trusted_artifact_store import TrustedArtifactError, TrustedArtifactStore

REQUIRED_BROKER_MODULES = (
    "market_health",
    "index_intelligence",
    "sector_rotation",
    "broker_profiles",
    "broker_sector_rotation",
)


def build_trusted_broker_dashboard(
    store: TrustedArtifactStore, *, decision_date: str, decision_time: str,
) -> dict:
    """Compose dashboard only from deployment-pinned, hash-verified artifacts."""
    artifacts = store.load(
        decision_date=decision_date,
        decision_time=decision_time,
        required_modules=REQUIRED_BROKER_MODULES,
    )
    missing = [
        name for name in REQUIRED_BROKER_MODULES
        if artifacts.get(name, {}).get("evidence_gate_passed") is not True
    ]
    if missing:
        return {
            "status": "insufficient_evidence",
            "dashboard": None,
            "missing_modules": missing,
            "trusted_inputs": {
                name: {
                    "status": artifacts.get(name, {}).get("status", "unavailable"),
                    "reason": artifacts.get(name, {}).get("rejection_reason", "artifact_missing"),
                }
                for name in missing
            },
            "production_recommendations_enabled": False,
            "signals_enabled": False,
            "trade_actions_enabled": False,
        }

    # A multi-source broker/market join is meaningful only when every
    # admitted input describes the same exchange session and calendar.
    as_of_dates = {artifacts[name]["as_of_date"] for name in REQUIRED_BROKER_MODULES}
    if as_of_dates != {decision_date}:
        raise TrustedArtifactError("trusted_artifacts_as_of_date_mismatch")
    calendar_ids = {
        artifacts[name]["quality_context"].get("session_calendar_id")
        for name in REQUIRED_BROKER_MODULES
    }
    if len(calendar_ids) != 1 or not all(
        isinstance(value, str) and value.strip() for value in calendar_ids
    ):
        raise TrustedArtifactError("trusted_artifacts_session_calendar_mismatch")

    broker = artifacts["broker_profiles"]
    broker_data = broker["data"]
    rolling_profiles = broker_data.get("rolling_profiles")
    if not isinstance(rolling_profiles, dict):
        raise TrustedArtifactError("broker_profiles_payload_missing_rolling_profiles")
    rotations_data = artifacts["broker_sector_rotation"]["data"]
    rotations = rotations_data.get("sector_rotation_by_window", {})
    if not isinstance(rotations, dict):
        raise TrustedArtifactError("broker_sector_rotation_windows_must_be_object")
    candidates = broker_data.get("candidates", [])
    if not isinstance(candidates, list):
        raise TrustedArtifactError("broker_profiles_candidates_must_be_list")

    source_manifest = {
        "status": "verified",
        "source_ids": broker["source_ids"],
        "coverage": str(broker["coverage_ratio"]),
        "available_at": broker["available_at"],
    }
    dashboard = build_broker_intelligence_dashboard(
        as_of_date=decision_date,
        as_of_timestamp=decision_time,
        rolling_profiles=rolling_profiles,
        source_manifest=source_manifest,
        sector_rotation_by_window=rotations,
        candidates=candidates,
    )
    trusted_inputs = {
        name: {
            "status": artifacts[name]["status"],
            "as_of_date": artifacts[name]["as_of_date"],
            "available_at": artifacts[name]["available_at"],
            "source_ids": artifacts[name]["source_ids"],
            "evidence_ids": artifacts[name]["evidence_ids"],
            "coverage_ratio": artifacts[name]["coverage_ratio"],
            "quality_context": artifacts[name]["quality_context"],
        }
        for name in REQUIRED_BROKER_MODULES
    }
    return {
        "status": dashboard["status"],
        "dashboard": dashboard,
        "trusted_inputs": trusted_inputs,
        "market_context": {
            name: artifacts[name]["data"]
            for name in ("market_health", "index_intelligence", "sector_rotation")
        },
        "production_recommendations_enabled": False,
        "signals_enabled": False,
        "trade_actions_enabled": False,
        "interpretation_boundary": (
            "Broker codes are execution-channel identifiers, not beneficial owners. "
            "This endpoint is descriptive research only and does not infer intent."
        ),
    }


def load_deployment_broker_dashboard(*, decision_date: str, decision_time: str) -> dict:
    """Load a registry whose path is fixed by deployment environment, not request data."""
    root_value = os.environ.get("NEPSE_TRUSTED_ARTIFACT_ROOT")
    registry_value = os.environ.get("NEPSE_TRUSTED_ARTIFACT_REGISTRY_PATH")
    if not root_value or not registry_value:
        raise TrustedArtifactError("trusted_broker_artifact_store_not_configured")
    root = Path(root_value).resolve()
    registry_path = Path(registry_value).resolve()
    # The registry is part of the private artifact store. Resolve symlinks
    # before checking containment so a deployment misconfiguration cannot
    # silently load a registry from outside the protected mount.
    try:
        registry_path.relative_to(root)
    except ValueError:
        raise TrustedArtifactError("trusted_broker_registry_path_escapes_store") from None
    if not registry_path.is_file():
        raise TrustedArtifactError("trusted_broker_registry_unavailable")
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise TrustedArtifactError("trusted_broker_registry_invalid") from None
    if not isinstance(registry, dict):
        raise TrustedArtifactError("trusted_broker_registry_must_be_object")
    max_age_raw = os.environ.get("NEPSE_TRUSTED_ARTIFACT_MAX_AGE_DAYS", "7")
    try:
        max_age_days = int(max_age_raw)
    except (TypeError, ValueError):
        raise TrustedArtifactError("trusted_artifact_max_age_days_invalid") from None
    store = TrustedArtifactStore(root, registry, max_age_days=max_age_days)
    return build_trusted_broker_dashboard(
        store, decision_date=decision_date, decision_time=decision_time,
    )
