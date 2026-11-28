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
from .sector_historical_timeline import build_sector_timeline_snapshot


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



def build_evidence_completeness_report(
    *,
    expected_symbols: list[str],
    expected_publisher_ids: list[str],
    observations: list[dict[str, Any]],
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """Compare observed evidence with an explicit operator-supplied expectation set."""
    symbols = [str(value).strip().upper() for value in expected_symbols if str(value).strip()]
    publishers = [str(value).strip() for value in expected_publisher_ids if str(value).strip()]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("expected_symbols_must_be_non_empty_and_unique")
    if len(publishers) != len(set(publishers)):
        raise ValueError("expected_publisher_ids_must_be_unique")
    eligible_indices = {
        row.get("index") for row in assessment.get("observations", [])
        if row.get("eligible_for_independence_count")
    }
    observed_by_symbol = {symbol: 0 for symbol in symbols}
    observed_by_publisher = {publisher: 0 for publisher in publishers}
    for index, row in enumerate(observations):
        if index not in eligible_indices or not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        publisher = str(row.get("publisher_id", "")).strip()
        if symbol in observed_by_symbol:
            observed_by_symbol[symbol] += 1
        if publisher in observed_by_publisher:
            observed_by_publisher[publisher] += 1
    missing_symbols = sorted(symbol for symbol, count in observed_by_symbol.items() if count == 0)
    missing_publishers = sorted(publisher for publisher, count in observed_by_publisher.items() if count == 0)
    symbol_coverage = (len(symbols) - len(missing_symbols)) / len(symbols)
    publisher_coverage = (
        (len(publishers) - len(missing_publishers)) / len(publishers)
        if publishers else None
    )
    return {
        "status": "complete" if not missing_symbols and not missing_publishers else "incomplete",
        "expected_symbol_count": len(symbols),
        "observed_symbol_count": len(symbols) - len(missing_symbols),
        "missing_symbols": missing_symbols,
        "symbol_coverage_pct": round(symbol_coverage * 100, 2),
        "expected_publisher_count": len(publishers),
        "observed_publisher_count": len(publishers) - len(missing_publishers),
        "missing_publishers": missing_publishers,
        "publisher_coverage_pct": round(publisher_coverage * 100, 2) if publisher_coverage is not None else None,
        "eligible_observation_count": len(eligible_indices),
        "expectation_set_provenance": "operator_supplied_not_exchange_verified",
        "production_admission_allowed": False,
    }



def replay_trusted_sector_timeline(
    events: list[dict[str, Any]],
    *,
    as_of_date: str,
    decision_time: str,
    allowed_sector_codes: set[str],
    known_security_ids: set[str],
    registry_path: str | Path | None,
    freshness_policy_path: str | Path | None,
    hmac_key: str | None,
) -> dict[str, Any]:
    """Replay only timeline events passing point-in-time publisher and freshness gates.

    Missing source_url is intentionally rejected: a publisher label without a
    host that can be matched to the reviewed registry is not trusted evidence.
    The registry and policy are loaded at decision_time, so future versions are
    rejected by their loaders rather than applied retroactively.
    """
    registry = load_publisher_trust_registry(
        registry_path, hmac_key, decision_time=decision_time
    )
    freshness = load_evidence_freshness_policy(
        freshness_policy_path, hmac_key, decision_time=decision_time
    )
    observations = []
    valid_event_indexes = []
    rejected = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            rejected.append({"index": index, "reason": "event_not_object"})
            continue
        source_url = event.get("source_url")
        if not isinstance(source_url, str) or not source_url.strip():
            rejected.append({"index": index, "event_id": event.get("event_id"),
                             "reason": "source_url_missing_host_unverifiable"})
            continue
        observations.append({
            "publisher_id": event.get("publisher_id"),
            "source_url": source_url,
            "source_class": event.get("source_class"),
            "captured_at": event.get("captured_at"),
        })
        valid_event_indexes.append(index)
    assessment = assess_publisher_evidence(
        observations, registry=registry, freshness_policy=freshness,
        decision_time=decision_time,
    )
    accepted_events = []
    for assessment_row, event_index in zip(assessment["observations"], valid_event_indexes):
        event = dict(events[event_index])
        if not assessment_row.get("eligible_for_independence_count"):
            rejected.append({
                "index": event_index, "event_id": event.get("event_id"),
                "reason": assessment_row.get("independence_status", "not_eligible"),
                "freshness_status": assessment_row.get("freshness_status"),
                "approved_host_match": assessment_row.get("approved_host_match", False),
            })
            continue
        # Timeline corroboration counts independently reviewed ownership groups,
        # not multiple brands operated by the same group.
        event["publisher_id"] = assessment_row["ownership_group_id"]
        accepted_events.append(event)
    result = build_sector_timeline_snapshot(
        accepted_events, as_of_date=as_of_date, decision_time=decision_time,
        allowed_sector_codes=allowed_sector_codes,
        known_security_ids=known_security_ids,
    )
    result["publisher_trust_replay"] = {
        "registry_status": registry["status"],
        "registry_sha256": registry.get("registry_sha256"),
        "registry_generated_at": registry.get("generated_at"),
        "freshness_policy_status": freshness["status"],
        "freshness_policy_sha256": freshness.get("policy_sha256"),
        "freshness_policy_generated_at": freshness.get("generated_at"),
        "input_event_count": len(events),
        "eligible_event_count": len(accepted_events),
        "rejected_event_count": len(rejected),
        "rejected_events": rejected,
        "eligible_ownership_group_count": assessment["eligible_independent_ownership_group_count"],
    }
    configured = registry["status"] == "reviewed_registry_loaded" and freshness["status"] == "reviewed_policy_loaded"
    result["status"] = result["status"] if configured else "insufficient_evidence"
    result["verified"] = False
    result["admission_allowed"] = False
    result["production_admission_allowed"] = False
    result["limitations"] = list(result.get("limitations", [])) + [
        "Historical trust replay uses the reviewed registry and freshness policy visible at decision_time.",
        "Events without source_url are excluded because publisher hostname cannot be independently matched.",
        "This research replay does not establish legal ownership or official NEPSE membership.",
    ]
    return result


def build_historical_trust_version_report(
    *,
    registry_path: str | Path | None,
    freshness_policy_path: str | Path | None,
    hmac_key: str | None,
    decision_times: list[str],
    versioned_registry_paths: dict[str, str | Path] | None = None,
    versioned_freshness_policy_paths: dict[str, str | Path] | None = None,
) -> dict[str, Any]:
    """Report signed registry/policy versions selected for each historical cutoff.

    Explicit maps bind an exact decision_time string to an archived server-owned
    snapshot path. No filesystem discovery or client-provided paths are used.
    """
    if not isinstance(decision_times, list) or not decision_times:
        raise ValueError("decision_times_must_be_non_empty_list")
    rows = []
    for cutoff in decision_times:
        selected_registry_path = (versioned_registry_paths or {}).get(cutoff, registry_path)
        selected_policy_path = (versioned_freshness_policy_paths or {}).get(cutoff, freshness_policy_path)
        registry = load_publisher_trust_registry(
            selected_registry_path, hmac_key, decision_time=cutoff
        )
        policy = load_evidence_freshness_policy(
            selected_policy_path, hmac_key, decision_time=cutoff
        )
        rows.append({
            "decision_time": cutoff,
            "registry_status": registry["status"],
            "registry_sha256": registry.get("registry_sha256"),
            "registry_generated_at": registry.get("generated_at"),
            "publisher_ownership_groups": {key: value["ownership_group_id"] for key, value in registry.get("publishers", {}).items()},
            "freshness_policy_status": policy["status"],
            "freshness_policy_sha256": policy.get("policy_sha256"),
            "freshness_policy_generated_at": policy.get("generated_at"),
            "historical_replay_eligible": (
                registry["status"] == "reviewed_registry_loaded"
                and policy["status"] == "reviewed_policy_loaded"
            ),
        })
    identity_changes = []
    previous = None
    for row in rows:
        current = row["publisher_ownership_groups"]
        if previous is not None:
            for publisher_id in sorted(set(previous) | set(current)):
                if previous.get(publisher_id) != current.get(publisher_id):
                    identity_changes.append({
                        "decision_time": row["decision_time"],
                        "publisher_id": publisher_id,
                        "previous_ownership_group_id": previous.get(publisher_id),
                        "current_ownership_group_id": current.get(publisher_id),
                        "status": "review_required_identity_change",
                    })
        previous = current
    return {
        "status": "assessed",
        "cutoff_count": len(rows),
        "publisher_identity_changes": identity_changes,
        "versions": rows,
        "version_selection_mode": "explicit_cutoff_to_server_owned_snapshot_path_with_default_fallback",
        "historical_archive_search_supported": False,
        "explicit_version_map_supported": True,
        "production_admission_allowed": False,
        "limitations": [
            "Historical versions must be explicitly mapped to exact decision-time cutoffs by server-side configuration; automatic archive discovery is not implemented.",
            "A snapshot generated after a historical decision cutoff is rejected, not backfilled.",
        ],
    }



def build_sector_evidence_coverage_report(
    *,
    expected_symbols_by_sector: dict[str, list[str]],
    expected_capture_sessions: list[str],
    observations: list[dict[str, Any]],
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """Report per-sector symbol coverage and missing source-capture sessions."""
    if not isinstance(expected_symbols_by_sector, dict) or not expected_symbols_by_sector:
        raise ValueError("expected_symbols_by_sector_required")
    if not isinstance(expected_capture_sessions, list) or not expected_capture_sessions:
        raise ValueError("expected_capture_sessions_required")
    eligible = {
        row.get("index") for row in assessment.get("observations", [])
        if row.get("eligible_for_independence_count")
    }
    normalized: dict[str, set[str]] = {}
    for sector, symbols in expected_symbols_by_sector.items():
        if not isinstance(sector, str) or not sector.strip() or not isinstance(symbols, list) or not symbols:
            raise ValueError("sector_expectation_invalid")
        normalized[sector] = {str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()}
        if not normalized[sector]:
            raise ValueError("sector_symbols_required")
    observed: dict[str, set[str]] = {sector: set() for sector in normalized}
    sessions = set()
    for index, row in enumerate(observations):
        if index not in eligible or not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        sector = str(row.get("sector_code", "")).strip()
        if sector in normalized and symbol in normalized[sector]:
            observed[sector].add(symbol)
        captured = row.get("captured_at")
        if isinstance(captured, str) and len(captured) >= 10:
            sessions.add(captured[:10])
    sectors = {}
    for sector, expected in normalized.items():
        missing = sorted(expected - observed[sector])
        sectors[sector] = {
            "expected_symbol_count": len(expected),
            "observed_symbol_count": len(expected & observed[sector]),
            "missing_symbols": missing,
            "coverage_pct": round(100 * len(expected & observed[sector]) / len(expected), 2),
            "status": "complete" if not missing else "incomplete",
        }
    missing_sessions = sorted(set(expected_capture_sessions) - sessions)
    return {
        "status": "complete" if not missing_sessions and all(x["status"] == "complete" for x in sectors.values()) else "incomplete",
        "sector_coverage": sectors,
        "expected_capture_sessions": sorted(set(expected_capture_sessions)),
        "observed_capture_sessions": sorted(sessions),
        "missing_capture_sessions": missing_sessions,
        "capture_session_coverage_pct": round(
            100 * (len(set(expected_capture_sessions)) - len(missing_sessions)) / len(set(expected_capture_sessions)), 2
        ),
        "expectations_provenance": "operator_supplied_not_exchange_verified",
        "production_admission_allowed": False,
    }
