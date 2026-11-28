"""Source coverage and evidence gates for a bounded NEPSE historical pilot.

Provider names are candidates, not assertions of authority or live connectivity.
No endpoint is guessed and no network request is made by this module.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from app.historical_pilot_source_contract import validate_historical_source_contract

PROVIDER_CATALOG = {
    "nepse_official": {"name": "NEPSE Official", "role": "official_primary", "authority": "exchange"},
    "cdsc": {"name": "CDSC", "role": "official_primary", "authority": "depository"},
    "sharesansar": {"name": "ShareSansar", "role": "corroborative_third_party", "authority": "third_party"},
    "chukul": {"name": "Chukul", "role": "corroborative_third_party", "authority": "third_party"},
    "sharehub_nepal": {"name": "ShareHub Nepal", "role": "corroborative_third_party", "authority": "third_party"},
    "punji": {"name": "Punji", "role": "identity_review_required", "authority": "unverified"},
    "merolagani": {"name": "Merolagani", "role": "corroborative_third_party", "authority": "third_party"},
    "nepsealpha": {"name": "NepseAlpha", "role": "corroborative_third_party", "authority": "third_party"},
    "chartnepali": {"name": "ChartNepali", "role": "corroborative_third_party", "authority": "third_party"},
    "bullhouse": {"name": "Bullhouse Investment", "role": "corroborative_third_party", "authority": "third_party"},
}
_HEX_64 = re.compile(r"^[a-fA-F0-9]{64}$")


def audit_nepse_source_coverage(*, source_contracts: list[Mapping[str, Any]], decision_cutoff: str,
                                required_third_party_count: int = 2) -> dict:
    """Validate explicit provider contracts and identify gaps without inventing endpoints."""
    issues: list[dict[str, Any]] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for index, contract in enumerate(source_contracts):
        if not isinstance(contract, Mapping):
            issues.append({"reason": "source_contract_not_mapping", "index": index})
            continue
        source_id = str(contract.get("source_id", "")).strip()
        if source_id not in PROVIDER_CATALOG:
            issues.append({"reason": "provider_not_in_reviewed_catalog", "index": index, "source_id": source_id or None})
            continue
        if source_id in by_id:
            issues.append({"reason": "duplicate_provider_contract", "source_id": source_id})
            continue
        by_id[source_id] = contract

    provider_status = []
    approved_official = set()
    approved_third_party = set()
    for source_id, provider in PROVIDER_CATALOG.items():
        contract = by_id.get(source_id)
        if contract is None:
            provider_status.append({"source_id": source_id, **provider, "status": "NOT_CONFIGURED", "capture_allowed": False})
            continue
        identity_reviewed = contract.get("publisher_identity_reviewed") is True
        if source_id == "punji" and not identity_reviewed:
            provider_status.append({"source_id": source_id, **provider, "status": "IDENTITY_REVIEW_REQUIRED", "capture_allowed": False})
            continue
        checked = validate_historical_source_contract(contract=contract, decision_cutoff=decision_cutoff)
        approved = checked.get("capture_allowed") is True and identity_reviewed
        status = "APPROVED_FOR_CAPTURE" if approved else "CONTRACT_BLOCKED"
        provider_status.append({
            "source_id": source_id, **provider, "status": status,
            "capture_allowed": approved, "contract_errors": checked.get("errors", []),
            "dataset_kind": checked.get("dataset_kind"),
        })
        if approved and provider["role"] == "official_primary":
            approved_official.add(source_id)
        elif approved and provider["role"] == "corroborative_third_party":
            approved_third_party.add(source_id)

    if not approved_official:
        issues.append({"reason": "no_approved_official_primary_source"})
    if "nepse_official" not in approved_official:
        issues.append({"reason": "nepse_official_contract_not_approved"})
    if "cdsc" not in approved_official:
        issues.append({"reason": "cdsc_contract_not_approved"})
    if len(approved_third_party) < required_third_party_count:
        issues.append({"reason": "insufficient_independent_third_party_contracts",
                       "required": required_third_party_count, "approved": len(approved_third_party)})
    status = "SOURCE_COVERAGE_READY" if not issues else "SOURCE_COVERAGE_BLOCKED"
    canonical = json.dumps({"providers": provider_status, "issues": issues}, sort_keys=True, separators=(",", ":"))
    return {
        "status": status, "providers": provider_status, "issues": issues,
        "approved_official_sources": sorted(approved_official),
        "approved_third_party_sources": sorted(approved_third_party),
        "required_cross_check_candidates": ["sharesansar", "chukul", "sharehub_nepal", "punji"],
        "network_access_performed": False, "endpoints_invented": False,
        "publisher_authenticity_proven": False, "exchange_completeness_proven": False,
        "coverage_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "limitations": [
            "Catalog entries are source candidates only; no provider is authenticated by its name.",
            "Each endpoint, publisher identity, licence, access policy and capture contract requires human review.",
            "Punji publisher/legal identity must be confirmed before it can count as an independent source.",
            "Third-party records corroborate but do not replace NEPSE/CDSC primary evidence.",
        ],
    }


def evaluate_historical_pilot_evidence(*, source_coverage: Mapping[str, Any],
                                       capture_evidence: list[Mapping[str, Any]],
                                       reconciliation: Mapping[str, Any],
                                       calendar_evidence: Mapping[str, Any],
                                       universe_evidence: Mapping[str, Any]) -> dict:
    """Fail-closed gate for a bounded panel; only real, hashed capture evidence qualifies."""
    issues: list[dict[str, Any]] = []
    if source_coverage.get("status") != "SOURCE_COVERAGE_READY":
        issues.append({"reason": "source_coverage_not_ready"})
    seen_capture_ids = set()
    seen_source_ids = set()
    valid_capture_count = 0
    for index, item in enumerate(capture_evidence):
        if not isinstance(item, Mapping):
            issues.append({"reason": "capture_evidence_not_mapping", "index": index})
            continue
        capture_id = str(item.get("capture_id", "")).strip()
        source_id = str(item.get("source_id", "")).strip()
        if not capture_id or capture_id in seen_capture_ids:
            issues.append({"reason": "capture_id_missing_or_duplicate", "index": index})
        seen_capture_ids.add(capture_id)
        if not source_id or source_id in seen_source_ids:
            issues.append({"reason": "source_capture_missing_or_duplicate", "index": index})
        seen_source_ids.add(source_id)
        digest = str(item.get("raw_payload_sha256", ""))
        if not _HEX_64.fullmatch(digest):
            issues.append({"reason": "raw_payload_sha256_invalid", "index": index})
        row_count = item.get("row_count")
        row_count_valid = isinstance(row_count, int) and not isinstance(row_count, bool) and row_count > 0
        if not row_count_valid:
            issues.append({"reason": "capture_row_count_invalid", "index": index})
        if item.get("pagination_complete") is not True:
            issues.append({"reason": "capture_pagination_incomplete", "index": index})
        if item.get("schema_validation_status") != "passed":
            issues.append({"reason": "capture_schema_not_validated", "index": index})
        if item.get("raw_payload_archived") is not True:
            issues.append({"reason": "raw_payload_not_archived", "index": index})
        if not str(item.get("window_start", "")).strip() or not str(item.get("window_end", "")).strip():
            issues.append({"reason": "capture_window_missing", "index": index})
        if not str(item.get("publisher_id", "")).strip():
            issues.append({"reason": "capture_publisher_id_missing", "index": index})
        if (capture_id and _HEX_64.fullmatch(digest) and row_count_valid
                and item.get("pagination_complete") is True
                and item.get("schema_validation_status") == "passed"
                and item.get("raw_payload_archived") is True):
            valid_capture_count += 1
    if valid_capture_count == 0:
        issues.append({"reason": "no_valid_raw_capture_evidence"})
    approved = set(source_coverage.get("approved_official_sources", [])) | set(source_coverage.get("approved_third_party_sources", []))
    if not approved.issubset(seen_source_ids):
        issues.append({"reason": "approved_sources_missing_capture_evidence",
                       "missing": sorted(approved - seen_source_ids)})
    if reconciliation.get("status") != "RECONCILIATION_PASSED":
        issues.append({"reason": "independent_source_reconciliation_not_passed"})
    if reconciliation.get("unresolved_critical_anomalies") != 0:
        issues.append({"reason": "unresolved_critical_anomalies_present_or_unreported"})
    if reconciliation.get("independent_publisher_count", 0) < 3:
        issues.append({"reason": "fewer_than_three_independent_publishers"})
    if calendar_evidence.get("official_session_completeness_verified") is not True:
        issues.append({"reason": "official_market_calendar_completeness_unverified"})
    if universe_evidence.get("point_in_time_universe_verified") is not True:
        issues.append({"reason": "point_in_time_security_universe_unverified"})
    if universe_evidence.get("ipo_delist_suspension_coverage_verified") is not True:
        issues.append({"reason": "ipo_delist_suspension_coverage_unverified"})
    canonical = json.dumps({"capture_count": len(capture_evidence), "issues": issues,
                            "source_coverage_sha256": source_coverage.get("coverage_sha256")}, sort_keys=True, separators=(",", ":"))
    return {
        "status": "HISTORICAL_PILOT_EVIDENCE_READY_FOR_HUMAN_REVIEW" if not issues else "HISTORICAL_PILOT_BLOCKED",
        "capture_count": len(capture_evidence), "valid_capture_count": valid_capture_count,
        "captured_source_ids": sorted(seen_source_ids), "issues": issues,
        "pilot_evidence_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "backtest_admission_allowed": False, "replay_executed": False,
        "publisher_authenticity_proven": False, "performance_claims_allowed": False,
        "limitations": [
            "Hashes prove byte identity only, not that a publisher is genuine or the data is complete.",
            "Reconciliation status must be generated by the independent, versioned reconciliation pipeline.",
            "This evidence gate qualifies a bounded pilot for human review; Step 77 and Step 78 gates remain mandatory.",
        ],
    }


def run_controlled_historical_pilot(*, pilot_evidence: Mapping[str, Any],
                                    replay_kwargs: Mapping[str, Any]) -> dict:
    """Invoke Step 78 only after the real capture/reconciliation evidence gate passes."""
    if pilot_evidence.get("status") != "HISTORICAL_PILOT_EVIDENCE_READY_FOR_HUMAN_REVIEW":
        return {
            "status": "BLOCKED_NO_VERIFIED_PILOT_PANEL",
            "pilot_evidence": dict(pilot_evidence),
            "replay_result": None, "historical_replay_executed": False,
            "canonical_promotion_allowed": False, "production_enabled": False,
        }
    from app.historical_replay_enforcement import enforce_and_run_six_scanner_replay
    result = enforce_and_run_six_scanner_replay(**dict(replay_kwargs))
    return {
        "status": result.get("status", "BLOCKED"),
        "pilot_evidence": dict(pilot_evidence), "replay_result": result,
        "historical_replay_executed": result.get("historical_replay_executed") is True,
        "canonical_promotion_allowed": False, "production_enabled": False,
        "performance_metrics_interpreted": False,
    }
