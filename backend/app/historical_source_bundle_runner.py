"""Validate real source bundles before handing a bounded panel to Step 78.

All I/O is injected by the caller. This module performs no network access and
never treats a provider name or caller-supplied status flag as source proof.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from typing import Any

from app.historical_pilot_capture import validate_official_capture_manifest
from app.historical_pilot_source_contract import validate_historical_source_contract
from app.historical_source_pilot_gate import (
    audit_nepse_source_coverage,
    evaluate_historical_pilot_evidence,
    run_controlled_historical_pilot,
)

_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")


def _digest_ok(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def validate_real_source_bundle(
    *,
    source_contracts: list[Mapping[str, Any]],
    capture_bundles: list[Mapping[str, Any]],
    decision_cutoff: str,
    schema_validator: Callable[..., Mapping[str, Any]],
    archive_verifier: Callable[..., Mapping[str, Any]],
    reconciliation: Mapping[str, Any],
    calendar_evidence: Mapping[str, Any],
    universe_evidence: Mapping[str, Any],
) -> dict:
    """Validate each raw manifest/payload using existing contract and capture validators."""
    coverage = audit_nepse_source_coverage(
        source_contracts=source_contracts, decision_cutoff=decision_cutoff,
    )
    contract_results = []
    registry = []
    contract_by_id = {}
    for contract in source_contracts:
        source_id = str(contract.get("source_id", "")).strip()
        checked = validate_historical_source_contract(
            contract=contract, decision_cutoff=decision_cutoff,
        )
        identity_ok = contract.get("publisher_identity_reviewed") is True
        if checked.get("capture_allowed") is True and identity_ok:
            registry.append(checked["registry_record"])
            contract_by_id[source_id] = contract
        contract_results.append({
            "source_id": source_id or None,
            "status": "APPROVED_FOR_CAPTURE" if checked.get("capture_allowed") and identity_ok else "BLOCKED",
            "contract_errors": checked.get("errors", []),
            "publisher_identity_reviewed": identity_ok,
        })

    capture_evidence = []
    capture_reports = []
    errors = []
    seen_capture_ids = set()
    for index, bundle in enumerate(capture_bundles):
        if not isinstance(bundle, Mapping):
            errors.append({"index": index, "reason": "capture_bundle_not_mapping"})
            continue
        manifest = bundle.get("manifest")
        payloads = bundle.get("payloads")
        if not isinstance(manifest, Mapping) or not isinstance(payloads, Mapping):
            errors.append({"index": index, "reason": "manifest_or_payloads_missing"})
            continue
        capture_id = str(manifest.get("capture_id", "")).strip()
        source_id = str(manifest.get("source_id", "")).strip()
        if not capture_id or capture_id in seen_capture_ids:
            errors.append({"index": index, "reason": "capture_id_missing_or_duplicate"})
            continue
        seen_capture_ids.add(capture_id)
        contract = contract_by_id.get(source_id)
        if contract is None:
            errors.append({"index": index, "reason": "capture_source_contract_not_approved"})
            continue
        report = validate_official_capture_manifest(
            manifest, payloads, approved_registry=registry,
            decision_cutoff=decision_cutoff,
        )
        if report.get("status") != "CAPTURE_VALIDATED":
            errors.append({"capture_id": capture_id, "reason": "raw_capture_manifest_blocked",
                           "details": report.get("errors", [])})
            capture_reports.append(report)
            continue
        try:
            schema = schema_validator(
                dataset_kind=contract.get("dataset_kind"),
                manifest=manifest,
                payloads=payloads,
            )
        except Exception as exc:
            schema = {"status": "SCHEMA_VALIDATION_ERROR", "error_type": type(exc).__name__}
        row_count = schema.get("row_count") if isinstance(schema, Mapping) else None
        schema_ok = (
            isinstance(schema, Mapping)
            and schema.get("status") == "passed"
            and isinstance(row_count, int) and not isinstance(row_count, bool) and row_count > 0
        )
        if not schema_ok:
            errors.append({"capture_id": capture_id, "reason": "schema_validation_failed",
                           "schema_status": schema.get("status") if isinstance(schema, Mapping) else None})
        try:
            archive = archive_verifier(
                capture_id=capture_id,
                manifest=manifest,
                payloads=payloads,
                raw_payload_hashes=report.get("raw_payload_hashes", []),
            )
        except Exception as exc:
            archive = {"status": "ARCHIVE_VERIFICATION_ERROR", "error_type": type(exc).__name__}
        archive_ok = (
            isinstance(archive, Mapping)
            and archive.get("status") == "archived"
            and bool(str(archive.get("archive_ref", "")).strip())
            and _digest_ok(archive.get("archive_manifest_sha256"))
        )
        if not archive_ok:
            errors.append({"capture_id": capture_id, "reason": "immutable_raw_archive_not_verified"})
        evidence = {
            "capture_id": capture_id,
            "source_id": source_id,
            "publisher_id": report.get("publisher_id"),
            "raw_payload_sha256": hashlib.sha256(
                json.dumps(report.get("raw_payload_hashes", []), sort_keys=True).encode()
            ).hexdigest(),
            "row_count": row_count,
            "pagination_complete": report.get("status") == "CAPTURE_VALIDATED",
            "schema_validation_status": "passed" if schema_ok else "failed",
            "raw_payload_archived": archive_ok,
            "window_start": report.get("window_start"),
            "window_end": report.get("window_end"),
            "capture_manifest_sha256": report.get("manifest_sha256"),
            "archive_ref": archive.get("archive_ref") if isinstance(archive, Mapping) else None,
            "archive_manifest_sha256": archive.get("archive_manifest_sha256") if isinstance(archive, Mapping) else None,
        }
        capture_evidence.append(evidence)
        capture_reports.append({
            "capture_validation": report,
            "schema_validation": dict(schema) if isinstance(schema, Mapping) else {},
            "archive_validation": dict(archive) if isinstance(archive, Mapping) else {},
        })

    for name, report in (
        ("reconciliation", reconciliation),
        ("calendar", calendar_evidence),
        ("universe", universe_evidence),
    ):
        digest = report.get("report_sha256") if isinstance(report, Mapping) else None
        if not _digest_ok(digest):
            errors.append({"reason": f"{name}_report_sha256_missing_or_invalid"})

    evidence = evaluate_historical_pilot_evidence(
        source_coverage=coverage,
        capture_evidence=capture_evidence,
        reconciliation=reconciliation,
        calendar_evidence=calendar_evidence,
        universe_evidence=universe_evidence,
    )
    if errors:
        evidence = dict(evidence)
        evidence["status"] = "HISTORICAL_PILOT_BLOCKED"
        evidence["issues"] = list(evidence.get("issues", [])) + errors
        evidence["backtest_admission_allowed"] = False
        evidence["replay_executed"] = False
    canonical = json.dumps({
        "coverage": coverage.get("coverage_sha256"),
        "captures": [x.get("capture_validation", {}).get("manifest_sha256") for x in capture_reports],
        "evidence": evidence.get("pilot_evidence_sha256"),
        "errors": errors,
    }, sort_keys=True, separators=(",", ":"))
    return {
        "status": evidence.get("status"),
        "source_coverage": coverage,
        "contract_results": contract_results,
        "capture_reports": capture_reports,
        "pilot_evidence": evidence,
        "errors": errors,
        "bundle_validation_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "network_access_performed": False,
        "historical_replay_executed": False,
        "backtest_admission_allowed": False,
        "production_enabled": False,
    }


def run_replay_from_validated_source_bundle(
    *,
    source_bundle_kwargs: Mapping[str, Any],
    replay_kwargs: Mapping[str, Any],
) -> dict:
    """Run Steps 80–81 bundle validation first; delegate only eligible evidence to Step 78."""
    bundle = validate_real_source_bundle(**dict(source_bundle_kwargs))
    if bundle.get("status") != "HISTORICAL_PILOT_EVIDENCE_READY_FOR_HUMAN_REVIEW":
        return {
            "status": "BLOCKED_SOURCE_BUNDLE_NOT_READY",
            "source_bundle": bundle,
            "replay_result": None,
            "historical_replay_executed": False,
            "canonical_promotion_allowed": False,
            "production_enabled": False,
        }
    replay = run_controlled_historical_pilot(
        pilot_evidence=bundle["pilot_evidence"],
        replay_kwargs=replay_kwargs,
    )
    return {
        "status": replay.get("status", "BLOCKED"),
        "source_bundle": bundle,
        "replay_result": replay,
        "historical_replay_executed": replay.get("historical_replay_executed") is True,
        "canonical_promotion_allowed": False,
        "production_enabled": False,
        "performance_metrics_interpreted": False,
    }
