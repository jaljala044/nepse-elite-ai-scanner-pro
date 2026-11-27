"""Bridge deployment-pinned trusted artifacts into IDPAT's seven gates.

The deployment registry and payload root are server-owned. No request body is
used to attest a gate. Missing or rejected artifacts block their dependent gate.
"""
from __future__ import annotations

from datetime import datetime
from typing import Mapping

from app.idpat_source_evidence import derive_idpat_gate_evidence
from app.trusted_artifact_store import TrustedArtifactStore

GATE_ARTIFACTS = {
    "market": ("market_health", "index_intelligence"),
    "sector": ("sector_rotation",),
    "broker": ("broker_profiles", "broker_sector_rotation"),
    "liquidity": ("ohlcv_quality", "turnover_quality"),
    "execution": ("execution_readiness",),
    "corporate_actions": ("corporate_actions",),
    "source_quality": ("source_quality",),
}
REQUIRED_ARTIFACTS = tuple(dict.fromkeys(
    name for names in GATE_ARTIFACTS.values() for name in names
))


def _aware(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("artifact_available_at_must_be_timezone_aware")
    return parsed


def derive_idpat_gates_from_trusted_store(
    store: TrustedArtifactStore, *, decision_date: str, decision_time: str
) -> dict:
    """Load server-pinned payloads and derive gate evidence without client claims."""
    if not isinstance(store, TrustedArtifactStore):
        raise TypeError("trusted_artifact_store_required")
    artifacts = store.load(
        decision_date=decision_date,
        decision_time=decision_time,
        required_modules=REQUIRED_ARTIFACTS,
    )
    reports, artifact_rejections, lineage = {}, {}, {}
    for gate, names in GATE_ARTIFACTS.items():
        loaded = [artifacts.get(name) for name in names]
        rejected = {}
        for name, item in zip(names, loaded):
            if not isinstance(item, dict):
                rejected[name] = "artifact_missing"
            elif item.get("status") not in {"observed", "research_only", "descriptive_only"}:
                rejected[name] = item.get("rejection_reason", "artifact_not_admitted")
        if rejected:
            artifact_rejections[gate] = rejected
            reports[gate] = {"report_status": "blocked"}
            continue

        source_ids, evidence_ids, available = [], [], []
        payload = {}
        for name, item in zip(names, loaded):
            source_ids.extend(item["source_ids"])
            evidence_ids.extend(item["evidence_ids"])
            available.append(_aware(item["available_at"]))
            data = item.get("data")
            if not isinstance(data, Mapping):
                rejected[name] = "artifact_payload_not_object"
                break
            for key, value in data.items():
                if key in payload and payload[key] != value:
                    rejected[name] = "conflicting_artifact_field:" + key
                    break
                payload[key] = value
            if rejected:
                break
        if rejected:
            artifact_rejections[gate] = rejected
            reports[gate] = {"report_status": "blocked"}
            continue
        source_ids = sorted(set(source_ids))
        evidence_ids = sorted(set(evidence_ids))
        # Composite IDs are deterministic references to the contributing
        # server-pinned IDs; full individual lineage is retained alongside.
        reports[gate] = {
            "report_status": "validated",
            "source_id": "|".join(source_ids),
            "evidence_id": "|".join(evidence_ids),
            "source_ids": source_ids,
            "evidence_ids": evidence_ids,
            "available_at": max(available).isoformat(),
            **payload,
        }
        lineage[gate] = {
            "source_ids": source_ids,
            "evidence_ids": evidence_ids,
            "artifact_modules": list(names),
        }

    result = derive_idpat_gate_evidence(reports, decision_time=decision_time)
    result["artifact_rejections"] = artifact_rejections
    result["lineage"] = lineage
    result["artifact_modules_required"] = list(REQUIRED_ARTIFACTS)
    result["trust_boundary"] = "deployment_registry_and_server_owned_artifact_root"
    result["production_enabled"] = False
    return result
