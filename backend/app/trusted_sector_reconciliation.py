"""Fail-closed bridge from reviewed publisher trust to sector reconciliation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .publisher_trust import (
    assess_publisher_evidence,
    load_evidence_freshness_policy,
    load_publisher_trust_registry,
)
from .sector_evidence_reconciliation import reconcile_sector_evidence


def reconcile_trusted_sector_evidence(
    observations: list[dict[str, Any]],
    *,
    symbols: list[str],
    allowed_sector_codes: set[str],
    as_of_date: str,
    decision_time: str,
    registry_path: str | Path | None,
    freshness_policy_path: str | Path | None,
    hmac_key: str | None,
) -> dict[str, Any]:
    """Reconcile only rows passing reviewed publisher, host and freshness gates.

    This adapter maps reviewed publisher IDs to reviewed ownership-group IDs
    before invoking the legacy reconciler, preventing related publisher brands
    from being counted as independent corroboration.
    """
    registry = load_publisher_trust_registry(
        registry_path, hmac_key, decision_time=decision_time
    )
    freshness = load_evidence_freshness_policy(
        freshness_policy_path, hmac_key, decision_time=decision_time
    )
    assessment = assess_publisher_evidence(
        observations, registry=registry, freshness_policy=freshness,
        decision_time=decision_time,
    )
    accepted = []
    rejected = []
    for index, row in enumerate(observations):
        decision = assessment["observations"][index] if index < len(assessment["observations"]) else {}
        if not decision.get("eligible_for_independence_count"):
            rejected.append({
                "index": index,
                "symbol": row.get("symbol") if isinstance(row, dict) else None,
                "publisher_id": row.get("publisher_id") if isinstance(row, dict) else None,
                "reason": decision.get("independence_status", decision.get("status", "not_assessed")),
            })
            continue
        mapped = dict(row)
        mapped["original_publisher_id"] = mapped.get("publisher_id")
        mapped["publisher_id"] = decision["ownership_group_id"]
        accepted.append(mapped)

    if accepted:
        result = reconcile_sector_evidence(
            accepted, symbols=symbols, allowed_sector_codes=allowed_sector_codes,
            as_of_date=as_of_date, decision_time=decision_time,
        )
    else:
        result = reconcile_sector_evidence(
            [], symbols=symbols, allowed_sector_codes=allowed_sector_codes,
            as_of_date=as_of_date, decision_time=decision_time,
        )
    # Preserve original brand-level publisher labels separately from the
    # reconciler's ownership-group count; never mislabel groups as publishers.
    for symbol, symbol_result in result["results"].items():
        symbol_result["independent_publisher_count"] = 0
        symbol_result["independent_ownership_group_count"] = 0
        groups = set()
        brand_ids = set()
        for row in accepted:
            if str(row.get("symbol", "")).strip().upper() == symbol:
                brand_ids.add(str(row.get("original_publisher_id", "")))
                groups.add(str(row.get("publisher_id", "")))
        symbol_result["independent_ownership_group_count"] = len(groups)
        symbol_result["publisher_brand_count"] = len(brand_ids)
        symbol_result["independent_publisher_count"] = len(groups)
    result["publisher_trust"] = {
        "registry_status": registry["status"],
        "freshness_policy_status": freshness["status"],
        "eligible_observation_count": len(accepted),
        "rejected_observation_count": len(rejected),
        "rejected_observations": rejected,
        "eligible_independent_ownership_group_count": assessment["eligible_independent_ownership_group_count"],
    }
    result["status"] = "review_ready" if (
        result["status"] == "review_ready"
        and registry["status"] == "reviewed_registry_loaded"
        and freshness["status"] == "reviewed_policy_loaded"
    ) else "insufficient_evidence"
    result["verified"] = False
    result["admission_allowed"] = False
    result["production_recommendations_enabled"] = False
    result["limitations"] = list(result.get("limitations", [])) + [
        "Only registry-reviewed publisher identities, approved hosts and explicitly fresh observations are eligible.",
        "Related publisher brands sharing an ownership group count once.",
        "Internal HMAC attestations do not prove legal ownership or official NEPSE membership.",
        "This bridge is research-only and cannot authorize production recommendations.",
    ]
    return result


def publisher_trust_readiness(
    *, registry_path: str | Path | None,
    freshness_policy_path: str | Path | None,
    hmac_key: str | None,
    decision_time: str,
) -> dict[str, Any]:
    registry = load_publisher_trust_registry(
        registry_path, hmac_key, decision_time=decision_time
    )
    freshness = load_evidence_freshness_policy(
        freshness_policy_path, hmac_key, decision_time=decision_time
    )
    ready = registry["status"] == "reviewed_registry_loaded" and freshness["status"] == "reviewed_policy_loaded"
    return {
        "status": "configured_for_research" if ready else "not_configured_or_invalid",
        "publisher_registry_status": registry["status"],
        "freshness_policy_status": freshness["status"],
        "publisher_count": len(registry.get("publishers", {})),
        "freshness_source_class_count": len(freshness.get("max_age_seconds", {})),
        "independence_assessment_allowed": ready,
        "freshness_assessment_allowed": freshness["status"] == "reviewed_policy_loaded",
        "production_admission_allowed": False,
    }
