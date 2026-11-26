"""Operational readiness diagnostics for the canonical evidence path.

Secrets are read only from deployment environment configuration and are never
returned. This module reports readiness; it does not enable trading or scoring.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from .canonical_evidence import load_canonical_evidence_records
from .source_trust_registry import verify_promotion_ledger, verify_source_registry


def _reviewer_keys(raw: str | None) -> dict[str, bytes]:
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("reviewer key configuration is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError("reviewer key configuration must be an object")
    result = {}
    for reviewer, value in decoded.items():
        if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(value, str):
            raise ValueError("reviewer key entries must map reviewer IDs to hex strings")
        try:
            key = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("reviewer key must be hex encoded") from exc
        if len(key) < 32:
            raise ValueError("reviewer HMAC keys must contain at least 32 bytes")
        result[reviewer] = key
    return result


def build_evidence_readiness(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Inspect config and canonical evidence without creating or mutating stores."""
    env = os.environ if environ is None else environ
    missing: list[str] = []
    blockers: list[str] = []

    registry_path = Path(env["NEPSE_SOURCE_REGISTRY_PATH"]) if env.get("NEPSE_SOURCE_REGISTRY_PATH") else None
    pinned_digest = env.get("NEPSE_SOURCE_REGISTRY_SHA256")
    ledger_path = Path(env.get(
        "NEPSE_PROMOTION_LEDGER_PATH",
        str(Path(__file__).resolve().parents[1] / "data" / "promotion-ledger.jsonl"),
    ))
    database_path = Path(env.get(
        "NEPSE_EVIDENCE_DATABASE",
        str(Path(__file__).resolve().parents[1] / "data" / "evidence.duckdb"),
    ))

    registry = None
    registry_valid = False
    if registry_path is None:
        missing.append("source_registry_path")
    elif not registry_path.is_file():
        missing.append("source_registry_file")
    elif not pinned_digest:
        missing.append("pinned_source_registry_sha256")
    else:
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
                blockers.append("source_registry_invalid")
                registry = None
            else:
                registry_valid = verify_source_registry(registry, pinned_digest)
                if not registry_valid:
                    blockers.append("source_registry_digest_mismatch")
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            blockers.append("source_registry_invalid")

    try:
        keys = _reviewer_keys(env.get("NEPSE_REVIEWER_KEYS_JSON"))
    except ValueError:
        keys = {}
        blockers.append("reviewer_key_configuration_invalid")
    if not keys:
        missing.append("reviewer_keys")

    try:
        ledger = verify_promotion_ledger(ledger_path)
    except (OSError, UnicodeDecodeError, ValueError):
        ledger = {"valid": False, "events": [], "errors": ["ledger_read_failed"]}
    if not ledger["valid"]:
        blockers.append("promotion_ledger_integrity_failure")
    if not ledger_path.is_file():
        missing.append("promotion_ledger_file")

    evidence_store_exists = database_path.is_file()
    if not evidence_store_exists:
        missing.append("evidence_database")

    source_count = len(registry.get("sources", [])) if isinstance(registry, dict) else 0
    active_policies = [
        item for item in (registry or {}).get("sources", [])
        if isinstance(item, dict) and item.get("status") == "active"
    ]
    canonical_policy_count = sum(
        bool(item.get("canonical_record_types")) for item in active_policies
    )
    if canonical_policy_count == 0:
        missing.append("active_canonical_source_policy")

    canonical_count = 0
    canonical_status = "not_configured"
    if (
        registry_valid and keys and evidence_store_exists
        and ledger["valid"] and canonical_policy_count > 0
    ):
        try:
            result = load_canonical_evidence_records(
                database_path=database_path,
                ledger_path=ledger_path,
                registry=registry,
                trusted_registry_sha256=pinned_digest,
                reviewer_keys=keys,
            )
            canonical_count = result["promoted_record_count"]
            canonical_status = "ready_for_internal_read" if canonical_count else "no_promoted_records"
            if not canonical_count:
                missing.append("accepted_canonical_promotions")
        except (OSError, ValueError, TypeError, KeyError):
            canonical_status = "blocked"
            blockers.append("canonical_evidence_verification_failed")

    if blockers:
        status = "blocked"
    elif canonical_status == "ready_for_internal_read":
        status = "ready_for_internal_read"
    elif not missing:
        status = "no_promoted_records"
    else:
        status = "not_configured"

    return {
        "status": status,
        "canonical_read_status": canonical_status,
        "source_registry_configured": registry_path is not None and registry_path.is_file(),
        "source_registry_valid": registry_valid,
        "source_policy_count": source_count,
        "active_source_policy_count": len(active_policies),
        "active_canonical_source_policy_count": canonical_policy_count,
        "reviewer_key_count": len(keys),
        "promotion_ledger_exists": ledger_path.is_file(),
        "promotion_ledger_valid": ledger["valid"],
        "promotion_event_count": len(ledger["events"]),
        "evidence_store_exists": evidence_store_exists,
        "canonical_record_count": canonical_count,
        "missing_requirements": sorted(set(missing)),
        "blockers": sorted(set(blockers)),
        "production_eligible": False,
        "production_blockers": [
            "canonical_evidence_not_connected_to_scanner_or_market_health_consumers",
            "production_data_source_activation_requires_separate_review",
        ],
    }
